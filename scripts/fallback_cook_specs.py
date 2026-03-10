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


def make_spec(spec_id, name, family, asset, timeframe, thesis, indicators, long_rules, short_rules, long_exit, short_exit, variant_name, template_name, params):
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
    quandalf_produced = int(status.get("specs_produced", 0) or 0) > 0 or len(existing_paths) > 0

    recent_cycles = list(state.get("recent_cycles") or [])
    recent_cycles = [item for item in recent_cycles if int(item.get("cycle_id", -1) or -1) != cycle_id]

    if quandalf_produced:
        state["zero_spec_streak"] = 0
        recent_cycles.append({"cycle_id": cycle_id, "fallback_used": False, "quandalf_zero": False})
        state["recent_cycles"] = recent_cycles[-10:]
        persist_state(state)
        print(json.dumps({"status": "skipped", "reason": "quandalf_produced_specs", "cycle_id": cycle_id}))
        return

    zero_spec_streak = int(state.get("zero_spec_streak", 0) or 0) + 1
    state["zero_spec_streak"] = zero_spec_streak

    if zero_spec_streak < 3:
        recent_cycles.append({"cycle_id": cycle_id, "fallback_used": False, "quandalf_zero": True})
        state["recent_cycles"] = recent_cycles[-10:]
        persist_state(state)
        print(json.dumps({"status": "skipped", "reason": "fallback_guard_active", "cycle_id": cycle_id, "zero_spec_streak": zero_spec_streak}))
        return

    spec = make_spec(
        f"QD-{date_tag}-{cycle_tag}-{asset}-EMA-PULLBACK-v1",
        f"{asset} EMA Pullback v1",
        f"{asset.lower()}_ema_pullback",
        asset, timeframe,
        "trend pullback continuation after value reclaim",
        ["EMA_20", "EMA_55", "ATR_14", "RSI_14", "PLUS_DI_14", "MINUS_DI_14"],
        ["Close > EMA_55", "EMA_20 > EMA_55", "low >= EMA_20 - 0.6 * ATR_14", "RSI_14 >= 50", "PLUS_DI_14 >= MINUS_DI_14"],
        ["Close < EMA_55", "EMA_20 < EMA_55", "high <= EMA_20 + 0.6 * ATR_14", "RSI_14 <= 50", "MINUS_DI_14 >= PLUS_DI_14"],
        ["Stop loss: 1.1 * ATR_14 below entry", "Take profit: 2.4 * ATR_14 above entry", "Early exit if Close crosses_below EMA_20", "Time stop: 10 bars"],
        ["Stop loss: 1.1 * ATR_14 above entry", "Take profit: 2.4 * ATR_14 below entry", "Early exit if Close crosses_above EMA_20", "Time stop: 10 bars"],
        f"{asset.lower()}_ema_pullback_v1", "ema_pullback", {"ema_fast": 20, "ema_anchor": 55, "pullback_buffer_atr": 0.6, "rsi_mid": 50}
    )

    path = OUT_DIR / f"{spec['id']}.strategy_spec.json"
    write_json(path, spec)
    paths = [str(path)]

    recent_cycles.append({"cycle_id": cycle_id, "fallback_used": True, "quandalf_zero": True})
    rolling = recent_cycles[-10:]
    state["recent_cycles"] = rolling
    fallback_share = sum(1 for item in rolling if item.get("fallback_used")) / max(1, len(rolling))
    state["fallback_share_10_cycle"] = round(fallback_share, 3)
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
        "new_families": [spec["family_name"]],
        "iterated_families": [],
        "abandoned_families": [],
        "fallback_source": True,
        "next_cycle_focus": f"Fallback rescue fired after {zero_spec_streak} zero-spec cycles. Evaluate the single {asset} {timeframe} rescue spec and restore real exploration.",
        "rationale": "Fallback cooker emitted one rescue spec after 3 consecutive zero-spec cycles from Quandalf.",
    })
    write_json(STATUS, status)

    warning = "Fallback dominance detected — Quandalf may be stuck" if fallback_share > 0.2 and len(rolling) >= 5 else None
    print(json.dumps({"status": "ok", "cycle_id": cycle_id, "spec_count": len(paths), "spec_paths": paths, "fallback_share_10_cycle": round(fallback_share, 3), "warning": warning}))


if __name__ == "__main__":
    main()
