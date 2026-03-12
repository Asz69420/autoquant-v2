#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
ORDERS = ROOT / "agents" / "quandalf" / "memory" / "cycle_orders.json"
STATUS = ROOT / "agents" / "quandalf" / "memory" / "current_cycle_status.json"
OUT_DIR = ROOT / "artifacts" / "strategy_specs"
STATE_PATH = ROOT / "data" / "state" / "fallback_control.json"


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_state():
    return load_json(STATE_PATH, {"zero_spec_streak": 0, "recent_cycles": []})


def persist_state(payload):
    write_json(STATE_PATH, payload)


def make_spec(spec_id, name, family, asset, timeframe, thesis, indicators, long_rules, short_rules, long_exit, short_exit, variant_name, template_name, params, management_style="one_shot"):
    risk_management = {
        "initial_stop": "1.1 ATR",
        "trailing_stop": None,
        "time_stop_bars": 10,
        "breakeven_trigger": None,
        "partial_tp_levels": []
    }
    exit_style = "one_shot"
    position_stages = [
        {"action": "entry", "trigger": "signal", "size_pct": 100},
        {"action": "exit", "trigger": "exit_rules", "size_pct": 100}
    ]
    if management_style == "partial_runner":
        risk_management["partial_tp_levels"] = [
            {"trigger": "1.2 ATR", "size_pct": 50},
            {"trigger": "2.4 ATR", "size_pct": 50}
        ]
        risk_management["trailing_stop"] = "0.9 ATR after first partial"
        exit_style = "partial_runner"
        position_stages = [
            {"action": "entry", "trigger": "signal", "size_pct": 100},
            {"action": "take_profit", "trigger": "1.2 ATR", "size_pct": 50},
            {"action": "runner_exit", "trigger": "trailing_stop_or_exit_rules", "size_pct": 50}
        ]
    elif management_style == "trail_and_timer":
        risk_management["initial_stop"] = "1.2 ATR"
        risk_management["trailing_stop"] = "1.0 ATR"
        risk_management["time_stop_bars"] = 14
        exit_style = "trailing_time_mix"
        position_stages = [
            {"action": "entry", "trigger": "signal", "size_pct": 100},
            {"action": "de_risk", "trigger": "8 bars in trade", "size_pct": 40},
            {"action": "exit", "trigger": "trailing_stop_or_exit_rules", "size_pct": 60}
        ]
    return {
        "schema_version": "1.0",
        "id": spec_id,
        "ts_iso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "thesis_id": f"{spec_id.lower()}_thesis",
        "name": name,
        "version": "1.0",
        "asset": asset,
        "timeframe": timeframe,
        "family_name": family,
        "thesis": thesis,
        "primary_asset": asset,
        "primary_timeframe": timeframe,
        "validation_targets": [{"asset": asset, "timeframe": timeframe, "purpose": "walk_forward_screen"}],
        "edge_mechanism": thesis,
        "expected_regime": "trending and transitional",
        "invalidation_condition": f"If {family} cannot clear the trade floor or PF > 1 after costs on {asset} {timeframe}, retire the family.",
        "indicators": indicators,
        "entry_rules": {"long": long_rules, "short": short_rules},
        "exit_rules": {"long": long_exit, "short": short_exit},
        "position_sizing": {"risk_per_trade_pct": 0.004},
        "trade_management": {
            "entry_style": "one_shot",
            "exit_style": exit_style,
            "position_stages": position_stages,
            "risk_management": risk_management
        },
        "regime_filter": {
            "allowed_regimes": ["trending", "transitional"],
            "detection_method": f"Simple {asset} {timeframe} trend/transition filter.",
        },
        "variants": [{
            "name": variant_name,
            "template_name": template_name,
            "parameters": [{"name": k, "value": v} for k, v in params.items()],
            "risk_policy": {
                "stop_type": "atr",
                "stop_atr_mult": 1.1,
                "tp_type": "atr",
                "tp_atr_mult": 2.4,
                "risk_per_trade_pct": 0.004,
                "max_concurrent_positions": 1,
                "max_holding_bars": 10,
            },
            "execution_policy": {
                "entry_fill": "bar_close",
                "tie_break": "worst_case",
                "allow_reverse": True,
                "slippage_bps": 8,
                "fee_bps": 6,
            },
            "risk_rules": ["cooldown_bars=0"],
        }],
        "complexity_score": 1.4,
        "status": "ready_to_test",
        "source": "fallback_cooker",
        "fallback_source": True,
        "research_mode": "fallback",
    }


def main():
    orders = load_json(ORDERS, {})
    status = load_json(STATUS, {})
    state = load_state()
    cycle_id = int(orders.get("cycle_id", 0) or 0)
    asset = str(orders.get("target_asset") or "ETH").upper()
    timeframe = str(orders.get("target_timeframe") or "4h")
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    cycle_tag = f"C{cycle_id}"

    existing_paths = [str(p).strip() for p in (status.get("spec_paths") or []) if str(p).strip()]
    minimum_spec_count = int(orders.get("minimum_spec_count", 3) or 3)
    produced_count = max(int(status.get("specs_produced", 0) or 0), len(existing_paths))
    quandalf_produced = produced_count >= minimum_spec_count

    recent_cycles = list(state.get("recent_cycles") or [])
    recent_cycles = [item for item in recent_cycles if int(item.get("cycle_id", -1) or -1) != cycle_id]

    if quandalf_produced:
        state["zero_spec_streak"] = 0
        recent_cycles.append({"cycle_id": cycle_id, "fallback_used": False, "quandalf_zero": False, "quandalf_under_minimum": False})
        state["recent_cycles"] = recent_cycles[-10:]
        persist_state(state)
        print(json.dumps({"status": "skipped", "reason": "quandalf_produced_minimum_specs", "cycle_id": cycle_id, "produced_count": produced_count, "minimum_spec_count": minimum_spec_count}))
        return

    force_fallback_cycle_id = int(state.get("force_fallback_cycle_id", 0) or 0)
    force_fallback = force_fallback_cycle_id == cycle_id

    zero_spec_streak = int(state.get("zero_spec_streak", 0) or 0) + 1
    state["zero_spec_streak"] = zero_spec_streak

    if zero_spec_streak < 3 and not force_fallback:
        recent_cycles.append({"cycle_id": cycle_id, "fallback_used": False, "quandalf_zero": produced_count == 0, "quandalf_under_minimum": produced_count < minimum_spec_count})
        state["recent_cycles"] = recent_cycles[-10:]
        persist_state(state)
        print(json.dumps({"status": "skipped", "reason": "fallback_guard_active", "cycle_id": cycle_id, "zero_spec_streak": zero_spec_streak, "produced_count": produced_count, "minimum_spec_count": minimum_spec_count}))
        return

    fallback_specs = [
        make_spec(
            f"QD-{date_tag}-{cycle_tag}-{asset}-EMA-PULLBACK-v1",
            f"{asset} EMA Pullback v1",
            f"{asset.lower()}_ema_pullback",
            asset, timeframe,
            "trend pullback continuation after value reclaim",
            ["EMA_20", "EMA_55", "ATR_14", "RSI_14", "PLUS_DI_14", "MINUS_DI_14"],
            ["Close > EMA_55", "EMA_20 > EMA_55", "low >= EMA_20 - 0.9 * ATR_14", "RSI_14 >= 48", "PLUS_DI_14 >= MINUS_DI_14"],
            ["Close < EMA_55", "EMA_20 < EMA_55", "high <= EMA_20 + 0.9 * ATR_14", "RSI_14 <= 52", "MINUS_DI_14 >= PLUS_DI_14"],
            ["Stop loss: 1.1 * ATR_14 below entry", "Take profit: 2.4 * ATR_14 above entry", "Early exit if Close crosses_below EMA_20", "Time stop: 12 bars"],
            ["Stop loss: 1.1 * ATR_14 above entry", "Take profit: 2.4 * ATR_14 below entry", "Early exit if Close crosses_above EMA_20", "Time stop: 12 bars"],
            f"{asset.lower()}_ema_pullback_v1", "ema_pullback", {"ema_fast": 20, "ema_anchor": 55, "pullback_buffer_atr": 0.9, "rsi_mid": 50}, "one_shot"
        ),
        make_spec(
            f"QD-{date_tag}-{cycle_tag}-{asset}-RANGE-RECLAIM-v1",
            f"{asset} Range Reclaim v1",
            f"{asset.lower()}_range_reclaim",
            asset, timeframe,
            "range reclaim continuation after false breakdown and value recovery",
            ["EMA_20", "ATR_14", "RSI_14", "ADX_14"],
            ["Close > EMA_20", "RSI_14 >= 46", "ADX_14 <= 28"],
            ["Close < EMA_20", "RSI_14 <= 54", "ADX_14 <= 28"],
            ["Stop loss: 1.0 * ATR_14 below entry", "Take profit: 2.0 * ATR_14 above entry", "Exit if Close crosses_below EMA_20"],
            ["Stop loss: 1.0 * ATR_14 above entry", "Take profit: 2.0 * ATR_14 below entry", "Exit if Close crosses_above EMA_20"],
            f"{asset.lower()}_range_reclaim_v1", "range_reclaim", {"ema_anchor": 20, "adx_cap": 28, "rsi_mid": 50}, "partial_runner"
        ),
        make_spec(
            f"QD-{date_tag}-{cycle_tag}-{asset}-BREAKOUT-HOLD-v1",
            f"{asset} Breakout Hold v1",
            f"{asset.lower()}_breakout_hold",
            asset, timeframe,
            "breakout continuation after hold above broken structure with volatility expansion",
            ["EMA_20", "EMA_55", "ATR_14", "ADX_14"],
            ["Close > EMA_20", "EMA_20 > EMA_55", "ADX_14 >= 14"],
            ["Close < EMA_20", "EMA_20 < EMA_55", "ADX_14 >= 14"],
            ["Stop loss: 1.2 * ATR_14 below entry", "Take profit: 2.8 * ATR_14 above entry", "Trailing stop: 1.0 * ATR_14"],
            ["Stop loss: 1.2 * ATR_14 above entry", "Take profit: 2.8 * ATR_14 below entry", "Trailing stop: 1.0 * ATR_14"],
            f"{asset.lower()}_breakout_hold_v1", "breakout_hold", {"ema_fast": 20, "ema_anchor": 55, "adx_floor": 14}, "trail_and_timer"
        )
    ]

    generated_paths = []
    for spec in fallback_specs:
        path = OUT_DIR / f"{spec['id']}.strategy_spec.json"
        write_json(path, spec)
        generated_paths.append(str(path))
    paths = list(dict.fromkeys(existing_paths + generated_paths))

    recent_cycles.append({"cycle_id": cycle_id, "fallback_used": True, "quandalf_zero": True, "force_fallback": force_fallback})
    rolling = recent_cycles[-10:]
    state["recent_cycles"] = rolling
    fallback_share = sum(1 for item in rolling if item.get("fallback_used")) / max(1, len(rolling))
    state["fallback_share_10_cycle"] = round(fallback_share, 3)
    if force_fallback:
        state.pop("force_fallback_cycle_id", None)
        state.pop("force_fallback_reason", None)
        state.pop("force_fallback_ts_iso", None)
    persist_state(state)

    status.update({
        "cycle_id": cycle_id,
        "mode": orders.get("mode", "explore"),
        "research_direction": orders.get("research_direction", "explore_new"),
        "minimum_spec_count": orders.get("minimum_spec_count", 3),
        "maximum_spec_count": orders.get("maximum_spec_count", 4),
        "target_asset": asset,
        "target_timeframe": timeframe,
        "exploration_targets": orders.get("exploration_targets", {}),
        "iterate_target": orders.get("iterate_target"),
        "spec_paths": paths,
        "specs_produced": len(paths),
        "new_families": [spec["family_name"] for spec in fallback_specs],
        "iterated_families": [],
        "abandoned_families": [],
        "fallback_source": True,
        "next_cycle_focus": f"Fallback rescue fired after {zero_spec_streak} zero-spec cycles. Evaluate the three {asset} {timeframe} rescue families with diversified management and restore real exploration.",
        "rationale": "Fallback cooker emitted three denser rescue specs with diversified management after 3 consecutive under-minimum cycles from Quandalf.",
    })
    write_json(STATUS, status)

    warning = "Fallback dominance detected — Quandalf may be stuck" if fallback_share > 0.2 and len(rolling) >= 5 else None
    print(json.dumps({"status": "ok", "cycle_id": cycle_id, "spec_count": len(paths), "spec_paths": paths, "fallback_share_10_cycle": round(fallback_share, 3), "warning": warning}))


if __name__ == "__main__":
    main()
