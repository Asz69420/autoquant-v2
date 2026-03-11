#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
ORDERS = ROOT / "agents" / "quandalf" / "memory" / "cycle_orders.json"
LEARNING = ROOT / "agents" / "quandalf" / "memory" / "latest_learning_loop.json"
REFLECTION = ROOT / "agents" / "quandalf" / "memory" / "reflection_packet.json"
OUT = ROOT / "agents" / "quandalf" / "memory" / "research_program.json"


def load_json(path: Path, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main():
    orders = load_json(ORDERS, {})
    learning = load_json(LEARNING, {})
    reflection = load_json(REFLECTION, {})
    diagnosis = learning.get("diagnosis_breakdown") or {}
    recent_failures = (learning.get("dimensions") or {}).get("why_it_failed") or []

    anti_patterns = [
        "ceremonial sparse confirmation chains",
        "indicator stacks with no clear role separation",
        "single-lane convenience bias",
        "cosmetic refinement without structural diagnosis",
    ]
    if any("too sparse" in str(x).lower() for x in recent_failures):
        anti_patterns.append("event-sparse entries that cannot plausibly generate trades")
    if any("wrong regime" in str(x).lower() for x in recent_failures):
        anti_patterns.append("forcing continuation logic into regime-mismatched lanes")

    validation_basket = orders.get("validation_basket") or []
    active_hypotheses = []
    for concept in ((orders.get("exploration_targets") or {}).get("concepts") or []):
        active_hypotheses.append({
            "concept": concept,
            "primary_lane": f"{orders.get('target_asset')}/{orders.get('target_timeframe')}",
            "allowed_basket": validation_basket,
            "continuation_criteria": "strategy trades plausibly and survives screen with credible density",
            "rotation_criteria": "0-trade, wrong-regime, wrong-lane, or too-sparse diagnosis",
        })

    payload = {
        "ts_iso": now_iso(),
        "cycle_id": orders.get("cycle_id") or reflection.get("cycle_id"),
        "search_priorities": [
            "mechanism-first research",
            "lane choice justified by thesis",
            "denser participation logic before cosmetic refinement",
            "structured management variation",
        ],
        "active_hypotheses": active_hypotheses,
        "banned_failure_patterns": anti_patterns,
        "lane_rotation_policy": {
            "use_validation_basket": True,
            "rotate_when_concentration_high": True,
            "current_primary_lane": f"{orders.get('target_asset')}/{orders.get('target_timeframe')}",
            "allowed_basket": validation_basket,
        },
        "meaningful_refinement": [
            "change lane when thesis fits better elsewhere",
            "reassign component roles",
            "simplify sparse logic",
            "change management structure",
            "test adjacent timeframe or cross-asset robustness",
        ],
        "diagnosis_breakdown": diagnosis,
        "current_directives": [
            "Every strategy must carry a reasoning block.",
            "0 trades is a red flag that must resolve to refine or abort.",
            "Prefer a small basket of justified lanes over narrow single-lane convenience.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "path": str(OUT), "cycle_id": payload["cycle_id"]}, indent=2))


if __name__ == "__main__":
    main()
