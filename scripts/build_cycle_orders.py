#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
BRIEFING = ROOT / "agents" / "quandalf" / "memory" / "briefing_packet.json"
ORDERS = ROOT / "agents" / "quandalf" / "memory" / "cycle_orders.json"
STATUS = ROOT / "agents" / "quandalf" / "memory" / "current_cycle_status.json"
METRICS = ROOT / "data" / "state" / "current_cycle_metrics.json"

DEFAULT_ASSET_ORDER = ["ETH", "BTC", "SOL", "TAO", "AVAX", "LINK", "DOGE", "ARB", "OP", "INJ"]
DEFAULT_TF_ORDER = ["4h", "1h", "1d", "15m"]
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
]

MANAGEMENT_STYLES = [
    "one-shot entry with one-shot exit",
    "one-shot entry with partial take-profit and runner",
    "one-shot entry with trailing-stop exit",
    "time-based de-risking after entry",
    "scaled-out exits after confirmation",
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


def pick_asset_timeframe(universe: dict, prior_status: dict) -> tuple[str, str]:
    assets_by_tf = universe.get("assets_by_timeframe") or {}
    timeframes_by_asset = universe.get("timeframes_by_asset") or {}
    prev_asset = str(prior_status.get("target_asset") or "").upper()
    prev_tf = str(prior_status.get("target_timeframe") or "")

    candidate_pairs = []
    for tf in DEFAULT_TF_ORDER:
        for asset in DEFAULT_ASSET_ORDER:
            if asset in (assets_by_tf.get(tf) or []) and tf in (timeframes_by_asset.get(asset) or []):
                candidate_pairs.append((asset, tf))
    if not candidate_pairs:
        for asset, tfs in sorted(timeframes_by_asset.items()):
            for tf in tfs:
                candidate_pairs.append((asset, tf))

    for asset, tf in candidate_pairs:
        if asset != prev_asset and tf != prev_tf:
            return asset, tf
    for asset, tf in candidate_pairs:
        if asset != prev_asset:
            return asset, tf
    return candidate_pairs[0] if candidate_pairs else ("ETH", "4h")


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
        "exploration_targets": {
            "concepts": concept_pack,
            "management_styles": MANAGEMENT_STYLES,
            "assets": [asset],
            "timeframes": [timeframe],
        },
        "thesis_hint": f"Explore fresh {asset} {timeframe} structures across distinct mechanisms and trade-management styles. Prioritize dense concepts over ceremonial sparse logic.",
        "stop_condition": "Write 3-4 materially different specs for this asset/timeframe using supported candle data only. At least one spec should test a meaningfully different trade-management expression.",
        "rotation_reason": f"Deterministic explore rotation away from prior lane ({prior_status.get('target_asset', 'none')} / {prior_status.get('target_timeframe', 'none')}).",
    }
    ORDERS.parent.mkdir(parents=True, exist_ok=True)
    ORDERS.write_text(json.dumps(orders, indent=2), encoding="utf-8")
    sync_status_to_orders(cycle_id, orders)
    sync_metrics_to_orders(cycle_id, orders)
    print(json.dumps({"status": "ok", "cycle_id": cycle_id, "orders_path": str(ORDERS), "target_asset": asset, "target_timeframe": timeframe}))


if __name__ == "__main__":
    main()
