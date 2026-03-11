#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
REFLECTION = ROOT / "agents" / "quandalf" / "memory" / "reflection_packet.json"
DECISIONS = ROOT / "agents" / "quandalf" / "memory" / "refinement_decisions.json"
VALIDATOR = ROOT / "scripts" / "validate_quandalf_decisions.py"
OPENCLAW = Path(r"C:\Users\Clamps\AppData\Roaming\npm\openclaw.cmd")
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 330


def load_json(path: Path, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def normalize_legacy_decisions(reflection, decisions):
    if not isinstance(decisions, dict):
        decisions = {}
    outcomes = {}
    queue_meta = {}
    for item in (reflection.get("strategy_outcomes") or []):
        if not isinstance(item, dict):
            continue
        spec_id = str(item.get("strategy_spec_id") or "").strip()
        if not spec_id:
            continue
        outcomes[spec_id] = item
        for q in (item.get("queue") or []):
            if not isinstance(q, dict):
                continue
            queue_id = str(q.get("queue_id") or "").strip()
            if queue_id:
                queue_meta[queue_id] = q

    changed = False
    strategy_decisions = decisions.get("strategy_decisions") or []
    if not isinstance(strategy_decisions, list):
        strategy_decisions = []
        changed = True

    normalized_strategy = []
    for item in strategy_decisions:
        if not isinstance(item, dict):
            changed = True
            continue
        cloned = dict(item)
        decision = str(cloned.get("decision") or cloned.get("strategy_decision") or "").strip().lower()
        if decision != str(cloned.get("decision") or "").strip().lower():
            changed = True
        if decision:
            cloned["decision"] = decision
        cloned.pop("strategy_decision", None)
        spec_id = str(cloned.get("strategy_spec_id") or "").strip()
        outcome = outcomes.get(spec_id, {}) if spec_id else {}
        if not str(cloned.get("rationale") or "").strip():
            rationale = str(outcome.get("rationale") or outcome.get("diagnosis_category") or f"Inherited {decision or 'pending'} decision from legacy refinement format.").strip()
            cloned["rationale"] = rationale
            changed = True
        if not str(cloned.get("diagnosis_category") or "").strip() and outcome.get("diagnosis_category"):
            cloned["diagnosis_category"] = outcome.get("diagnosis_category")
            changed = True
        queue_decisions = cloned.get("queue_decisions")
        if not isinstance(queue_decisions, list):
            queue_decisions = []
            changed = True
        cloned["queue_decisions"] = queue_decisions
        normalized_strategy.append(cloned)

    jobs = decisions.get("jobs") or []
    if not isinstance(jobs, list):
        jobs = []
        changed = True
    normalized_jobs = []
    legacy_queue_map = {}
    for item in jobs:
        if not isinstance(item, dict):
            changed = True
            continue
        cloned = dict(item)
        legacy_decision = str(cloned.get("decision") or cloned.get("job_decision") or "").strip().lower()
        if legacy_decision and legacy_decision != str(cloned.get("decision") or "").strip().lower():
            cloned["decision"] = legacy_decision
            changed = True
        if "job_decision" in cloned:
            cloned.pop("job_decision", None)
            changed = True
        queue_id = str(cloned.get("queue_id") or "").strip()
        if queue_id and legacy_decision in {"pass", "refine", "abort"}:
            legacy_queue_map[queue_id] = cloned
        if legacy_decision == "refine":
            normalized_jobs.append(cloned)
        else:
            changed = True

    for item in normalized_strategy:
        spec_id = str(item.get("strategy_spec_id") or "").strip()
        existing = {str(q.get("queue_id") or "").strip() for q in (item.get("queue_decisions") or []) if isinstance(q, dict)}
        outcome = outcomes.get(spec_id, {}) if spec_id else {}
        for q in (outcome.get("queue") or []):
            if not isinstance(q, dict):
                continue
            queue_id = str(q.get("queue_id") or "").strip()
            if not queue_id or queue_id in existing:
                continue
            legacy = legacy_queue_map.get(queue_id, {})
            qdecision = str(legacy.get("decision") or item.get("decision") or "").strip().lower()
            if qdecision not in {"pass", "refine", "abort"}:
                continue
            notes = q.get("notes") or {}
            if isinstance(notes, dict):
                note_text = notes.get("error") or notes.get("reason") or notes.get("status") or "row evidence reviewed"
            else:
                note_text = str(notes).strip() or "row evidence reviewed"
            qentry = {
                "queue_id": queue_id,
                "decision": qdecision,
                "rationale": str(legacy.get("rationale") or f"Legacy queue decision normalized for {queue_id}: {note_text}.").strip(),
            }
            result_id = q.get("result_id")
            if result_id:
                qentry["source_result_id"] = result_id
            item.setdefault("queue_decisions", []).append(qentry)
            changed = True

    decisions["strategy_decisions"] = normalized_strategy
    decisions["jobs"] = normalized_jobs
    return decisions, changed


def run_validator():
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    payload = {}
    try:
        payload = json.loads((proc.stdout or "").strip() or "{}")
    except Exception:
        payload = {"status": "error", "errors": ["validator_output_parse_failed"], "raw": proc.stdout}
    return proc.returncode, payload, proc.stdout, proc.stderr


def build_missing_summary(errors):
    out = {
        "missing_strategy_decisions": [],
        "missing_queue_decisions": [],
        "invalid_entries": [],
    }
    for err in errors or []:
        text = str(err)
        if text.startswith("missing_strategy_decision:"):
            out["missing_strategy_decisions"].append(text.split(":", 1)[1])
        elif text.startswith("missing_queue_decision_global:"):
            out["missing_queue_decisions"].append(text.split(":", 1)[1])
        else:
            out["invalid_entries"].append(text)
    return out


def build_prompt(reflection, validator_payload, attempt):
    cycle_id = int(reflection.get("cycle_id") or 0)
    outcomes = reflection.get("strategy_outcomes") or []
    compact = []
    for item in outcomes:
        if not isinstance(item, dict):
            continue
        compact.append({
            "strategy_spec_id": item.get("strategy_spec_id"),
            "asset": item.get("asset"),
            "timeframe": item.get("timeframe"),
            "diagnosis_category": item.get("diagnosis_category"),
            "rationale": item.get("rationale"),
            "allowed_next_actions": item.get("allowed_next_actions"),
            "results": [
                {
                    "id": r.get("id"),
                    "asset": r.get("asset"),
                    "timeframe": r.get("timeframe"),
                    "qscore": r.get("score_total"),
                    "profit_factor": r.get("profit_factor"),
                    "total_trades": r.get("total_trades"),
                    "decision": r.get("score_decision"),
                }
                for r in (item.get("results") or [])
                if isinstance(r, dict)
            ],
            "queue": [
                {
                    "queue_id": q.get("queue_id"),
                    "stage": q.get("stage"),
                    "status": q.get("status"),
                    "result_id": q.get("result_id"),
                    "notes": q.get("notes"),
                }
                for q in (item.get("queue") or [])
                if isinstance(q, dict)
            ],
        })

    missing = build_missing_summary(validator_payload.get("errors") or [])

    return (
        f"Read agents/quandalf/memory/reflection_packet.json for cycle {cycle_id} and rewrite "
        f"agents/quandalf/memory/refinement_decisions.json from scratch. This is attempt {attempt}/{MAX_ATTEMPTS}. "
        "LAW: there are exactly 3 legal decisions everywhere: pass, refine, abort. "
        "Forbidden words and outputs: promote, fix_only, skip, pending, undecided. "
        "Do NOT write any top-level decision field. Write only: cycle_id, ts_iso, strategy_decisions, jobs. "
        "You must decide BOTH levels: \n"
        "1) strategy_decisions: one overall decision per strategy_spec_id\n"
        "2) queue_decisions: inside each strategy_decision, one explicit decision for EVERY queue row in that strategy's queue array\n"
        "Each queue_decision must contain queue_id, decision, rationale, and source_result_id when a result_id exists.\n"
        "Required shape example: {\"cycle_id\": 23, \"ts_iso\": \"...\", \"strategy_decisions\": [{\"strategy_spec_id\": \"...\", \"decision\": \"abort\", \"rationale\": \"...\", \"diagnosis_category\": \"too sparse\", \"queue_decisions\": [{\"queue_id\": \"rq_123\", \"decision\": \"abort\", \"rationale\": \"zero trades on valid data\", \"source_result_id\": null}]}], \"jobs\": []}. "
        "If decision=refine at strategy level, include iteration_intent, structural_change, expected_effect, and add at least one refine job in jobs.\n"
        "If decision is pass or abort, do not add a refine job.\n"
        "You are not allowed to omit any queue row. You are not allowed to leave stale cycle data in the file. "
        "Return by writing the file only.\n\n"
        f"Validator failure summary: {json.dumps(missing, ensure_ascii=False)}\n\n"
        f"Cycle evidence summary: {json.dumps(compact, ensure_ascii=False)}"
    )


def call_quandalf(prompt):
    proc = subprocess.run(
        [str(OPENCLAW), "agent", "--agent", "quandalf", "--message", prompt],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=TIMEOUT_SECONDS,
    )
    return proc


def autofill_queue_decisions_from_strategy(reflection, decisions):
    changed = False
    by_spec = {}
    for item in (decisions.get("strategy_decisions") or []):
        if isinstance(item, dict):
            by_spec[str(item.get("strategy_spec_id") or "").strip()] = item

    for outcome in (reflection.get("strategy_outcomes") or []):
        if not isinstance(outcome, dict):
            continue
        spec_id = str(outcome.get("strategy_spec_id") or "").strip()
        if not spec_id or spec_id not in by_spec:
            continue
        target = by_spec[spec_id]
        strategy_decision = str(target.get("decision") or "").strip().lower()
        if strategy_decision not in {"pass", "refine", "abort"}:
            continue
        existing = target.get("queue_decisions") or []
        if existing:
            continue
        queue_decisions = []
        for q in (outcome.get("queue") or []):
            if not isinstance(q, dict):
                continue
            queue_id = str(q.get("queue_id") or "").strip()
            if not queue_id:
                continue
            result_id = q.get("result_id")
            status = str(q.get("status") or "").strip().lower()
            notes = q.get("notes") or {}
            if isinstance(notes, dict):
                note_text = notes.get("reason") or notes.get("error") or notes.get("status") or "row evidence reviewed"
            else:
                note_text = str(notes).strip() or "row evidence reviewed"
            rationale = f"Inherited {strategy_decision} from Quandalf's strategy-level decision for {spec_id}; queue row {queue_id} ended as {status or 'unknown'} with evidence: {note_text}."
            entry = {
                "queue_id": queue_id,
                "decision": strategy_decision,
                "rationale": rationale,
            }
            if result_id:
                entry["source_result_id"] = result_id
            queue_decisions.append(entry)
        if queue_decisions:
            target["queue_decisions"] = queue_decisions
            changed = True

    if changed:
        DECISIONS.write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    return changed


def main():
    reflection = load_json(REFLECTION, {})
    cycle_id = int(reflection.get("cycle_id") or 0)
    if cycle_id <= 0:
        print(json.dumps({"status": "error", "reason": "reflection_packet_missing_cycle_id"}, indent=2))
        return 1

    decisions = load_json(DECISIONS, {})
    cycle_reset = int(decisions.get("cycle_id") or 0) != cycle_id
    if cycle_reset:
        decisions = {"cycle_id": cycle_id, "ts_iso": reflection.get("ts_iso"), "strategy_decisions": [], "jobs": []}
        DECISIONS.write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    decisions, normalized = normalize_legacy_decisions(reflection, decisions)
    if normalized:
        DECISIONS.write_text(json.dumps(decisions, indent=2), encoding="utf-8")

    final_validator = None
    agent_runs = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        code, payload, stdout, stderr = run_validator()
        final_validator = payload
        if code == 0:
            print(json.dumps({
                "status": "ok",
                "cycle_id": cycle_id,
                "attempts": attempt - 1,
                "validator": payload,
                "agent_runs": agent_runs,
            }, indent=2))
            return 0

        prompt = build_prompt(reflection, payload, attempt)
        proc = call_quandalf(prompt)
        agent_runs.append({
            "attempt": attempt,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-500:],
            "stderr_tail": (proc.stderr or "")[-500:],
        })
        if proc.returncode != 0:
            print(json.dumps({
                "status": "error",
                "cycle_id": cycle_id,
                "reason": "quandalf_call_failed",
                "attempt": attempt,
                "validator": payload,
                "agent_runs": agent_runs,
            }, indent=2))
            return 1

    decisions = load_json(DECISIONS, {})
    cycle_reset = int(decisions.get("cycle_id") or 0) != cycle_id
    if cycle_reset:
        decisions = {"cycle_id": cycle_id, "ts_iso": reflection.get("ts_iso"), "strategy_decisions": [], "jobs": []}
        DECISIONS.write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    decisions, normalized = normalize_legacy_decisions(reflection, decisions)
    if normalized:
        DECISIONS.write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    autofilled = autofill_queue_decisions_from_strategy(reflection, decisions)
    code, payload, stdout, stderr = run_validator()
    final_validator = payload
    status = "ok" if code == 0 else "error"
    print(json.dumps({
        "status": status,
        "cycle_id": cycle_id,
        "attempts": MAX_ATTEMPTS,
        "autofilled_queue_decisions": autofilled,
        "validator": final_validator,
        "agent_runs": agent_runs,
    }, indent=2))
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
