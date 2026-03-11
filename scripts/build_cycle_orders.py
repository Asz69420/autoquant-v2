#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
BRIEFING = ROOT / "agents" / "quandalf" / "memory" / "briefing_packet.json"
ORDERS = ROOT / "agents" / "quandalf" / "memory" / "cycle_orders.json"
STATUS = ROOT / "agents" / "quandalf" / "memory" / "current_cycle_status.json"
METRICS = ROOT / "data" / "state" / "current_cycle_metrics.json"
ROTATION_HISTORY = ROOT / "data" / "state" / "rotation_history.json"
REGIME_SUMMARY = ROOT / "data" / "state" / "regime_summary.json"
EXTERNAL_INTEL_INDEX = ROOT / "data" / "external_intel" / "index.json"

DEFAULT_ASSET_ORDER = ["ETH", "BTC", "SOL", "TAO", "AVAX", "LINK", "DOGE", "ARB", "OP", "INJ"]
DEFAULT_TF_ORDER = ["4h", "1h", "1d", "15m"]
HIGH_BETA_ASSETS = ["TAO", "AXS", "DOGE", "ARB", "OP", "INJ"]
ROTATION_LOOKBACK = 5  # avoid repeating asset/tf pair from last N cycles
CONCEPT_PACKS = [
    [
        "trend pullback continuation after deeper value reclaim into structural support",
        "volatility squeeze expansion confirmed by persistence instead of first breakout bar",
        "failed breakdown reclaim that must hold before continuation entry",
    ],
    [
        "range-failure reversal after multi-bar breakout loses acceptance and re-enters balance",
        "trend reset continuation after a deeper pullback instead of shallow ema-touch logic",
        "compression fakeout into re-expansion with directional confirmation",
    ],
    [
        "state-change momentum after regime improvement and post-break hold",
        "mean reversion from exhaustion only when structure reaccepts prior value",
        "breakout continuation with delayed entry after retest rather than immediate trigger",
    ],
    [
        "opening-range or session-window continuation when a specific session structurally dominates follow-through",
        "inventory-reset continuation after flush-and-reclaim rather than static oversold bounce logic",
        "post-expansion partial-profit runner structure that keeps a core position for trend persistence",
    ],
    [
        "scale-in around value recovery when confirmation improves across bars instead of one-shot all-in timing",
        "trend continuation with asymmetric exit logic where trigger, risk, and exit indicators play different roles",
        "retest-and-hold continuation that de-risks by time if expansion fails to appear fast enough",
    ],
]

MANAGEMENT_STYLES = [
    "one-shot entry with one-shot exit",
    "one-shot entry with partial take-profit and runner",
    "one-shot entry with trailing-stop exit",
    "time-based de-risking after entry",
    "scaled-out exits after confirmation",
    "scale-in on improved confirmation, then scale-out into expansion",
    "partial-profit first target with runner managed by structure instead of fixed take-profit only",
]


def load_json(path: Path, default):
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, type(default)):
                return data
    except Exception:
        pass
    return default


def load_rotation_history() -> list:
    try:
        if ROTATION_HISTORY.exists():
            data = json.loads(ROTATION_HISTORY.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_rotation_history(history: list):
    ROTATION_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    # Keep last 20 entries
    ROTATION_HISTORY.write_text(json.dumps(history[-20:], indent=2), encoding="utf-8")


def load_regime_summary() -> dict:
    try:
        if REGIME_SUMMARY.exists():
            data = json.loads(REGIME_SUMMARY.read_text(encoding="utf-8"))
            return data.get("pairs", {})
    except Exception:
        pass
    return {}


def load_external_intel_index() -> dict:
    try:
        if EXTERNAL_INTEL_INDEX.exists():
            data = json.loads(EXTERNAL_INTEL_INDEX.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"items": [], "sources": []}


def select_external_intel(asset: str, timeframe: str, limit: int = 5) -> dict:
    index_data = load_external_intel_index()
    items = index_data.get("items") or []
    asset = str(asset or "").upper()
    selected = []
    fallback = []
    for item in reversed(items):
        if not isinstance(item, dict):
            continue
        scope = [str(x).upper() for x in (item.get("asset_scope") or [])]
        if asset and asset in scope:
            selected.append(item)
        elif not scope:
            fallback.append(item)
    chosen = (selected + fallback)[:limit]
    return {
        "enabled_sources": [s.get("id") for s in (index_data.get("sources") or []) if isinstance(s, dict) and s.get("enabled")],
        "recent_items": chosen,
        "target_asset": asset,
        "target_timeframe": timeframe,
        "count": len(chosen),
    }


def pick_asset_timeframe(universe: dict, prior_status: dict) -> tuple[str, str]:
    assets_by_tf = universe.get("assets_by_timeframe") or {}
    timeframes_by_asset = universe.get("timeframes_by_asset") or {}

    # Build all valid candidate pairs
    candidate_pairs = []
    for tf in DEFAULT_TF_ORDER:
        for asset in DEFAULT_ASSET_ORDER:
            if asset in (assets_by_tf.get(tf) or []) and tf in (timeframes_by_asset.get(asset) or []):
                candidate_pairs.append((asset, tf))
    if not candidate_pairs:
        for asset, tfs in sorted(timeframes_by_asset.items()):
            for tf in tfs:
                candidate_pairs.append((asset, tf))

    # Load rotation history — avoid pairs used in last N cycles
    history = load_rotation_history()
    recent_pairs = set()
    for entry in history[-ROTATION_LOOKBACK:]:
        a = str(entry.get("asset", "")).upper()
        t = str(entry.get("timeframe", ""))
        if a and t:
            recent_pairs.add((a, t))

    # Also track recent assets (not just pairs) to force diversity
    recent_assets = []
    for entry in history[-ROTATION_LOOKBACK:]:
        a = str(entry.get("asset", "")).upper()
        if a:
            recent_assets.append(a)

    # Prefer pairs not seen in recent history, and assets not recently used
    fresh_pairs = [(a, t) for a, t in candidate_pairs if (a, t) not in recent_pairs and a not in recent_assets]
    if fresh_pairs:
        return fresh_pairs[0]

    # Fallback: at least different pair from recent
    different_pairs = [(a, t) for a, t in candidate_pairs if (a, t) not in recent_pairs]
    if different_pairs:
        return different_pairs[0]

    # Last fallback: different from immediately previous
    prev_asset = str(prior_status.get("target_asset") or "").upper()
    prev_tf = str(prior_status.get("target_timeframe") or "")
    for asset, tf in candidate_pairs:
        if asset != prev_asset:
            return asset, tf

    return candidate_pairs[0] if candidate_pairs else ("ETH", "4h")


def pick_adjacent_timeframe(timeframe: str, available: list[str]) -> str | None:
    ordering = ["15m", "1h", "4h", "1d"]
    if timeframe not in ordering:
        return None
    idx = ordering.index(timeframe)
    candidates = []
    if idx > 0:
        candidates.append(ordering[idx - 1])
    if idx + 1 < len(ordering):
        candidates.append(ordering[idx + 1])
    for tf in candidates:
        if tf in available:
            return tf
    return None


def build_validation_basket(asset: str, timeframe: str, universe: dict) -> list[dict]:
    assets_by_tf = universe.get("assets_by_timeframe") or {}
    timeframes_by_asset = universe.get("timeframes_by_asset") or {}
    basket = []
    seen = set()

    def add_lane(a: str, tf: str, role: str):
        key = (a, tf)
        if not a or not tf or key in seen:
            return
        seen.add(key)
        basket.append({"asset": a, "timeframe": tf, "role": role})

    add_lane(asset, timeframe, "primary")
    adjacent = pick_adjacent_timeframe(timeframe, timeframes_by_asset.get(asset, []))
    if adjacent:
        add_lane(asset, adjacent, "adjacent_timeframe")

    same_tf_assets = [a for a in (assets_by_tf.get(timeframe) or []) if a != asset]
    for candidate in DEFAULT_ASSET_ORDER:
        if candidate in same_tf_assets:
            add_lane(candidate, timeframe, "similar_asset")
            break
    for candidate in HIGH_BETA_ASSETS:
        if candidate != asset and candidate in same_tf_assets:
            add_lane(candidate, timeframe, "structurally_different_asset")
            break

    return basket


def pick_concept_pack(cycle_id: int, prior_status: dict) -> list[str]:
    prior_concepts = ((prior_status.get("exploration_targets") or {}).get("concepts") or []) if isinstance(prior_status, dict) else []
    start_idx = int(cycle_id or 0) % len(CONCEPT_PACKS)
    for offset in range(len(CONCEPT_PACKS)):
        pack = CONCEPT_PACKS[(start_idx + offset) % len(CONCEPT_PACKS)]
        if pack != prior_concepts:
            return pack
    return CONCEPT_PACKS[start_idx]


def sync_metrics_to_orders(cycle_id: int, orders: dict):
    metrics = load_json(METRICS, {})
    if not isinstance(metrics, dict):
        metrics = {}
    metrics["cycle_id"] = cycle_id
    metrics["status"] = metrics.get("status") or "pending"
    metrics["mode"] = orders.get("mode")
    metrics["research_direction"] = orders.get("research_direction")
    metrics["target_asset"] = orders.get("target_asset")
    metrics["target_timeframe"] = orders.get("target_timeframe")
    metrics["exploration_targets"] = orders.get("exploration_targets") or {}
    metrics["iterate_target"] = orders.get("iterate_target")
    metrics.setdefault("spec_paths", [])
    metrics.setdefault("spec_ids", [])
    metrics.setdefault("specs_produced", 0)
    metrics.setdefault("specs_written", 0)
    metrics.setdefault("cycle_rows", 0)
    metrics.setdefault("external_rows", 0)
    metrics.setdefault("cycle_results_present", False)
    metrics.setdefault("external_results_present", False)
    metrics.setdefault("backtests_queued", 0)
    metrics.setdefault("backtests_completed", 0)
    metrics.setdefault("pass_count", 0)
    metrics.setdefault("fail_count", 0)
    metrics.setdefault("promote_count", 0)
    metrics.setdefault("best_result", None)
    metrics.setdefault("best_qscore", 0)
    metrics.setdefault("next_cycle_focus", "pending")
    metrics.setdefault("rationale", "pending")
    metrics["status_matches_cycle"] = True
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def sync_status_to_orders(cycle_id: int, orders: dict):
    status = load_json(STATUS, {})
    if not isinstance(status, dict):
        status = {}
    previous_asset = str(status.get("target_asset") or "").upper()
    previous_tf = str(status.get("target_timeframe") or "")
    new_asset = str(orders.get("target_asset") or "").upper()
    new_tf = str(orders.get("target_timeframe") or "")
    status["cycle_id"] = cycle_id
    status["mode"] = orders.get("mode")
    status["research_direction"] = orders.get("research_direction")
    status["target_asset"] = orders.get("target_asset")
    status["target_timeframe"] = orders.get("target_timeframe")
    status["exploration_targets"] = orders.get("exploration_targets") or {}
    status["iterate_target"] = orders.get("iterate_target")
    status["specific_family_to_iterate"] = orders.get("specific_family_to_iterate")
    should_clear = int(status.get("specs_produced", 0) or 0) <= 0
    if not should_clear and bool(status.get("fallback_source")) and (previous_asset != new_asset or previous_tf != new_tf):
        should_clear = True
    if should_clear:
        status["spec_paths"] = []
        status["specs_produced"] = 0
        status["new_families"] = []
        status["iterated_families"] = []
        status["abandoned_families"] = []
        status["fallback_source"] = False
        status["next_cycle_focus"] = "pending"
        status["rationale"] = "pending"
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")


def main():
    briefing = load_json(BRIEFING, {})
    prior_status = load_json(STATUS, {})
    cycle_id = int(briefing.get("cycle_id", 0) or 0)
    universe = briefing.get("supported_backtest_universe") or {}
    asset, timeframe = pick_asset_timeframe(universe, prior_status)
    concept_pack = pick_concept_pack(cycle_id, prior_status)

    # Load regime context for the target pair
    regimes = load_regime_summary()
    pair_key = f"{asset}/{timeframe}"
    regime_info = regimes.get(pair_key, {"current": "UNKNOWN", "confidence": 0.0})
    current_regime = regime_info.get("current", "UNKNOWN")
    regime_confidence = regime_info.get("confidence", 0.0)

    regime_hint = ""
    if current_regime == "TREND_UP":
        regime_hint = "Market is trending up — favor continuation and pullback entries over mean reversion."
    elif current_regime == "TREND_DOWN":
        regime_hint = "Market is trending down — favor short continuation or reversal setups, avoid blind long entries."
    elif current_regime == "CHOP":
        regime_hint = "Market is choppy/ranging — favor mean reversion and range-bound strategies, avoid trend-following."
    elif current_regime == "EXPANSION":
        regime_hint = "Volatility expanding — favor breakout and momentum strategies with wider stops."
    elif current_regime == "COMPRESSION":
        regime_hint = "Volatility compressing — favor squeeze breakout setups, expect imminent expansion."
    elif current_regime == "TRANSITION":
        regime_hint = "Market transitioning between states — favor adaptive strategies that can handle regime shifts."

    external_intel = select_external_intel(asset, timeframe)

    validation_basket = build_validation_basket(asset, timeframe, universe)
    orders = {
        "cycle_id": cycle_id,
        "ts_iso": datetime.now(timezone.utc).isoformat(),
        "mode": "explore",
        "minimum_spec_count": 3,
        "maximum_spec_count": 4,
        "target_asset": asset,
        "target_timeframe": timeframe,
        "research_direction": "explore_new",
        "specific_family_to_iterate": None,
        "iterate_target": None,
        "current_regime": current_regime,
        "regime_confidence": regime_confidence,
        "regime_context": regime_info,
        "external_intel": external_intel,
        "design_axes": {
            "indicator_roles": ["regime filter", "setup qualifier", "trigger", "risk", "exit"],
            "management_expressions": MANAGEMENT_STYLES,
            "conceptual_space": ["continuation", "reversal", "mean reversion", "session logic", "inventory reset", "expansion follow-through"],
            "anti_patterns": ["ceremonial sparse confirmation chains", "same indicator doing every role", "single-bar hero entries with no management logic"]
        },
        "exploration_targets": {
            "concepts": concept_pack,
            "management_styles": MANAGEMENT_STYLES,
            "assets": sorted({lane['asset'] for lane in validation_basket}),
            "timeframes": sorted({lane['timeframe'] for lane in validation_basket}),
        },
        "validation_basket": validation_basket,
        "allowed_lanes": validation_basket,
        "lane_authority": {
            "quandalf_controls_lane_selection": True,
            "auto_fetch_missing_data": True,
            "instruction": "Choose the best-fit asset/timeframe based on thesis. Use the validation basket deliberately. If you need a lane inside the supported universe that is not already cached, request it through the spec and the system will prepare the candles before backtest."
        },
        "thesis_hint": f"Explore fresh {asset} {timeframe} structures as the primary lane, but you are allowed to choose lanes from the validation basket when the thesis fits better. Current regime: {current_regime} ({regime_confidence}% confidence). {regime_hint} Prioritize dense concepts over ceremonial sparse logic. Use mechanism-first reasoning and vary indicator roles, lane choice, and management logic, not just entry triggers.",
        "stop_condition": "Write 3-4 materially different specs using the best-fit lanes from the allowed basket. At least one spec should test a meaningfully different trade-management expression, at least one should vary indicator-role assignment rather than only entry conditions, and chosen lanes must be justified by thesis.",
        "rotation_reason": f"Deterministic explore rotation away from prior lane ({prior_status.get('target_asset', 'none')} / {prior_status.get('target_timeframe', 'none')}) while preserving freedom to choose the best-fit lane from the basket.",
    }
    ORDERS.parent.mkdir(parents=True, exist_ok=True)
    ORDERS.write_text(json.dumps(orders, indent=2), encoding="utf-8")

    # Record rotation history
    history = load_rotation_history()
    history.append({"cycle_id": cycle_id, "asset": asset, "timeframe": timeframe, "regime": current_regime, "ts": datetime.now(timezone.utc).isoformat()})
    save_rotation_history(history)
    sync_status_to_orders(cycle_id, orders)
    sync_metrics_to_orders(cycle_id, orders)
    print(json.dumps({"status": "ok", "cycle_id": cycle_id, "orders_path": str(ORDERS), "target_asset": asset, "target_timeframe": timeframe}))


if __name__ == "__main__":
    main()
