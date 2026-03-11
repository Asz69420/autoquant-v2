#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
REFLECTION = ROOT / "agents" / "quandalf" / "memory" / "reflection_packet.json"
DECISIONS = ROOT / "agents" / "quandalf" / "memory" / "refinement_decisions.json"
OUT = ROOT / "agents" / "quandalf" / "memory" / "latest_experiment_memory.json"
STATE_OUT = ROOT / "data" / "state" / "quandalf_experiment_memory.json"


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
    reflection = load_json(REFLECTION, {})
    decisions = load_json(DECISIONS, {})
    by_decision = {}
    for item in (decisions.get("strategy_decisions") or []):
        if isinstance(item, dict):
            by_decision[str(item.get("strategy_spec_id") or "")] = item

    experiments = []
    for item in (reflection.get("strategy_outcomes") or []):
        if not isinstance(item, dict):
            continue
        spec_id = str(item.get("strategy_spec_id") or "")
        latest = item.get("latest_result") or {}
        decision = by_decision.get(spec_id, {})
        experiments.append({
            "strategy_spec_id": spec_id,
            "hypothesis": item.get("hypothesis"),
            "chosen_lane": {
                "asset": item.get("asset"),
                "timeframe": item.get("timeframe"),
            },
            "component_roles": item.get("indicators") or [],
            "mutation_surface": decision.get("mutation_type") or latest.get("mutation_type") or "initial",
            "expected_effect": item.get("rationale"),
            "actual_effect": {
                "trade_count": latest.get("total_trades"),
                "profit_factor": latest.get("profit_factor"),
                "max_drawdown_pct": latest.get("max_drawdown_pct"),
                "qscore": latest.get("score_total"),
                "decision": decision.get("decision") or item.get("recommended_action"),
            },
            "regime_context": latest.get("regime_metrics") or {},
            "diagnosis": decision.get("diagnosis_category") or item.get("diagnosis_category"),
            "lesson_extracted": decision.get("rationale") or item.get("rationale"),
        })

    payload = {
        "ts_iso": now_iso(),
        "cycle_id": reflection.get("cycle_id"),
        "count": len(experiments),
        "experiments": experiments,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    STATE_OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    STATE_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "count": len(experiments), "path": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
