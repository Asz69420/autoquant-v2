#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
REFLECTION = ROOT / "agents" / "quandalf" / "memory" / "reflection_packet.json"
DECISIONS = ROOT / "agents" / "quandalf" / "memory" / "refinement_decisions.json"
ALLOWED_DECISIONS = {"pass", "refine", "abort"}


def load_json(path: Path, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main() -> int:
    reflection = load_json(REFLECTION, {})
    decisions = load_json(DECISIONS, {})

    cycle_id = int(reflection.get("cycle_id") or 0)
    decision_cycle_id = int(decisions.get("cycle_id") or 0)
    strategy_outcomes = reflection.get("strategy_outcomes") or []
    strategy_decisions = decisions.get("strategy_decisions") or []
    jobs = decisions.get("jobs") or []

    errors = []
    if cycle_id <= 0:
        errors.append("reflection_packet_missing_cycle_id")
    if decision_cycle_id != cycle_id:
        errors.append(f"decision_cycle_mismatch:{decision_cycle_id}!={cycle_id}")
    if not isinstance(strategy_outcomes, list):
        errors.append("reflection_packet_strategy_outcomes_invalid")
        strategy_outcomes = []
    if not isinstance(strategy_decisions, list):
        errors.append("strategy_decisions_invalid")
        strategy_decisions = []
    if not isinstance(jobs, list):
        errors.append("jobs_invalid")
        jobs = []

    expected_ids = []
    expected_queue_ids = set()
    queue_to_strategy = {}
    for item in strategy_outcomes:
        if not isinstance(item, dict):
            continue
        spec_id = str(item.get("strategy_spec_id") or "").strip()
        if spec_id:
            expected_ids.append(spec_id)
        for queue_item in (item.get("queue") or []):
            if not isinstance(queue_item, dict):
                continue
            queue_id = str(queue_item.get("queue_id") or "").strip()
            if queue_id:
                expected_queue_ids.add(queue_id)
                queue_to_strategy[queue_id] = spec_id
    expected_set = set(expected_ids)

    seen = set()
    decided_queue_ids = set()
    for item in strategy_decisions:
        if not isinstance(item, dict):
            errors.append("strategy_decision_item_invalid")
            continue
        spec_id = str(item.get("strategy_spec_id") or "").strip()
        decision = str(item.get("decision") or "").strip().lower()
        rationale = str(item.get("rationale") or "").strip()
        if not spec_id:
            errors.append("strategy_decision_missing_strategy_spec_id")
            continue
        if spec_id not in expected_set:
            errors.append(f"unexpected_strategy_decision:{spec_id}")
        if spec_id in seen:
            errors.append(f"duplicate_strategy_decision:{spec_id}")
        seen.add(spec_id)
        if decision not in ALLOWED_DECISIONS:
            errors.append(f"invalid_decision:{spec_id}:{decision}")
        if not rationale:
            errors.append(f"missing_rationale:{spec_id}")
        if decision == "refine":
            for field in ("iteration_intent", "structural_change", "expected_effect"):
                if not str(item.get(field) or "").strip():
                    errors.append(f"missing_{field}:{spec_id}")

        queue_decisions = item.get("queue_decisions") or []
        if not isinstance(queue_decisions, list):
            errors.append(f"queue_decisions_invalid:{spec_id}")
            queue_decisions = []
        expected_for_strategy = {qid for qid, owner in queue_to_strategy.items() if owner == spec_id}
        seen_local = set()
        for qitem in queue_decisions:
            if not isinstance(qitem, dict):
                errors.append(f"queue_decision_item_invalid:{spec_id}")
                continue
            queue_id = str(qitem.get("queue_id") or "").strip()
            qdecision = str(qitem.get("decision") or "").strip().lower()
            qrationale = str(qitem.get("rationale") or "").strip()
            if not queue_id:
                errors.append(f"queue_decision_missing_queue_id:{spec_id}")
                continue
            if queue_id not in expected_queue_ids:
                errors.append(f"unexpected_queue_decision:{spec_id}:{queue_id}")
            if queue_id in seen_local:
                errors.append(f"duplicate_queue_decision:{spec_id}:{queue_id}")
            seen_local.add(queue_id)
            decided_queue_ids.add(queue_id)
            if qdecision not in ALLOWED_DECISIONS:
                errors.append(f"invalid_queue_decision:{spec_id}:{queue_id}:{qdecision}")
            if not qrationale:
                errors.append(f"missing_queue_rationale:{spec_id}:{queue_id}")
        missing_local = sorted(expected_for_strategy - seen_local)
        for queue_id in missing_local:
            errors.append(f"missing_queue_decision:{spec_id}:{queue_id}")

    missing = sorted(expected_set - seen)
    for spec_id in missing:
        errors.append(f"missing_strategy_decision:{spec_id}")

    refine_job_ids = set()
    for item in jobs:
        if not isinstance(item, dict):
            errors.append("job_item_invalid")
            continue
        decision = str(item.get("decision") or "").strip().lower()
        spec_id = str(item.get("strategy_spec_id") or "").strip()
        if decision != "refine":
            errors.append(f"invalid_job_decision:{spec_id}:{decision}")
            continue
        refine_job_ids.add(spec_id)
        for field in ("rationale", "spec_path", "mutation_type"):
            if not str(item.get(field) or "").strip():
                errors.append(f"missing_job_{field}:{spec_id}")

    for item in strategy_decisions:
        if not isinstance(item, dict):
            continue
        spec_id = str(item.get("strategy_spec_id") or "").strip()
        decision = str(item.get("decision") or "").strip().lower()
        if decision == "refine" and spec_id not in refine_job_ids:
            errors.append(f"refine_without_job:{spec_id}")
        if decision != "refine" and spec_id in refine_job_ids:
            errors.append(f"job_without_refine_decision:{spec_id}")

    missing_queue = sorted(expected_queue_ids - decided_queue_ids)
    for queue_id in missing_queue:
        errors.append(f"missing_queue_decision_global:{queue_id}")

    payload = {
        "status": "ok" if not errors else "error",
        "cycle_id": cycle_id,
        "strategy_count": len(expected_set),
        "decision_count": len(strategy_decisions),
        "expected_queue_count": len(expected_queue_ids),
        "decided_queue_count": len(decided_queue_ids),
        "job_count": len(jobs),
        "errors": errors,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
