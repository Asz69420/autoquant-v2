#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
BRIEFING = ROOT / "agents" / "quandalf" / "memory" / "briefing_packet.json"
ORDERS = ROOT / "agents" / "quandalf" / "memory" / "cycle_orders.json"
STATUS = ROOT / "agents" / "quandalf" / "memory" / "current_cycle_status.json"

DEFAULT_ASSET_ORDER = ["ETH", "BTC", "SOL", "TAO", "AVAX", "LINK", "DOGE", "ARB", "OP", "INJ"]
DEFAULT_TF_ORDER = ["4h", "1h", "1d", "15m"]
DEFAULT_CONCEPTS = [
    "trend pullback continuation after value reclaim",
    "volatility compression release with directional filter",
    "failed breakdown reacceptance with momentum confirmation",
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


def main():
    briefing = load_json(BRIEFING, {})
    prior_status = load_json(STATUS, {})
    cycle_id = int(briefing.get("cycle_id", 0) or 0)
    universe = briefing.get("supported_backtest_universe") or {}
    asset, timeframe = pick_asset_timeframe(universe, prior_status)

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
            "concepts": DEFAULT_CONCEPTS,
            "assets": [asset],
            "timeframes": [timeframe],
        },
        "thesis_hint": f"Explore fresh {asset} {timeframe} structures with simple, testable rules and distinct concepts.",
        "stop_condition": "Write 3-4 materially different specs for this asset/timeframe using supported candle data only.",
        "rotation_reason": f"Deterministic explore rotation away from prior lane ({prior_status.get('target_asset', 'none')} / {prior_status.get('target_timeframe', 'none')}).",
    }
    ORDERS.parent.mkdir(parents=True, exist_ok=True)
    ORDERS.write_text(json.dumps(orders, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "cycle_id": cycle_id, "orders_path": str(ORDERS), "target_asset": asset, "target_timeframe": timeframe}))


if __name__ == "__main__":
    main()
