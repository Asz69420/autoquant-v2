#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

from text_io import read_text_best_effort

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
TG_SCRIPT = os.path.join(ROOT, "scripts", "tg_notify.py")
TASK_GOVERNOR = os.path.join(ROOT, "scripts", "task_governor.py")
JOURNAL_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "latest_journal.md")
DAILY_JOURNAL_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "daily_journal.md")
JOURNAL_ARCHIVE_DIR = os.path.join(ROOT, "agents", "quandalf", "memory", "journal")
DECISION_COMPLETION_SCRIPT = os.path.join(ROOT, "scripts", "ensure_quandalf_decisions_complete.py")
BACKTESTER = os.path.join(ROOT, "scripts", "walk_forward_engine.py")
BALROG = r"C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\balrog-validate.py"
SPECS_DIR = os.path.join(ROOT, "artifacts", "strategy_specs")
BOARD_PATH = os.path.join(ROOT, "data", "state", "agent_messages.json")
CARD_STATE_PATH = os.path.join(ROOT, "data", "state", "cycle_postprocess_card_state.json")
CURRENT_CYCLE_SPECS_PATH = os.path.join(ROOT, "data", "state", "current_cycle_specs.json")
CURRENT_CYCLE_STATUS_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "current_cycle_status.json")
REFLECTION_PACKET_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "reflection_packet.json")
REFINEMENT_DECISIONS_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "refinement_decisions.json")
CURRENT_CYCLE_METRICS_PATH = os.path.join(ROOT, "data", "state", "current_cycle_metrics.json")
CURRENT_CYCLE_BATCH_SUMMARY_PATH = os.path.join(ROOT, "data", "state", "current_cycle_batch_summary.json")
RUN_STATE_PATH = os.path.join(ROOT, "data", "state", "research_cycle_started_at.json")
FALLBACK_CONTROL_PATH = os.path.join(ROOT, "data", "state", "fallback_control.json")
MIN_PASS_TRADES = 50
MIN_PROMOTE_TRADES = 50
SCREEN_MIN_TRADES = 30
MIN_IMPROVEMENT_DELTA = 0.05
MIN_POSITIVE_REGIME_PF = 1.2

PHASE_EMOJIS = {
    "briefing": "📋",
    "cooking": "🍳",
    "reflecting": "🔮",
    "backtesting": "🧪",
    "complete": "✅",
    "error": "❌",
    "promotion": "🏆",
    "journal": "🧙",
    "scanning": "📡",
}

STATUS_EMOJIS = {
    "ok": "✅",
    "fail": "❌",
    "warn": "⚠️",
}


def send_tg(message, channel="dm"):
    try:
        subprocess.run(
            [sys.executable, TG_SCRIPT, "--message", message, "--channel", channel],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as e:
        print(f"TG send failed: {e}", file=sys.stderr)


def send_tg_as(message, channel="dm", bot="oragorn"):
    try:
        proc = subprocess.run(
            [sys.executable, TG_SCRIPT, "--message", message, "--channel", channel, "--bot", bot],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode == 0 and '"status": "sent"' in (proc.stdout or "")
    except Exception as e:
        print(f"TG send failed: {e}", file=sys.stderr)
        return False


def record_pipeline_completion(record_prefix, actor, summary, outcome, significance, files_touched=None, evidence=None, notes=None, task_ids=None):
    files_touched = files_touched or []
    evidence = evidence or []
    task_ids = task_ids or []
    try:
        cmd = [
            sys.executable,
            TASK_GOVERNOR,
            "record",
            "--record-prefix",
            str(record_prefix),
            "--actor",
            str(actor),
            "--summary",
            str(summary),
            "--outcome",
            str(outcome),
            "--significance",
            str(significance),
        ]
        for item in files_touched:
            cmd.extend(["--file", str(item)])
        for item in evidence:
            cmd.extend(["--evidence", str(item)])
        for item in task_ids:
            cmd.extend(["--task-id", str(item)])
        if notes:
            cmd.extend(["--notes", str(notes)])
        subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except Exception as e:
        print(f"Completion record failed: {e}", file=sys.stderr)


def post_agent_message(from_agent, to_agent, msg_type, message):
    board = {"messages": []}
    if os.path.exists(BOARD_PATH):
        try:
            with open(BOARD_PATH, "r", encoding="utf-8") as f:
                current = json.load(f)
            if isinstance(current.get("messages"), list):
                board = current
            elif isinstance(current.get("messages"), dict):
                board = {"messages": []}
                for legacy_agent, payload in current["messages"].items():
                    if not isinstance(payload, dict):
                        continue
                    observations = payload.get("observations") or []
                    msg_text = "; ".join(observations[:2]) if observations else json.dumps(payload)[:160]
                    board["messages"].append(
                        {
                            "ts_iso": current.get("updated_at", datetime.now(timezone.utc).isoformat()),
                            "from": legacy_agent,
                            "to": "oragorn",
                            "type": payload.get("priority", "note"),
                            "message": msg_text,
                            "read_by": [],
                        }
                    )
        except Exception:
            board = {"messages": []}

    recent = board.get("messages", [])[-20:]
    now_dt = datetime.now(timezone.utc)
    for item in reversed(recent):
        if item.get("from") != from_agent or item.get("to") != to_agent or item.get("type") != msg_type or item.get("message") != message:
            continue
        try:
            ts = datetime.fromisoformat(str(item.get("ts_iso")).replace("Z", "+00:00"))
        except Exception:
            ts = None
        if ts and (now_dt - ts).total_seconds() < 6 * 3600:
            return

    entry = {
        "ts_iso": now_dt.isoformat(),
        "from": from_agent,
        "to": to_agent,
        "type": msg_type,
        "message": message,
        "read_by": [],
    }
    board.setdefault("messages", []).append(entry)
    if len(board["messages"]) > 100:
        board["messages"] = board["messages"][-100:]

    os.makedirs(os.path.dirname(BOARD_PATH), exist_ok=True)
    with open(BOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(board, f, indent=2)


def log_event(event_type, agent, message, severity="info", artifact_id=None, pipeline=None, step=None):
    try:
        conn = sqlite3.connect(DB)
        conn.execute(
            """
            INSERT INTO event_log (ts_iso, event_type, agent, pipeline, step, artifact_id, severity, message, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                event_type,
                agent,
                pipeline,
                step,
                artifact_id,
                severity,
                message,
                None,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def log_token_event(agent, pipeline, description):
    try:
        conn = sqlite3.connect(DB)
        conn.execute(
            """
            INSERT INTO token_spend (ts_iso, agent, pipeline, run_id, input_tokens, output_tokens, total_tokens, model, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                agent,
                pipeline,
                description,
                0,
                0,
                0,
                "tracked_externally",
                0,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def load_json_file(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_run_state():
    state = load_json_file(RUN_STATE_PATH)
    return state if isinstance(state, dict) else {}


def persist_run_state(state):
    os.makedirs(os.path.dirname(RUN_STATE_PATH), exist_ok=True)
    with open(RUN_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def resolve_cycle_id(run_state=None):
    run_state = run_state or load_run_state()
    run_cycle_id = int(run_state.get("cycle_id", 0) or 0)
    if run_cycle_id > 0:
        return run_cycle_id

    manifest = load_json_file(CURRENT_CYCLE_SPECS_PATH)
    manifest_cycle_id = int(manifest.get("cycle_id", 0) or 0)
    if manifest_cycle_id > 0:
        return manifest_cycle_id

    counter_path = os.path.join(ROOT, "data", "state", "cycle_counter.json")
    try:
        with open(counter_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("last_cycle_id", 0))
    except Exception:
        return 0


def unresolved_queue_rows_for_cycle(cycle_id):
    try:
        conn = sqlite3.connect(DB, timeout=10)
        row = conn.execute("SELECT COUNT(*) FROM research_funnel_queue WHERE cycle_id=? AND status IN ('queued','running')", (int(cycle_id),)).fetchone()
        conn.close()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def resolve_reporting_cycle_id(run_state=None):
    run_state = run_state or load_run_state()
    run_cycle_id = int(run_state.get("cycle_id", 0) or 0)
    run_status = str(run_state.get("status") or "").strip().lower()
    reflection = load_json_file(REFLECTION_PACKET_PATH)
    decisions = load_json_file(REFINEMENT_DECISIONS_PATH)
    reflection_cycle_id = int(reflection.get("cycle_id", 0) or 0)
    decision_cycle_id = int(decisions.get("cycle_id", 0) or 0)

    if reflection_cycle_id > 0 and reflection_cycle_id == decision_cycle_id:
        unresolved = unresolved_queue_rows_for_cycle(reflection_cycle_id)
        if run_cycle_id <= 0:
            return reflection_cycle_id
        if reflection_cycle_id == run_cycle_id:
            return reflection_cycle_id
        if unresolved > 0 and run_status in {"started", "busy", "pending"} and reflection_cycle_id < run_cycle_id:
            return reflection_cycle_id

    return resolve_cycle_id(run_state)


def infer_cycle_lane_from_spec_paths(spec_paths):
    asset = None
    timeframe = None
    for p in spec_paths or []:
        name = os.path.basename(str(p)).upper()
        parts = name.split('-')
        for token in parts:
            if token in {"ETH", "BTC", "SOL", "TAO", "AVAX", "LINK", "DOGE", "ARB", "OP", "INJ", "BABY"}:
                asset = token
                break
        if ".STRATEGY_SPEC.JSON" in name:
            pass
        if "-1H-" in name:
            timeframe = "1h"
        elif "-4H-" in name:
            timeframe = "4h"
        elif "-15M-" in name:
            timeframe = "15m"
        elif "-30M-" in name:
            timeframe = "30m"
    return asset, timeframe


def sync_cycle_status_to_active(cycle_id):
    """Ensure current_cycle_status.json carries coherent data for the active cycle.

    cycle-start and research-cycle sync the cycle id, but agent steps can overwrite
    only some fields and leave a split-brain status file behind. This function now
    also reconciles same-cycle status using the current orders + spec manifest.
    """
    cycle_id = int(cycle_id)
    if cycle_id <= 0:
        return
    status = load_json_file(CURRENT_CYCLE_STATUS_PATH)
    orders = load_json_file(os.path.join(ROOT, "agents", "quandalf", "memory", "cycle_orders.json"))
    manifest = load_json_file(CURRENT_CYCLE_SPECS_PATH)

    same_cycle = int(status.get("cycle_id", 0) or 0) == cycle_id
    if not same_cycle:
        status["cycle_id"] = cycle_id
        status["mode"] = "pending"
        status["research_direction"] = "pending"
        status["target_asset"] = None
        status["target_timeframe"] = None
        status["exploration_targets"] = {}
        status["iterate_target"] = None
        status["specific_family_to_iterate"] = None
        status["spec_paths"] = []
        status["specs_produced"] = 0
        status["new_families"] = []
        status["iterated_families"] = []
        status["abandoned_families"] = []
        status["next_cycle_focus"] = "pending"
        status["rationale"] = "pending"

    if int(orders.get("cycle_id", 0) or 0) == cycle_id:
        status["mode"] = orders.get("mode") or status.get("mode") or "pending"
        status["research_direction"] = orders.get("research_direction") or status.get("research_direction") or "pending"
        status["target_asset"] = orders.get("target_asset")
        status["target_timeframe"] = orders.get("target_timeframe")
        status["exploration_targets"] = orders.get("exploration_targets") or {}
        status["iterate_target"] = orders.get("iterate_target")
        status["specific_family_to_iterate"] = orders.get("specific_family_to_iterate")

    if int(manifest.get("cycle_id", 0) or 0) == cycle_id:
        status["spec_paths"] = list(manifest.get("spec_paths") or [])
        status["specs_produced"] = int(manifest.get("spec_count", len(status.get("spec_paths") or [])) or 0)
        inferred_asset, inferred_timeframe = infer_cycle_lane_from_spec_paths(status.get("spec_paths") or [])
        if inferred_asset:
            status["target_asset"] = inferred_asset
        if inferred_timeframe:
            status["target_timeframe"] = inferred_timeframe

    order_asset = str(status.get("target_asset") or "").strip().upper()
    spec_paths = status.get("spec_paths") or []
    if order_asset and spec_paths:
        mismatched = [p for p in spec_paths if f"-{order_asset}-" not in os.path.basename(str(p)).upper()]
        if mismatched:
            status["next_cycle_focus"] = "pending"
            status["rationale"] = "pending"
            status["new_families"] = []
            status["iterated_families"] = []
            status["abandoned_families"] = []

    os.makedirs(os.path.dirname(CURRENT_CYCLE_STATUS_PATH), exist_ok=True)
    with open(CURRENT_CYCLE_STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)


def observe_run_state(cycle_id=None):
    state = load_run_state()
    now_epoch = time.time()
    now_iso = datetime.now(timezone.utc).isoformat()
    state["reporting_last_seen_at_epoch"] = now_epoch
    state["reporting_last_seen_at_iso"] = now_iso
    if cycle_id and int(state.get("cycle_id", 0) or 0) <= 0:
        state["cycle_id"] = int(cycle_id)
    persist_run_state(state)
    return state


def finalize_run_state(cycle_id):
    state = observe_run_state(cycle_id)
    if int(state.get("cycle_id", 0) or 0) != int(cycle_id):
        return state

    started = float(state.get("started_at_epoch", 0) or 0)
    if started > 0 and not state.get("ended_at_epoch"):
        ended = time.time()
        state["status"] = "completed"
        state["ended_at_epoch"] = ended
        state["ended_at_iso"] = datetime.now(timezone.utc).isoformat()
        state["run_elapsed_seconds"] = round(max(0, ended - started), 1)
        persist_run_state(state)
    return state


def compute_timing_metrics(run_state):
    started = float(run_state.get("started_at_epoch", 0) or 0)
    ended = float(run_state.get("ended_at_epoch", 0) or 0)
    seen = float(run_state.get("reporting_last_seen_at_epoch", 0) or 0)

    run_elapsed = float(run_state.get("run_elapsed_seconds", 0) or 0)
    if run_elapsed <= 0 and started > 0:
        anchor = ended if ended > 0 else time.time()
        run_elapsed = round(max(0, anchor - started), 1)

    report_delay = 0.0
    if started > 0 and ended > 0 and seen > ended:
        report_delay = round(max(0, seen - ended), 1)

    return {
        "run_elapsed_seconds": run_elapsed,
        "report_delay_seconds": report_delay,
        "is_completed": ended > 0,
        "started_at_epoch": started,
        "ended_at_epoch": ended,
    }


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def normalize_cycle_key(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return str(int(text))
    except Exception:
        return text


def normalize_mode(value):
    text = str(value or "").strip().lower()
    if text in {"explore", "explore_new", "exploration"}:
        return "explore"
    if text in {"exploit", "iterate_existing", "iteration", "iterate"}:
        return "exploit"
    return text or "unknown"


def normalize_spec_id(value):
    text = str(value or "").strip()
    if not text:
        return ""
    base = os.path.basename(text)
    suffix = ".strategy_spec.json"
    if base.endswith(suffix):
        base = base[: -len(suffix)]
    return base


def unique_preserve(seq):
    seen = set()
    out = []
    for item in seq:
        key = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def spec_variant_job_count(spec_paths):
    total = 0
    for spec_path in spec_paths:
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = json.load(f)
        except Exception:
            continue
        variants = spec.get("variants") or []
        names = {str(v.get("name") or "").strip().lower() for v in variants if str(v.get("name") or "").strip()}
        total += max(1, len(names))
    return total


def summarize_best_result(rows_dict):
    if not rows_dict:
        return None

    def sort_key(row):
        row_dict = dict(row) if not isinstance(row, dict) else row
        return (row_dict.get("score_total") or 0, row_dict.get("profit_factor") or 0, row_dict.get("total_trades") or 0)

    best = max(rows_dict, key=sort_key)
    return {
        "strategy_spec_id": best.get("strategy_spec_id"),
        "variant_id": best.get("variant_id"),
        "asset": best.get("asset"),
        "timeframe": best.get("timeframe"),
        "qscore": round(best.get("score_total") or 0, 4),
        "profit_factor": round(best.get("profit_factor") or 0, 4),
        "total_trades": int(best.get("total_trades") or 0),
        "decision": best.get("score_decision") or "unknown",
    }


def fetch_cycle_queue_metrics(cycle_id):
    try:
        conn = sqlite3.connect(DB)
        rows = conn.execute(
            """
            SELECT stage, status, notes
            FROM research_funnel_queue
            WHERE cycle_id = ?
            """,
            (int(cycle_id),),
        ).fetchall()
        conn.close()
    except Exception:
        rows = []

    out = {
        "total": 0,
        "queued": 0,
        "running": 0,
        "done": 0,
        "skipped": 0,
        "terminal_failures": 0,
        "integrity_skips": 0,
        "retryable_failures": 0,
        "done_ok": 0,
        "done_terminal": 0,
        "orphan_discards": 0,
        "completed_attempts": 0,
        "by_stage": {},
    }
    for stage, status, notes in rows:
        stage_key = str(stage or "unknown")
        status_key = str(status or "unknown")
        note_text = str(notes or "").lower()
        bucket = out["by_stage"].setdefault(stage_key, {"queued": 0, "running": 0, "done": 0, "skipped": 0, "completed_attempts": 0})
        bucket[status_key] = bucket.get(status_key, 0) + 1
        out[status_key] = out.get(status_key, 0) + 1
        out["total"] += 1

        is_terminal = '"status": "terminal_fail"' in note_text
        is_integrity_skip = '"status": "integrity_skip"' in note_text or ('integrity_skip:' in note_text and 'zero_' in note_text)
        is_orphan_discard = '"status": "orphan_discarded"' in note_text

        if status_key == "done":
            if is_terminal:
                out["terminal_failures"] += 1
                out["done_terminal"] += 1
                out["completed_attempts"] += 1
                bucket["completed_attempts"] += 1
            elif is_integrity_skip:
                out["integrity_skips"] += 1
                out["completed_attempts"] += 1
                bucket["completed_attempts"] += 1
            elif is_orphan_discard:
                out["orphan_discards"] += 1
            else:
                out["done_ok"] += 1
                out["completed_attempts"] += 1
                bucket["completed_attempts"] += 1
        elif status_key == "skipped":
            if is_integrity_skip:
                out["integrity_skips"] += 1
            out["completed_attempts"] += 1
            bucket["completed_attempts"] += 1
        elif status_key == "queued" and '"status": "retry"' in note_text:
            out["retryable_failures"] += 1
    return out


def phase_state(done=False, active=False, blocked=False):
    if blocked:
        return "⛔"
    if done:
        return "✅"
    if active:
        return "▶"
    return "○"


def derive_reflection_rationale(cycle_status, metrics):
    decisions = load_json_file(REFINEMENT_DECISIONS_PATH)
    if int(decisions.get("cycle_id") or 0) == int(metrics.get("cycle_id") or 0):
        parts = []
        for item in (decisions.get("strategy_decisions") or [])[:3]:
            if not isinstance(item, dict):
                continue
            spec_id = str(item.get("strategy_spec_id") or "").strip()
            decision = str(item.get("decision") or "").strip().lower()
            rationale = str(item.get("rationale") or "").strip()
            if spec_id and (decision or rationale):
                parts.append(f"{spec_id}: {decision or 'decision'} — {rationale or 'no rationale provided'}")
        if parts:
            return " | ".join(parts)
    rationale = str(cycle_status.get("rationale") or "").strip()
    return rationale or "Await next cycle orders."


def derive_next_cycle_focus(cycle_orders, cycle_status, metrics):
    decisions = load_json_file(REFINEMENT_DECISIONS_PATH)
    reflection = load_json_file(REFLECTION_PACKET_PATH)
    if int(decisions.get("cycle_id") or 0) == int(metrics.get("cycle_id") or 0):
        strategy_decisions = decisions.get("strategy_decisions") or []
        if isinstance(strategy_decisions, list) and strategy_decisions:
            counts = {"pass": 0, "refine": 0, "abort": 0}
            diagnoses = []
            for item in strategy_decisions:
                if not isinstance(item, dict):
                    continue
                decision = str(item.get("decision") or "").strip().lower()
                if decision in counts:
                    counts[decision] += 1
                diag = str(item.get("diagnosis_category") or "").strip()
                if diag:
                    diagnoses.append(diag)
            if counts["refine"] > 0:
                return f"Refine {counts['refine']} strategy{'ies' if counts['refine'] != 1 else ''}; dominant diagnosis: {', '.join(sorted(set(diagnoses))[:2]) or 'review evidence'}."
            if counts["pass"] > 0:
                return f"Promote {counts['pass']} strategy{'ies' if counts['pass'] != 1 else ''} to the candidate library and continue validation."
            if counts["abort"] > 0:
                return f"Abort {counts['abort']} sparse strategy{'ies' if counts['abort'] != 1 else ''} and rotate to a new lane."

    if int(reflection.get("cycle_id") or 0) == int(metrics.get("cycle_id") or 0):
        summary = reflection.get("decision_summary") or {}
        if int(summary.get("zero_trade") or 0) > 0:
            return f"Current batch is too sparse ({int(summary.get('zero_trade') or 0)} zero-trade outcome{'s' if int(summary.get('zero_trade') or 0) != 1 else ''}); rotate thesis or loosen entry grammar."

    focus = cycle_status.get("next_cycle_focus") or cycle_status.get("next_focus")
    if focus:
        return str(focus).strip()

    mode = metrics.get("mode", "unknown")
    if mode == "exploit":
        iterate_target = cycle_orders.get("iterate_target") or cycle_orders.get("specific_family_to_iterate")
        if iterate_target:
            return f"Exploit {iterate_target} with tighter batch variants."

    targets = cycle_orders.get("exploration_targets") or {}
    concepts = ", ".join(targets.get("concepts") or [])
    assets = ", ".join(targets.get("assets") or [])
    timeframes = ", ".join(targets.get("timeframes") or [])
    if mode == "explore" and any([concepts, assets, timeframes]):
        detail_bits = [bit for bit in [concepts, assets, timeframes] if bit]
        return "Continue exploration rotation across " + " | ".join(detail_bits)

    rotation_reason = str(cycle_orders.get("rotation_reason") or "").strip()
    if rotation_reason:
        return rotation_reason

    rationale = str(cycle_status.get("rationale") or "").strip()
    return rationale[:240] if rationale else "Await next cycle orders."


def build_cycle_metrics(cycle_id, rows, elapsed_seconds, backtest_count, run_state=None):
    rows_dict = [dict(r) if not isinstance(r, dict) else r for r in rows]
    cycle_specs = load_json_file(CURRENT_CYCLE_SPECS_PATH)
    cycle_status = load_json_file(CURRENT_CYCLE_STATUS_PATH)
    cycle_orders = load_json_file(os.path.join(ROOT, "agents", "quandalf", "memory", "cycle_orders.json"))
    run_state = run_state or load_run_state()
    timing = compute_timing_metrics(run_state)

    target_cycle_key = normalize_cycle_key(cycle_id)
    manifest_cycle_key = normalize_cycle_key(cycle_specs.get("cycle_id", ""))
    status_cycle_key = normalize_cycle_key(cycle_status.get("cycle_id", ""))
    orders_cycle_key = normalize_cycle_key(cycle_orders.get("cycle_id", cycle_id))

    status_matches_cycle = bool(status_cycle_key and status_cycle_key == target_cycle_key)
    manifest_matches_cycle = bool(manifest_cycle_key and manifest_cycle_key == target_cycle_key)
    orders_match_cycle = not orders_cycle_key or orders_cycle_key == target_cycle_key

    manifest_spec_paths = cycle_specs.get("spec_paths") or [] if manifest_matches_cycle else []
    status_spec_paths = cycle_status.get("spec_paths") or [] if status_matches_cycle else []
    spec_paths = unique_preserve([str(p).strip() for p in (status_spec_paths or manifest_spec_paths) if str(p).strip()])
    normalized_manifest_spec_ids = {normalize_spec_id(path) for path in spec_paths if normalize_spec_id(path)}
    row_spec_ids = {normalize_spec_id(r.get("strategy_spec_id")) for r in rows_dict if normalize_spec_id(r.get("strategy_spec_id"))}
    cycle_rows = [r for r in rows_dict if normalize_spec_id(r.get("strategy_spec_id")) in normalized_manifest_spec_ids] if normalized_manifest_spec_ids else []
    external_rows = [r for r in rows_dict if normalize_spec_id(r.get("strategy_spec_id")) not in normalized_manifest_spec_ids] if normalized_manifest_spec_ids else rows_dict

    specs_produced = len(spec_paths)
    if not specs_produced:
        specs_produced = int(cycle_specs.get("spec_count", 0) or 0) if manifest_matches_cycle else 0

    mode = normalize_mode(cycle_status.get("mode") or cycle_orders.get("mode") or cycle_status.get("research_direction") or cycle_orders.get("research_direction"))
    minimum_spec_count = safe_int(cycle_status.get("minimum_spec_count", cycle_orders.get("minimum_spec_count", 0)) or 0)
    maximum_spec_count = safe_int(cycle_status.get("maximum_spec_count", cycle_orders.get("maximum_spec_count", cycle_orders.get("max_variants", 0))) or 0)

    new_families = cycle_status.get("new_families", []) if status_matches_cycle else []
    iterated_families = cycle_status.get("iterated_families", []) if status_matches_cycle else []
    abandoned_families = cycle_status.get("abandoned_families", []) if status_matches_cycle else []

    completed_backtests = len({str(r.get('id')) for r in cycle_rows if r.get('id')})
    queue_metrics = fetch_cycle_queue_metrics(cycle_id)
    queued_backtests = int(queue_metrics.get("total") or 0) or spec_variant_job_count(manifest_spec_paths or spec_paths)
    queue_done = int(queue_metrics.get("done") or 0)
    queue_skipped = int(queue_metrics.get("skipped") or 0)
    queue_running = int(queue_metrics.get("running") or 0)
    queue_pending = int(queue_metrics.get("queued") or 0)
    queue_terminal_failures = int(queue_metrics.get("terminal_failures") or 0)
    queue_integrity_skips = int(queue_metrics.get("integrity_skips") or 0)
    queue_done_ok = int(queue_metrics.get("done_ok") or max(0, queue_done - queue_terminal_failures))
    if queued_backtests < completed_backtests:
        queued_backtests = completed_backtests

    pass_count = sum(1 for r in cycle_rows if str(r.get("score_decision") or "").lower() in {"pass", "promote"})
    promote_count = sum(1 for r in cycle_rows if str(r.get("score_decision") or "").lower() == "promote")
    fail_count = max(0, completed_backtests - pass_count)
    best_result = summarize_best_result(cycle_rows)
    best_qs = best_result.get("qscore", 0) if best_result else 0

    decisions_payload = load_json_file(REFINEMENT_DECISIONS_PATH)
    reflection_payload = load_json_file(REFLECTION_PACKET_PATH)
    has_reflection_note = (
        (status_matches_cycle and bool(str(cycle_status.get("rationale") or "").strip() or str(cycle_status.get("next_cycle_focus") or "").strip()))
        or int(decisions_payload.get("cycle_id") or 0) == int(cycle_id)
        or int(reflection_payload.get("cycle_id") or 0) == int(cycle_id)
    )

    state_warning = None
    if manifest_matches_cycle and not status_matches_cycle:
        state_warning = f"current_cycle_status lags active cycle {target_cycle_key} (status={status_cycle_key or 'missing'}, manifest={manifest_cycle_key or 'missing'})"
    elif manifest_matches_cycle and int(cycle_specs.get('spec_count', 0) or 0) == 0 and rows_dict:
        state_warning = f"active cycle {target_cycle_key} has no captured specs, but {len(rows_dict)} recent off-cycle result(s) are present"

    metrics = {
        "cycle_id": cycle_id,
        "cycle_key": target_cycle_key,
        "manifest_cycle_id": cycle_specs.get("cycle_id"),
        "status_cycle_id": cycle_status.get("cycle_id"),
        "orders_cycle_id": cycle_orders.get("cycle_id") if orders_match_cycle else None,
        "status_matches_cycle": status_matches_cycle,
        "manifest_matches_cycle": manifest_matches_cycle,
        "state_warning": state_warning,
        "mode": mode,
        "research_direction": cycle_status.get("research_direction") or cycle_orders.get("research_direction"),
        "minimum_spec_count": minimum_spec_count,
        "maximum_spec_count": maximum_spec_count,
        "target_asset": cycle_orders.get("target_asset"),
        "target_timeframe": cycle_orders.get("target_timeframe"),
        "iterate_target": cycle_orders.get("iterate_target") or cycle_orders.get("specific_family_to_iterate"),
        "exploration_targets": cycle_orders.get("exploration_targets") or {},
        "spec_paths": spec_paths,
        "spec_ids": sorted(normalized_manifest_spec_ids),
        "specs_produced": specs_produced,
        "specs_written": specs_produced,
        "new_families": new_families,
        "iterated_families": iterated_families,
        "abandoned_families": abandoned_families,
        "active_families": len(new_families) + len(iterated_families),
        "all_recent_rows": len(rows_dict),
        "cycle_rows": len(cycle_rows),
        "external_rows": len(external_rows),
        "cycle_results_present": bool(cycle_rows),
        "external_results_present": bool(external_rows),
        "backtests_queued": queued_backtests,
        "backtests_completed": completed_backtests,
        "backtests": completed_backtests,
        "queue_total": queued_backtests,
        "queue_pending": queue_pending,
        "queue_running": queue_running,
        "queue_done": queue_done,
        "queue_skipped": queue_skipped,
        "queue_done_ok": queue_done_ok,
        "queue_integrity_skips": queue_integrity_skips,
        "queue_terminal_failures": queue_terminal_failures,
        "queue_retryable_failures": int(queue_metrics.get("retryable_failures") or 0),
        "stage_kpis": {
            "specs_written": specs_produced,
            "queue_total": queued_backtests,
            "queue_pending": queue_pending,
            "queue_running": queue_running,
            "queue_done_ok": queue_done_ok,
            "queue_skipped": queue_skipped,
            "queue_integrity_skips": queue_integrity_skips,
            "queue_terminal_failures": queue_terminal_failures,
            "queue_orphan_discards": int(queue_metrics.get("orphan_discards") or 0),
            "db_results": completed_backtests,
            "pass": pass_count,
            "promote": promote_count,
            "train_runs": int((queue_metrics.get("by_stage") or {}).get("screen", {}).get("completed_attempts") or 0),
            "test_runs": int((queue_metrics.get("by_stage") or {}).get("full", {}).get("completed_attempts") or 0)
        },
        "pass_count": pass_count,
        "fail_count": fail_count,
        "promote_count": promote_count,
        "promotions": promote_count,
        "best_result": best_result,
        "best_qscore": best_qs,
        "next_cycle_focus": "",
        "rationale": "",
        "has_reflection_note": has_reflection_note,
        "elapsed_seconds": elapsed_seconds,
        "run_elapsed_seconds": timing["run_elapsed_seconds"],
        "report_delay_seconds": timing["report_delay_seconds"],
        "is_completed": timing["is_completed"],
        "started_at_epoch": timing["started_at_epoch"],
        "ended_at_epoch": timing["ended_at_epoch"],
    }
    metrics["next_cycle_focus"] = derive_next_cycle_focus(cycle_orders, cycle_status, metrics)
    metrics["rationale"] = derive_reflection_rationale(cycle_status, metrics)
    return metrics


def _decision_counts_for_cycle(cycle_id):
    decisions_payload = load_json_file(REFINEMENT_DECISIONS_PATH) or {}
    reflection_payload = load_json_file(REFLECTION_PACKET_PATH) or {}

    strategy_decisions = []
    if int(decisions_payload.get("cycle_id") or -1) == int(cycle_id):
        strategy_decisions = decisions_payload.get("strategy_decisions") or []

    counts = {
        "iterated": 0,
        "passed": 0,
        "aborted": 0,
        "promoted": 0,
        "decision_count": 0,
        "queue_decision_count": 0,
        "expected_queue_count": 0,
        "executed_queue_count": 0,
        "executed_queue_decision_count": 0,
        "queue_iterated": 0,
        "queue_passed": 0,
        "queue_aborted": 0,
    }

    executed_queue_ids = set()
    if int(reflection_payload.get("cycle_id") or -1) == int(cycle_id):
        for item in (reflection_payload.get("strategy_outcomes") or []):
            if not isinstance(item, dict):
                continue
            for q in (item.get("queue") or []):
                if not isinstance(q, dict):
                    continue
                queue_id = str(q.get("queue_id") or "").strip()
                if not queue_id:
                    continue
                counts["expected_queue_count"] += 1
                status = str(q.get("status") or "").strip().lower()
                if status in {"done", "skipped", "failed", "error", "complete", "completed"}:
                    executed_queue_ids.add(queue_id)
        counts["executed_queue_count"] = len(executed_queue_ids)

    if isinstance(strategy_decisions, list) and strategy_decisions:
        for item in strategy_decisions:
            if not isinstance(item, dict):
                continue
            decision = str(item.get("decision") or "").strip().lower()
            counts["decision_count"] += 1
            queue_decisions = item.get("queue_decisions") or []
            if isinstance(queue_decisions, list):
                counts["queue_decision_count"] += len(queue_decisions)
                for qd in queue_decisions:
                    if not isinstance(qd, dict):
                        continue
                    queue_id = str(qd.get("queue_id") or "").strip()
                    qdecision = str(qd.get("decision") or "").strip().lower()
                    if queue_id in executed_queue_ids:
                        counts["executed_queue_decision_count"] += 1
                        if qdecision == "refine":
                            counts["queue_iterated"] += 1
                        elif qdecision == "pass":
                            counts["queue_passed"] += 1
                        elif qdecision == "abort":
                            counts["queue_aborted"] += 1
            if decision == "refine":
                counts["iterated"] += 1
            elif decision == "pass":
                counts["passed"] += 1
            elif decision == "abort":
                counts["aborted"] += 1
        return counts

    if int(reflection_payload.get("cycle_id") or -1) == int(cycle_id):
        for item in (reflection_payload.get("strategy_outcomes") or []):
            if not isinstance(item, dict):
                continue
            action = str(item.get("recommended_action") or item.get("outcome") or "").strip().lower()
            if action in {"pending", "red_flag", "fix_only", "", "promote"}:
                continue
            counts["decision_count"] += 1
            if action == "refine":
                counts["iterated"] += 1
            elif action == "pass":
                counts["passed"] += 1
            elif action == "abort":
                counts["aborted"] += 1
    return counts


def build_log_card(cycle_id, rows, elapsed_seconds, backtest_count, run_state=None):
    metrics = build_cycle_metrics(cycle_id, rows, elapsed_seconds, backtest_count, run_state=run_state)
    run_elapsed = metrics.get("run_elapsed_seconds", elapsed_seconds)
    elapsed_str = f"{int(run_elapsed // 60)}m {int(run_elapsed % 60)}s" if run_elapsed else "?"

    decision_counts = _decision_counts_for_cycle(cycle_id)
    generated = metrics.get("specs_produced", 0)
    strategy_iterated = int(decision_counts.get("iterated") or len(metrics.get("iterated_families") or []))
    strategy_passed = int(decision_counts.get("passed") or metrics.get("pass_count", 0))
    new_families = len(metrics.get("new_families") or [])
    active_families = metrics.get("active_families", 0)
    family_aborted = len(metrics.get("abandoned_families") or [])
    integrity_zero_trades = int(metrics.get("queue_integrity_skips") or 0)
    train_runs = int(metrics.get("stage_kpis", {}).get("train_runs") or 0)
    test_runs = int(metrics.get("stage_kpis", {}).get("test_runs") or 0)
    completed_attempts = train_runs + test_runs
    executed_backtests = completed_attempts
    decided_total = int(decision_counts.get("decision_count") or 0)
    queue_decided_total = int(decision_counts.get("queue_decision_count") or 0)
    expected_queue_total = int(decision_counts.get("expected_queue_count") or 0)
    executed_queue_total = int(decision_counts.get("executed_queue_count") or 0)
    executed_queue_decided_total = int(decision_counts.get("executed_queue_decision_count") or 0)
    backtests = executed_backtests
    queue_passed = int(decision_counts.get("queue_passed") or 0)
    queue_iterated = int(decision_counts.get("queue_iterated") or 0)
    queue_aborted = int(decision_counts.get("queue_aborted") or 0)
    decision_payload = load_json_file(REFINEMENT_DECISIONS_PATH) or {}
    has_closed_decisions = int(decision_payload.get("cycle_id") or 0) == int(metrics.get("cycle_id") or 0) and bool(decision_payload.get("strategy_decisions"))
    if has_closed_decisions or decided_total > 0:
        passed = strategy_passed
        iterated = strategy_iterated
        aborted = int(decision_counts.get("aborted") or family_aborted)
    elif backtests > 0:
        passed = queue_passed
        iterated = queue_iterated
        aborted = queue_aborted
    else:
        passed = strategy_passed
        iterated = strategy_iterated
        aborted = int(decision_counts.get("aborted") or family_aborted)
    decision_basis = max(generated, backtests, decided_total)
    unresolved = max(0, decision_basis - (strategy_passed + strategy_iterated + int(decision_counts.get("aborted") or family_aborted)))
    unresolved_queue = max(0, executed_queue_total - executed_queue_decided_total)
    best_qs = metrics.get("best_qscore") or 0
    mode = metrics.get("mode") or "cycle"

    decisions_complete = (unresolved_queue == 0 and unresolved == 0 and (decided_total > 0 or executed_backtests == 0)) or has_closed_decisions
    if decisions_complete:
        if passed > 0:
            status_emoji = "✅"
        elif integrity_zero_trades > 0 or executed_backtests > 0:
            status_emoji = "⚠️"
        else:
            status_emoji = "🔄"
    else:
        status_emoji = "🔄" if executed_backtests == 0 else "⚠️"

    note_candidates = []
    if not decisions_complete:
        if unresolved_queue > 0:
            note_candidates.append(f"This {mode} cycle has {train_runs} completed train run{'s' if train_runs != 1 else ''} and {test_runs} completed test run{'s' if test_runs != 1 else ''}, with {unresolved_queue} rows still awaiting Quandalf's explicit pass / refine / abort judgment. This is in-flight evidence, not a final verdict.")
        elif executed_backtests == 0 and generated > 0:
            note_candidates.append(f"This {mode} cycle generated fresh work but no train/test executions have completed yet, so the batch is still gathering evidence before any strategy gets advanced or cut.")
        else:
            note_candidates.append(f"This {mode} cycle is still in progress. Evidence collection is ahead of decision closure, so final pass / refine / abort counts are intentionally withheld until Quandalf finishes judging the batch.")
    else:
        if passed > 0 and best_qs > 0:
            note_candidates.append(f"This {mode} cycle found real traction, with best QS {best_qs:.2f} and the strongest families now earning another round of refinement or validation.")
        if integrity_zero_trades > 0 and executed_backtests > 0:
            note_candidates.append(f"This {mode} cycle completed {train_runs} train run{'s' if train_runs != 1 else ''} and {test_runs} test run{'s' if test_runs != 1 else ''}. {aborted} strateg{'ies' if aborted != 1 else 'y'} resolved to abort after red-flag outcomes, and {iterated} resolved to refine.")
        if executed_backtests > 0 and passed == 0 and generated > 0 and integrity_zero_trades == 0:
            note_candidates.append(f"This {mode} cycle tested fresh ideas but none cleared the evidence gate, so the right move is to abandon these mechanisms and try a different concept or management style.")
        if family_aborted > 0 and best_qs > 0:
            note_candidates.append(f"This {mode} cycle cut {family_aborted} weak family{'ies' if family_aborted != 1 else ''} while preserving the better branch with best QS {best_qs:.2f} for the next decision pass.")
        if metrics.get("external_results_present"):
            note_candidates.append(f"This {mode} cycle is being judged only on its own batch, while {metrics['external_rows']} off-cycle result{'s' if metrics['external_rows'] != 1 else ''} were intentionally ignored to keep the card honest.")
        if not note_candidates:
            note_candidates.append(f"This {mode} cycle completed its judgment pass, but no convincing result was strong enough to change direction.")

    note = next((candidate for candidate in note_candidates if len(candidate) <= 350), note_candidates[-1])
    if len(note) > 350:
        note = f"This {mode} cycle is still building evidence, with best QS {best_qs:.2f} and the next decision waiting on cleaner current-cycle results." if best_qs > 0 else f"This {mode} cycle is still building evidence, and the next decision is waiting on cleaner current-cycle backtest results."

    train_failed = integrity_zero_trades if integrity_zero_trades > 0 else max(0, train_runs - test_runs)

    lines = []
    lines.append("🧪 Research" if not decisions_complete else "🔮 Reflection")
    lines.append(f"{status_emoji} | ▶️ {elapsed_str} | 🆔 {metrics['cycle_id']}")
    lines.append("○────────────activity────────────")
    if decisions_complete:
        lines.append(f"Pass: {passed}")
        lines.append(f"Iterate: {iterated}")
        lines.append(f"Abort: {aborted}")
    else:
        lines.append(f"Generated: {generated}")
        lines.append(f"Training: {train_runs}")
        lines.append(f"Testing: {test_runs}")
        lines.append(f"Failed: {train_failed}")
    lines.append("○─────────────note─────────────")
    lines.append(note)

    return "\n".join(lines), metrics


def count_backtests(rows):
    seen_ids = set()
    for row in rows:
        if isinstance(row, dict):
            row_id = row.get("id")
        else:
            row_id = row["id"] if "id" in row.keys() else None
        if row_id:
            seen_ids.add(str(row_id))
    return len(seen_ids)


def filter_rows_to_current_cycle(rows, cycle_id):
    metrics = build_cycle_metrics(cycle_id, rows, 0, count_backtests(rows))
    target_ids = set(metrics.get("spec_ids") or [])
    if not target_ids:
        return [], metrics
    cycle_rows = []
    for row in rows:
        row_dict = dict(row) if not isinstance(row, dict) else row
        if normalize_spec_id(row_dict.get("strategy_spec_id")) in target_ids:
            cycle_rows.append(row_dict)
    return cycle_rows, metrics


def write_cycle_metrics(metrics):
    try:
        os.makedirs(os.path.dirname(CURRENT_CYCLE_METRICS_PATH), exist_ok=True)
        with open(CURRENT_CYCLE_METRICS_PATH, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        should_write_batch_summary = (
            metrics.get("status_matches_cycle", False)
            and (
                bool(metrics.get("cycle_results_present"))
                or (int(metrics.get("specs_produced", 0) or 0) > 0 and int(metrics.get("external_rows", 0) or 0) == 0)
            )
        )
        if should_write_batch_summary:
            with open(CURRENT_CYCLE_BATCH_SUMMARY_PATH, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
    except Exception:
        pass


def load_card_state():
    state = {}
    try:
        if os.path.exists(CARD_STATE_PATH):
            with open(CARD_STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
    except Exception:
        state = {}
    cards = state.get("cards") if isinstance(state, dict) else None
    if not isinstance(cards, dict):
        cards = {}
        legacy = state.get("last_card") if isinstance(state, dict) else None
        if isinstance(legacy, dict):
            legacy_key = f"{int(legacy.get('cycle_id', -1) or -1)}:research"
            cards[legacy_key] = {
                "cycle_id": int(legacy.get("cycle_id", -1) or -1),
                "kind": "research",
                "fingerprint": legacy.get("fingerprint"),
                "sent_at_iso": legacy.get("sent_at_iso"),
                "preview": legacy.get("preview") or [],
            }
    return {"cards": cards}


def should_send_card(cycle_id, card_kind, card_text):
    fingerprint = hashlib.sha256(card_text.encode("utf-8")).hexdigest()
    state = load_card_state()
    cards = state.get("cards") or {}
    key = f"{int(cycle_id)}:{str(card_kind or 'research')}"
    last = cards.get(key)
    if not isinstance(last, dict):
        return True, fingerprint
    if last.get("fingerprint") == fingerprint:
        return False, fingerprint
    return True, fingerprint


def remember_card_send(cycle_id, card_kind, card_text, fingerprint):
    os.makedirs(os.path.dirname(CARD_STATE_PATH), exist_ok=True)
    state = load_card_state()
    cards = state.get("cards") or {}
    key = f"{int(cycle_id)}:{str(card_kind or 'research')}"
    cards[key] = {
        "cycle_id": int(cycle_id),
        "kind": str(card_kind or 'research'),
        "fingerprint": fingerprint,
        "sent_at_iso": datetime.now(timezone.utc).isoformat(),
        "preview": card_text.splitlines(),
    }
    state = {"cards": cards}
    with open(CARD_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def send_log_card(cycle_id, log_card, metrics=None):
    metrics = metrics or {}
    should_emit = (
        bool(metrics.get("cycle_results_present"))
        or int(metrics.get("backtests_completed", 0) or 0) > 0
        or int(metrics.get("specs_produced", 0) or 0) > 0
        or bool(metrics.get("state_warning"))
    )
    if not should_emit:
        return False

    card_kind = "reflection" if str(log_card).startswith("🔮 Reflection") else "research"
    should_send, fingerprint = should_send_card(cycle_id, card_kind, log_card)
    if not should_send:
        return False

    log_card_formatted = f"<pre>{log_card}</pre>"
    banner_name = "refinement.jpg" if card_kind == "reflection" else "cooking.jpg"
    banner_path = os.path.join(r"C:\Users\Clamps\.openclaw\workspace-oragorn\assets\banners", banner_name)
    sent_ok = False
    if os.path.exists(banner_path):
        proc = subprocess.run(
            [
                sys.executable,
                TG_SCRIPT,
                "--message",
                log_card_formatted,
                "--channel",
                "log",
                "--bot",
                "logron",
                "--photo",
                banner_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        sent_ok = proc.returncode == 0 and '"status": "sent"' in (proc.stdout or "")
    else:
        sent_ok = send_tg_as(log_card_formatted, "log", "logron")

    if not sent_ok:
        return False

    remember_card_send(cycle_id, card_kind, log_card, fingerprint)
    return True



def format_journal_html(raw_text):
    import html
    import re

    text = html.escape(raw_text)
    text = re.sub(r'^### (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def split_message(text, max_len=4000):
    if len(text) <= max_len:
        return [text]
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        split_at = text.rfind('\n', 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(text[:split_at])
        text = text[split_at:].lstrip('\n')
    return parts


def extract_latest_journal_entry(raw_text):
    text = str(raw_text or "").replace("\r\n", "\n").strip()
    if not text:
        return ""

    marker = "\n## Entry "
    idx = text.rfind(marker)
    if idx != -1:
        return text[idx + 1 :].strip()

    if text.startswith("## Entry "):
        return text

    return text


def sync_live_journal(cycle_id=None):
    source_text = ""
    if os.path.exists(JOURNAL_PATH):
        source_text = read_text_best_effort(JOURNAL_PATH)

    latest_entry = extract_latest_journal_entry(source_text)
    if not latest_entry and os.path.exists(DAILY_JOURNAL_PATH):
        latest_entry = read_text_best_effort(DAILY_JOURNAL_PATH).strip()

    latest_entry = latest_entry.strip()
    if not latest_entry:
        return ""

    os.makedirs(os.path.dirname(DAILY_JOURNAL_PATH), exist_ok=True)
    with open(DAILY_JOURNAL_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(latest_entry + "\n")
    with open(JOURNAL_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(latest_entry + "\n")

    os.makedirs(JOURNAL_ARCHIVE_DIR, exist_ok=True)
    now_local = datetime.now()
    archive_parts = [now_local.strftime("%Y-%m-%d-%H%M")]
    if cycle_id:
        archive_parts.append(f"cycle-{int(cycle_id)}")
    archive_path = os.path.join(JOURNAL_ARCHIVE_DIR, "-".join(archive_parts) + ".md")
    if not os.path.exists(archive_path):
        with open(archive_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(latest_entry + "\n")

    return latest_entry


def ensure_decision_closure(cycle_id, timeout_seconds=180):
    reflection_payload = load_json_file(REFLECTION_PACKET_PATH) or {}
    if int(reflection_payload.get("cycle_id") or -1) != int(cycle_id):
        return False, {"status": "error", "reason": "reflection_cycle_mismatch", "reflection_cycle_id": reflection_payload.get("cycle_id"), "cycle_id": cycle_id}
    try:
        proc = subprocess.run(
            [sys.executable, DECISION_COMPLETION_SCRIPT],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except Exception as e:
        return False, {"status": "error", "reason": "decision_completion_exception", "error": str(e), "cycle_id": cycle_id}

    payload = {}
    raw = (proc.stdout or "").strip()
    if raw:
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"status": "error", "reason": "decision_completion_output_parse_failed", "stdout": raw[-1000:]}
    else:
        payload = {"status": "error", "reason": "decision_completion_no_output", "stderr": (proc.stderr or "")[-1000:]}
    ok = proc.returncode == 0 and str(payload.get("status") or "").lower() == "ok"
    return ok, payload


def apply_queue_decisions(conn, cycle_id):
    decisions_payload = load_json_file(REFINEMENT_DECISIONS_PATH) or {}
    if int(decisions_payload.get("cycle_id") or -1) != int(cycle_id):
        return {"resolved": 0, "queue_ids": []}

    resolved = []
    for item in (decisions_payload.get("strategy_decisions") or []):
        if not isinstance(item, dict):
            continue
        for qd in (item.get("queue_decisions") or []):
            if not isinstance(qd, dict):
                continue
            queue_id = str(qd.get("queue_id") or "").strip()
            decision = str(qd.get("decision") or "").strip().lower()
            rationale = str(qd.get("rationale") or "").strip()
            if not queue_id or decision not in {"pass", "abort"}:
                continue
            row = conn.execute("SELECT status FROM research_funnel_queue WHERE id=?", (queue_id,)).fetchone()
            if not row:
                continue
            status = str(row[0] or "").strip().lower()
            if status not in {"queued", "running"}:
                continue
            notes = json.dumps({
                "status": "decision_resolved",
                "decision": decision,
                "rationale": rationale,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            })
            conn.execute(
                "UPDATE research_funnel_queue SET status='done', completed_at=?, started_at=NULL, notes=? WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), notes, queue_id),
            )
            resolved.append(queue_id)
    return {"resolved": len(resolved), "queue_ids": resolved}


def normalize_rule_block(block):
    if isinstance(block, dict):
        long_rules = block.get("long") or []
        short_rules = block.get("short") or []
        return {"long": list(long_rules), "short": list(short_rules)}
    if isinstance(block, list):
        return {"long": list(block), "short": list(block)}
    return {"long": [], "short": []}


def has_minimum_rules(spec):
    entries = normalize_rule_block(spec.get("entry_rules"))
    exits = normalize_rule_block(spec.get("exit_rules"))
    return any(entries.values()) and any(exits.values())


def indicator_signature(spec):
    indicators = spec.get("indicators") or []
    names = []
    for item in indicators:
        if isinstance(item, str):
            names.append(item.lower())
        elif isinstance(item, dict):
            names.append(str(item.get("name") or "").lower())
    return "|".join(sorted(x for x in names if x))


def derive_family_name(spec):
    explicit = str(spec.get("family_name") or "").strip()
    if explicit:
        return explicit
    signature = indicator_signature(spec)
    if signature:
        return signature.replace("|", "-")[:120]
    return str(spec.get("name") or spec.get("id") or "unknown-family").strip().lower().replace(" ", "-")


def conceptual_duplicate_warning(conn, signature):
    if not signature:
        return None
    rows = conn.execute(
        """
        SELECT strategy_spec_id, strategy_family
        FROM backtest_results
        WHERE COALESCE(strategy_family, '') <> ''
        ORDER BY ts_iso DESC
        LIMIT 10
        """
    ).fetchall()
    for row in rows:
        family = str(row[1] or "").strip().lower().replace("-", "|")
        if family == signature:
            return row[0]
    return None


def family_is_killed(conn, family_name):
    row = conn.execute(
        "SELECT COUNT(*) FROM backtest_results WHERE lower(COALESCE(strategy_family, '')) = lower(?) AND COALESCE(killed, 0) = 1",
        (family_name,),
    ).fetchone()
    return bool(row and row[0])


def get_family_context(conn, family_name):
    rows = conn.execute(
        """
        SELECT id, ts_iso, score_decision, score_total, family_generation
        FROM backtest_results
        WHERE lower(COALESCE(strategy_family, '')) = lower(?)
        ORDER BY ts_iso DESC
        """,
        (family_name,),
    ).fetchall()
    parent_id = rows[0][0] if rows else None
    next_generation = (int(rows[0][4] or 1) + 1) if rows else 1
    return rows, parent_id, next_generation


def regime_has_positive_edge(regime_scores):
    if isinstance(regime_scores, str):
        try:
            regime_scores = json.loads(regime_scores)
        except Exception:
            regime_scores = {}
    for data in (regime_scores or {}).values():
        try:
            if float((data or {}).get("profit_factor") or 0.0) > MIN_POSITIVE_REGIME_PF:
                return True
        except Exception:
            continue
    return False


def load_fallback_control():
    return load_json_file(FALLBACK_CONTROL_PATH)


def analyze_result_row(row):
    metrics = {}
    score_flags = []
    directional_bias = None
    suspicious = False
    auto_fail = False
    try:
        metrics = json.loads(row[9] or "{}") if row[9] else {}
    except Exception:
        metrics = {}
    try:
        score_flags = json.loads(row[13] or "[]") if row[13] else []
    except Exception:
        score_flags = []
    trades_blob = metrics.get("outofsample", {}).get("trades") or metrics.get("trades") or []
    if row[6] < MIN_PASS_TRADES:
        auto_fail = True
        score_flags.append("auto_fail_low_trade_count")
        score_flags.append("below_scoring_floor")
    if (row[4] or 0) > 10 and (row[6] or 0) < 20:
        suspicious = True
        score_flags.append("suspicious_overfit")
    if trades_blob:
        long_count = sum(1 for t in trades_blob if str(t.get("direction", "")).lower() == "long")
        short_count = sum(1 for t in trades_blob if str(t.get("direction", "")).lower() == "short")
        total = long_count + short_count
        if total > 0:
            dominant = max(long_count, short_count) / total
            if dominant > 0.8:
                directional_bias = round(dominant * 100.0, 1)
                score_flags.append("directional_bias")
    return auto_fail, suspicious, directional_bias, json.dumps(sorted(set(score_flags)))


def apply_family_kill_rules(conn, family_name):
    rows = conn.execute(
        """
        SELECT id, score_decision, score_total, family_generation, total_trades, mutation_type
        FROM backtest_results
        WHERE lower(COALESCE(strategy_family, '')) = lower(?)
        ORDER BY ts_iso ASC
        """,
        (family_name,),
    ).fetchall()
    if not rows:
        return None

    best_qs = max(float(r[2] or 0) for r in rows)
    max_generation = max(int(r[3] or 1) for r in rows)
    pass_count = sum(1 for r in rows if str(r[1] or "").lower() in {"pass", "promote"})
    best_trades = max(int(r[4] or 0) for r in rows)
    first_qs = float(rows[0][2] or 0.0)
    total_improvement = round(best_qs - first_qs, 4)
    zero_trade_count = sum(1 for r in rows if int(r[4] or 0) == 0)
    weak_pf_first = float(rows[0][2] or 0.0) < 0.5
    structural_fail_count = sum(1 for r in rows if str(r[5] or "").lower() in {"param_tweak", "reclassified_refine", "initial"} and str(r[1] or "").lower() == "fail")

    reason = None
    if zero_trade_count > 0:
        reason = "0 trades observed in family run"
    elif best_trades < SCREEN_MIN_TRADES and max_generation >= 1:
        reason = f"screen-stage density below {SCREEN_MIN_TRADES} trades"
    elif structural_fail_count >= 3:
        reason = "3 structurally similar fails"
    elif weak_pf_first:
        reason = "PF/QScore too weak on first full backtest"
    elif max_generation >= 3 and total_improvement <= 0.1:
        reason = f"3+ refinement rounds with total QScore improvement <= 0.1 ({total_improvement:.3f})"
    elif max_generation >= 5 and pass_count == 0:
        reason = f"5+ generations with no PASS result"
    elif max_generation >= 5 and best_qs < 0.5:
        reason = "best variant still below PASS threshold after 5 generations"
    elif max_generation >= 3 and best_trades < MIN_PASS_TRADES:
        reason = f"best variant trade_count still < {MIN_PASS_TRADES} after 3 generations"

    if not reason:
        return None

    conn.execute(
        "UPDATE backtest_results SET killed = 1 WHERE lower(COALESCE(strategy_family, '')) = lower(?)",
        (family_name,),
    )
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(mechanism_priors)")}
        if "last_rotation_reason" not in existing:
            conn.execute("ALTER TABLE mechanism_priors ADD COLUMN last_rotation_reason TEXT")
        if "last_rotation_family" not in existing:
            conn.execute("ALTER TABLE mechanism_priors ADD COLUMN last_rotation_family TEXT")
        mechanism = "unknown"
        latest_spec_id_row = conn.execute("SELECT strategy_spec_id FROM backtest_results WHERE lower(COALESCE(strategy_family,''))=lower(?) ORDER BY ts_iso DESC LIMIT 1", (family_name,)).fetchone()
        if latest_spec_id_row and latest_spec_id_row[0]:
            spec_path = os.path.join(SPECS_DIR, str(latest_spec_id_row[0]) + '.strategy_spec.json')
            if os.path.exists(spec_path):
                with open(spec_path, 'r', encoding='utf-8') as handle:
                    spec = json.load(handle)
                mechanism = str(spec.get('edge_mechanism') or 'unknown').strip()
        conn.execute(
            "INSERT INTO mechanism_priors(mechanism, success_rate, total_tested, avg_best_qs, priority_modifier, updated_at, last_rotation_reason, last_rotation_family) VALUES (?, 0, 0, 0, 0.5, ?, ?, ?) ON CONFLICT(mechanism) DO UPDATE SET priority_modifier=MIN(priority_modifier, 0.5), updated_at=excluded.updated_at, last_rotation_reason=excluded.last_rotation_reason, last_rotation_family=excluded.last_rotation_family",
            (mechanism, datetime.now(timezone.utc).isoformat(), reason, family_name),
        )
    except Exception:
        pass

    event_message = f"Family {family_name} auto-rotated: {reason}"
    log_event("family_auto_rotated", "logron", event_message, severity="warn", pipeline="research_cycle", step="postprocess")
    status = load_json_file(CURRENT_CYCLE_STATUS_PATH)
    status.setdefault("family_kill_events", []).append({"ts_iso": datetime.now(timezone.utc).isoformat(), "family": family_name, "reason": reason})
    status.setdefault("abandoned_families", []).append(family_name)
    with open(CURRENT_CYCLE_STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)
    return reason


def backtest_new_specs():
    if not os.path.exists(SPECS_DIR):
        return 0

    conn = sqlite3.connect(DB)
    backtested = 0

    for f in os.listdir(SPECS_DIR):
        if not f.endswith(".strategy_spec.json"):
            continue

        spec_path = os.path.join(SPECS_DIR, f)
        file_spec_id = f.replace(".strategy_spec.json", "")

        try:
            with open(spec_path, "r", encoding="utf-8") as fh:
                spec = json.load(fh)
            explicit_spec_id = (spec.get("id") or "").strip()
            spec_ids = [file_spec_id]
            if explicit_spec_id and explicit_spec_id not in spec_ids:
                spec_ids.append(explicit_spec_id)

            asset = str(spec.get("asset", "ETH")).strip()
            timeframe = str(spec.get("timeframe", "4h")).strip()
            variants = spec.get("variants", [])
            if not variants:
                continue
            if not has_minimum_rules(spec):
                log_event("spec_rejected", "logron", f"Rejected malformed spec {file_spec_id}: missing entry or exit rules", severity="warn", artifact_id=file_spec_id, pipeline="research_cycle", step="validation")
                continue

            family_name = derive_family_name(spec)
            duplicate_of = conceptual_duplicate_warning(conn, indicator_signature(spec))
            if duplicate_of:
                log_event("spec_duplicate_warning", "logron", f"Spec {file_spec_id} conceptually duplicates recent spec {duplicate_of}", severity="warn", artifact_id=file_spec_id, pipeline="research_cycle", step="validation")
            if family_is_killed(conn, family_name):
                log_event("spec_rejected", "logron", f"Rejected spec {file_spec_id}: family {family_name} already killed", severity="warn", artifact_id=file_spec_id, pipeline="research_cycle", step="validation")
                continue

            family_rows, parent_id, next_generation = get_family_context(conn, family_name)
            validation_targets = spec.get("validation_targets") or []
            validation_target = json.dumps(validation_targets[0]) if validation_targets else None
            placeholders = ",".join("?" * len(spec_ids))
            existing_for_spec = conn.execute(
                f"SELECT COUNT(*) FROM backtest_results WHERE strategy_spec_id IN ({placeholders})",
                tuple(spec_ids),
            ).fetchone()[0]
            if existing_for_spec > 0:
                continue

            seen_variant_names = set()
            for v in variants:
                vname = str(v.get("name", "default")).strip()
                if not vname or vname in seen_variant_names:
                    continue
                seen_variant_names.add(vname)

                try:
                    balrog_result = subprocess.run(
                        [sys.executable, BALROG, "--spec", spec_path],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if balrog_result.returncode != 0:
                        try:
                            balrog_out = json.loads(balrog_result.stdout or "{}")
                            errors = balrog_out.get("errors", [])
                            print(f"Balrog BLOCKED {f}: {errors}", file=sys.stderr)
                            log_event("balrog_block", "balrog", f"Blocked spec {file_spec_id}: {errors}", severity="warn", artifact_id=file_spec_id, pipeline="research_cycle", step="validation")
                        except Exception:
                            print(f"Balrog BLOCKED {f}: validation failed", file=sys.stderr)
                            log_event("balrog_block", "balrog", f"Blocked spec {file_spec_id}: validation failed", severity="warn", artifact_id=file_spec_id, pipeline="research_cycle", step="validation")
                        continue

                    existing_variant = conn.execute(
                        f"""
                        SELECT COUNT(*) FROM backtest_results
                        WHERE strategy_spec_id IN ({placeholders})
                          AND lower(variant_id) = lower(?)
                          AND lower(asset) = lower(?)
                          AND lower(timeframe) = lower(?)
                        """,
                        tuple(spec_ids + [vname, asset, timeframe]),
                    ).fetchone()[0]
                    if existing_variant > 0:
                        continue

                    screen_cmd = [
                        sys.executable,
                        BACKTESTER,
                        "--asset", asset,
                        "--tf", timeframe,
                        "--strategy-spec", spec_path,
                        "--variant", vname,
                        "--stage", "screen",
                        "--strategy-family", family_name,
                        "--mutation-type", "initial",
                        "--family-generation", str(next_generation),
                    ]
                    if parent_id:
                        screen_cmd.extend(["--parent-id", parent_id])
                    if validation_target:
                        screen_cmd.extend(["--validation-target", validation_target])
                    screen_result = subprocess.run(screen_cmd, capture_output=True, text=True, timeout=120)
                    screen_payload = json.loads(screen_result.stdout or "{}") if (screen_result.stdout or "").strip() else {}
                    if screen_result.returncode != 0 or not screen_payload.get("screen_passed"):
                        log_event("screen_failed", "frodex", f"Screen failed for {file_spec_id} variant {vname}", severity="warn", artifact_id=file_spec_id, pipeline="research_cycle", step="backtest")
                        continue

                    result = subprocess.run(
                        [
                            sys.executable,
                            BACKTESTER,
                            "--asset",
                            asset,
                            "--tf",
                            timeframe,
                            "--strategy-spec",
                            spec_path,
                            "--variant",
                            vname,
                            "--stage",
                            "full",
                            "--strategy-family",
                            family_name,
                            "--mutation-type",
                            "screen_passed",
                            "--family-generation",
                            str(next_generation),
                        ] + (["--parent-id", parent_id] if parent_id else []) + (["--validation-target", validation_target] if validation_target else []),
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if result.returncode == 0:
                        backtested += 1
                        bt_row = conn.execute(
                            f"""
                            SELECT id, strategy_family, parent_id, family_generation, profit_factor, max_drawdown_pct, total_trades, win_rate_pct, score_total, metrics, score_decision, mutation_type, stage, score_flags
                            FROM backtest_results
                            WHERE strategy_spec_id IN ({placeholders})
                              AND lower(variant_id) = lower(?)
                              AND lower(asset) = lower(?)
                              AND lower(timeframe) = lower(?)
                              AND stage = 'full'
                            ORDER BY ts_iso DESC LIMIT 1
                            """,
                            tuple(spec_ids + [vname, asset, timeframe]),
                        ).fetchone()
                        result_id = bt_row[0] if bt_row else None
                        pf = bt_row[4] if bt_row and bt_row[4] is not None else 0
                        qs = bt_row[8] if bt_row and bt_row[8] is not None else 0
                        if bt_row:
                            auto_fail, suspicious, directional_bias, updated_flags = analyze_result_row(bt_row)
                            if auto_fail:
                                conn.execute("UPDATE backtest_results SET score_decision = 'fail', score_total = 0.0, score_grade = 'F', score_flags = ? WHERE id = ?", (updated_flags, result_id))
                                qs = 0
                            elif suspicious or directional_bias:
                                conn.execute("UPDATE backtest_results SET score_flags = ? WHERE id = ?", (updated_flags, result_id))
                            conn.commit()
                            kill_reason = apply_family_kill_rules(conn, bt_row[1] or family_name)
                            details = [f"PF {pf}", f"QS {qs}", f"family={bt_row[1]}", f"parent={bt_row[2]}", f"gen={bt_row[3]}"]
                            if suspicious:
                                details.append("suspicious_overfit")
                            if directional_bias:
                                details.append(f"directional_bias={directional_bias}%")
                            if kill_reason:
                                details.append("family_killed")
                            log_event(
                                "backtest_complete",
                                "frodex",
                                f"Backtested {file_spec_id} variant {vname}: " + ", ".join(details),
                                artifact_id=result_id,
                                pipeline="research_cycle",
                                step="backtest",
                            )
                    else:
                        print(f"Backtest failed for {vname}: {result.stderr[:200]}", file=sys.stderr)
                except Exception as e:
                    print(f"Backtest error for {vname}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Spec read failed for {f}: {e}", file=sys.stderr)

    conn.close()
    return backtested




def update_mechanism_priors(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS mechanism_priors (mechanism TEXT PRIMARY KEY, success_rate REAL, total_tested INTEGER, avg_best_qs REAL, priority_modifier REAL DEFAULT 1.0, updated_at TEXT)")
    rows = conn.execute("SELECT strategy_spec_id, score_decision, score_total FROM backtest_results WHERE COALESCE(strategy_spec_id,'') <> ''").fetchall()
    by_mech = {}
    for spec_id, decision, score_total in rows:
        spec_path = os.path.join(SPECS_DIR, str(spec_id) + '.strategy_spec.json')
        if not os.path.exists(spec_path):
            continue
        try:
            with open(spec_path, 'r', encoding='utf-8') as handle:
                spec = json.load(handle)
        except Exception:
            continue
        mech = str(spec.get('edge_mechanism') or 'unknown').strip()
        bucket = by_mech.setdefault(mech, {'tested': 0, 'success': 0, 'best': []})
        bucket['tested'] += 1
        if str(decision or '').lower() in ('pass', 'promote'):
            bucket['success'] += 1
        bucket['best'].append(float(score_total or 0.0))
    updated = []
    for mech, data in by_mech.items():
        tested = int(data['tested'])
        success_rate = round((data['success'] / tested) * 100.0, 2) if tested else 0.0
        avg_best_qs = round(sum(data['best']) / len(data['best']), 4) if data['best'] else 0.0
        if success_rate > 30.0:
            modifier = 1.5
        elif success_rate < 10.0 and tested >= 10:
            modifier = 0.5
        else:
            modifier = 1.0
        conn.execute("INSERT INTO mechanism_priors(mechanism, success_rate, total_tested, avg_best_qs, priority_modifier, updated_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(mechanism) DO UPDATE SET success_rate=excluded.success_rate, total_tested=excluded.total_tested, avg_best_qs=excluded.avg_best_qs, priority_modifier=excluded.priority_modifier, updated_at=excluded.updated_at", (mech, success_rate, tested, avg_best_qs, modifier, datetime.now(timezone.utc).isoformat()))
        updated.append({'mechanism': mech, 'success_rate': success_rate, 'total_tested': tested, 'avg_best_qs': avg_best_qs, 'priority_modifier': modifier})
    return updated


def update_portability_scores(conn):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(backtest_results)")}
    if 'portability_score' not in existing:
        try:
            conn.execute("ALTER TABLE backtest_results ADD COLUMN portability_score REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    promote_rows = conn.execute("SELECT id, strategy_spec_id, variant_id, asset, timeframe FROM backtest_results WHERE lower(COALESCE(score_decision,'')) = 'promote' AND stage = 'full'").fetchall()
    updated = []
    for result_id, spec_id, variant_id, asset, timeframe in promote_rows:
        validations = conn.execute("SELECT asset, timeframe, score_decision FROM backtest_results WHERE parent_id = ? AND stage = 'validation'", (result_id,)).fetchall()
        passed = sum(1 for _, _, decision in validations if str(decision or '').lower() in ('pass', 'promote'))
        if passed <= 0:
            portability = 0.0
        elif passed <= 2:
            portability = 25.0 * passed
        else:
            portability = min(100.0, 75.0 + (passed - 3) * 12.5)
        conn.execute("UPDATE backtest_results SET portability_score = ? WHERE id = ?", (portability, result_id))
        updated.append({'result_id': result_id, 'validation_count': len(validations), 'passed': passed, 'portability_score': portability})
    return updated

def extract_lessons(rows):
    conn = sqlite3.connect(DB)
    lessons_added = 0

    for r in rows:
        if not r["total_trades"] or r["total_trades"] == 0:
            continue

        pf = r["profit_factor"] or 0
        dd = r["max_drawdown_pct"] or 0
        trades = r["total_trades"]
        qs = r["score_total"] or 0
        decision = r["score_decision"] or "?"
        spec_id = r["strategy_spec_id"] or "unknown"
        result_id = r["id"]

        existing = conn.execute("SELECT id FROM lessons WHERE backtest_result_id = ?", (result_id,)).fetchone()
        if existing:
            continue

        if pf < 0.5:
            observation = f"Strategy {spec_id} on {r['asset']}/{r['timeframe']} has very low PF ({pf:.3f}). Entry logic may be anti-correlated with price movement."
            implication = "Consider inverting entry conditions or switching to a different indicator combination."
        elif pf < 1.0:
            observation = f"Strategy {spec_id} on {r['asset']}/{r['timeframe']} is slightly losing (PF {pf:.3f}). Edge exists but costs eat it."
            implication = "Try tightening stops, widening TP, or adding a regime filter to trade only in favorable conditions."
        elif pf >= 1.0 and trades < MIN_PASS_TRADES:
            observation = f"Strategy {spec_id} on {r['asset']}/{r['timeframe']} shows thin edge (PF {pf:.3f}) but too few trades ({trades}). Mechanism is too sparse."
            implication = "Abandon this sparse mechanism. Do not relax triggers to chase trade count; find a denser concept instead."
        elif pf >= 1.5:
            observation = f"Strategy {spec_id} on {r['asset']}/{r['timeframe']} shows strong edge (PF {pf:.3f}, {trades} trades). Worth iterating."
            implication = "Test across multiple assets for robustness. If PF holds, candidate for promotion."
        else:
            observation = f"Strategy {spec_id} on {r['asset']}/{r['timeframe']}: PF {pf:.3f}, DD {dd:.1f}%, {trades} trades, QScore {qs:.2f} ({decision})."
            implication = "Marginal edge. Consider parameter optimization or regime filtering."

        lesson_id = f"lesson_{result_id}"
        conn.execute(
            """
            INSERT OR IGNORE INTO lessons (
                id, ts_iso, backtest_result_id, strategy_spec_id, lesson_type,
                observation, implication, actionable, suggested_action, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson_id,
                datetime.now(timezone.utc).isoformat(),
                result_id,
                spec_id,
                "backtest_analysis",
                observation,
                implication,
                1,
                implication,
                "medium",
            ),
        )
        lessons_added += 1

    conn.commit()
    conn.close()
    return lessons_added


def check_fallback_dominance(conn):
    try:
        control = load_fallback_control()
        fallback_share = float(control.get("fallback_share_10_cycle") or 0.0)
        if fallback_share > 0.2:
            log_event("fallback_dominance_warning", "logron", f"Fallback dominance detected: {fallback_share*100:.1f}% of last 10 cycles used fallback — Quandalf may be stuck", severity="warn", pipeline="research_cycle", step="postprocess")
            return True
    except Exception:
        pass
    return False


def validate_and_classify_specs(conn, cycle_id):
    spec_paths = []
    specs_dir = SPECS_DIR
    if os.path.exists(specs_dir):
        for fname in os.listdir(specs_dir):
            if fname.endswith(".strategy_spec.json"):
                spec_paths.append(os.path.join(specs_dir, fname))

    recent_results = conn.execute(
        "SELECT strategy_spec_id FROM backtest_results ORDER BY ts_iso DESC LIMIT 10"
    ).fetchall()
    recent_specs = {}
    for (spec_id,) in recent_results:
        spec_path = os.path.join(specs_dir, f"{spec_id}.strategy_spec.json")
        if os.path.exists(spec_path):
            try:
                with open(spec_path, 'r', encoding='utf-8') as f:
                    recent_specs[spec_id] = json.load(f)
            except Exception:
                pass

    reclassified = []
    for spec_path in spec_paths:
        try:
            with open(spec_path, 'r', encoding='utf-8') as f:
                spec = json.load(f)
        except Exception:
            continue

        declared_mode = str(spec.get("research_mode") or spec.get("mode") or "explore").lower()
        if declared_mode != "explore":
            continue

        spec_indicators = set()
        for item in spec.get("indicators") or []:
            token = str(item if isinstance(item, str) else item.get("name") if isinstance(item, dict) else "").strip().upper()
            if token:
                spec_indicators.add(token.split("_")[0])

        spec_exit = set()
        for side, rules in (spec.get("exit_rules") or {}).items() if isinstance(spec.get("exit_rules"), dict) else []:
            for rule in rules or []:
                text = str(rule or "").lower()
                if "time stop" in text:
                    spec_exit.add("time_stop")
                if "trailing" in text:
                    spec_exit.add("trailing_stop")

        tm = spec.get("trade_management") if isinstance(spec.get("trade_management"), dict) else {}
        spec_tm = (str(tm.get("entry_style") or "one_shot").strip().lower(), str(tm.get("exit_style") or "one_shot").strip().lower())
        spec_regime = str(spec.get("expected_regime") or "").strip().lower()
        spec_asset = str(spec.get("primary_asset") or spec.get("asset") or "").strip().upper()
        spec_holding = tuple(sorted(holding for holding in [
            'time_stop' if ((tm.get('risk_management') or {}).get('time_stop_bars') is not None) else '',
            'position_stages' if tm.get('position_stages') else ''
        ] if holding))

        truly_new = True
        for recent_id, recent_spec in recent_specs.items():
            recent_indicators = set()
            for item in recent_spec.get("indicators") or []:
                token = str(item if isinstance(item, str) else item.get("name") if isinstance(item, dict) else "").strip().upper()
                if token:
                    recent_indicators.add(token.split("_")[0])

            recent_exit = set()
            for side, rules in (recent_spec.get("exit_rules") or {}).items() if isinstance(recent_spec.get("exit_rules"), dict) else []:
                for rule in rules or []:
                    text = str(rule or "").lower()
                    if "time stop" in text:
                        recent_exit.add("time_stop")
                    if "trailing" in text:
                        recent_exit.add("trailing_stop")

            recent_tm_obj = recent_spec.get("trade_management") if isinstance(recent_spec.get("trade_management"), dict) else {}
            recent_tm = (str(recent_tm_obj.get("entry_style") or "one_shot").strip().lower(), str(recent_tm_obj.get("exit_style") or "one_shot").strip().lower())
            recent_regime = str(recent_spec.get("expected_regime") or "").strip().lower()
            recent_asset = str(recent_spec.get("primary_asset") or recent_spec.get("asset") or "").strip().upper()
            recent_holding = tuple(sorted(holding for holding in [
                'time_stop' if ((recent_tm_obj.get('risk_management') or {}).get('time_stop_bars') is not None) else '',
                'position_stages' if recent_tm_obj.get('position_stages') else ''
            ] if holding))

            differences = 0
            if spec_indicators != recent_indicators:
                differences += 1
            if spec_exit != recent_exit:
                differences += 1
            if spec_tm != recent_tm:
                differences += 1
            if spec_regime != recent_regime:
                differences += 1
            if spec_asset != recent_asset:
                differences += 1
            if spec_holding != recent_holding:
                differences += 1

            if differences < 2:
                truly_new = False
                break

        if not truly_new:
            spec_id = spec.get("id") or os.path.basename(spec_path).replace(".strategy_spec.json", "")
            spec["research_mode"] = "refine"
            spec["mutation_type"] = "reclassified_refine"
            with open(spec_path, 'w', encoding='utf-8') as f:
                json.dump(spec, f, indent=2)
            log_event("explore_reclassified", "logron", f"Reclassified {spec_id} from explore to refine — parameter change only", severity="info", pipeline="research_cycle", step="validation")
            reclassified.append(spec_id)

    return reclassified


def main():

    p = argparse.ArgumentParser()
    p.add_argument("--since-minutes", type=int, default=30)
    p.add_argument("--send-card-only", action="store_true")
    p.add_argument("--backfill-unbacktested", action="store_true")
    a = p.parse_args()

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=a.since_minutes)).isoformat()

    if a.send_card_only:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, strategy_spec_id, variant_id, asset, timeframe,
                   profit_factor, max_drawdown_pct, total_trades, win_rate_pct,
                   score_total, score_decision, ts_iso
            FROM backtest_results
            WHERE ts_iso >= ?
            GROUP BY id
            ORDER BY ts_iso DESC
            """,
            (cutoff,),
        ).fetchall()
        total_rows = conn.execute("SELECT COUNT(*) FROM backtest_results").fetchone()[0]
        conn.close()

        run_state = observe_run_state()
        cycle_id = resolve_reporting_cycle_id(run_state)
        sync_cycle_status_to_active(cycle_id)
        run_state = observe_run_state(cycle_id)
        timing = compute_timing_metrics(run_state)
        elapsed_seconds = timing["run_elapsed_seconds"]

        backtest_count = count_backtests(rows)
        log_card, metrics = build_log_card(cycle_id, rows, elapsed_seconds, backtest_count, run_state=run_state)
        write_cycle_metrics(metrics)
        sent = send_log_card(cycle_id, log_card, metrics=metrics)

        status = "card_sent" if sent else ("state_warning" if metrics.get("state_warning") else "card_skipped_duplicate")
        print(json.dumps({"status": status, "since_minutes": a.since_minutes, "cycle_id": cycle_id, "rows": len(rows), "backtests": backtest_count, "total_in_db": total_rows, "card_metrics": metrics}))
        return

    new_backtests = backtest_new_specs() if a.backfill_unbacktested else 0
    log_token_event("frodex", "research_cycle", f"cycle-postprocess run; new_backtests={new_backtests}")
    start_time = time.time()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, strategy_spec_id, variant_id, asset, timeframe,
               profit_factor, max_drawdown_pct, total_trades, win_rate_pct,
               score_total, score_decision, ts_iso, strategy_family
        FROM backtest_results
        WHERE ts_iso >= ?
        GROUP BY id
        ORDER BY ts_iso DESC
        """,
        (cutoff,),
    ).fetchall()

    total_rows = conn.execute("SELECT COUNT(*) FROM backtest_results").fetchone()[0]
    
    check_fallback_dominance(conn)
    cycle_id_preview = resolve_reporting_cycle_id(load_run_state())
    validate_and_classify_specs(conn, cycle_id_preview)
    
    families_to_check = set()
    for row in rows:
        family = str(row["strategy_family"] or "").strip()
        if family:
            families_to_check.add(family)
    
    for family in families_to_check:
        apply_family_kill_rules(conn, family)
    
    conn.close()

    if not rows:
        cycle_id = resolve_reporting_cycle_id(load_run_state())
        run_state = finalize_run_state(cycle_id)
        cycle_id = resolve_reporting_cycle_id(run_state)
        sync_cycle_status_to_active(cycle_id)
        timing = compute_timing_metrics(run_state)
        elapsed_seconds = timing["run_elapsed_seconds"]
        log_card, metrics = build_log_card(cycle_id, [], elapsed_seconds, 0, run_state=run_state)
        write_cycle_metrics(metrics)
        sent = send_log_card(cycle_id, log_card, metrics=metrics)
        if int(metrics.get("queue_terminal_failures", 0) or 0) > 0:
            record_pipeline_completion(
                record_prefix="CYCLE-{0}".format(cycle_id),
                actor="logron",
                summary="Cycle {0} postprocess observed terminal queue failures without fresh DB results.".format(cycle_id),
                outcome="partial",
                significance="medium",
                files_touched=[
                    "data/state/current_cycle_metrics.json",
                    "data/state/current_cycle_batch_summary.json",
                ],
                evidence=[
                    "data/state/current_cycle_metrics.json",
                    "data/state/current_cycle_batch_summary.json",
                ],
                notes="queue_terminal_failures={0}; queue_done={1}; sent_card={2}".format(
                    metrics.get("queue_terminal_failures", 0),
                    metrics.get("queue_done", 0),
                    sent,
                ),
                task_ids=["TASK-0004"],
            )
        print(json.dumps({"status": "card_sent_waiting" if sent else "no_new_results", "since_minutes": a.since_minutes, "total_in_db": total_rows, "new_backtests": new_backtests, "cycle_id": cycle_id, "run_state": run_state, "card_metrics": metrics}))
        return

    sync_cycle_status_to_active(cycle_id_preview)
    cycle_rows, preview_metrics = filter_rows_to_current_cycle(rows, cycle_id_preview)
    rows_for_dm = cycle_rows if cycle_rows else []

    dm_lines = []
    dm_lines.append("🧪 Research Cycle Results")
    dm_lines.append("")

    best_qscore = 0
    best_strategy = None
    for r in rows_for_dm:
        pf = round(r["profit_factor"], 3) if r["profit_factor"] else 0
        dd = round(r["max_drawdown_pct"], 1) if r["max_drawdown_pct"] else 0
        qs = round(r["score_total"], 2) if r["score_total"] else 0
        trades = r["total_trades"] or 0
        decision = r["score_decision"] or "?"

        emoji = "🟢" if qs >= 3.0 else "🟡" if qs >= 1.0 else "🔴"
        dm_lines.append(f"{emoji} {r['asset']}/{r['timeframe']} PF:{pf} DD:{dd}% T:{trades} QS:{qs} {decision}")

        if qs > best_qscore:
            best_qscore = qs
            best_strategy = f"{r['asset']}/{r['timeframe']}"

    dm_lines.append("")
    dm_lines.append(f"Total in DB: {total_rows} | New this cycle: {len(rows_for_dm)}")

    healthy_rows = [r for r in rows_for_dm if int(r["total_trades"] or 0) >= 15 and float(r["profit_factor"] or 0) > 0 and float(r["win_rate_pct"] or 0) > 0]

    if rows_for_dm:
        dm_text = "\n".join(dm_lines)
        dm_parts = split_message(dm_text, 3900)
        for part in dm_parts:
            send_tg_as(f"<pre>{part}</pre>", "hades", "oragorn")

    if rows_for_dm and not healthy_rows:
        send_tg_as("<pre>🚨 Research cycle integrity alert\nCycle produced results, but none were healthy enough for reflection (need trades>=15, PF>0, WR>0). Check backtester/output integrity.</pre>", "hades", "logron")
        send_tg_as("<pre>🚨 Research cycle integrity alert\nNo healthy rows this cycle. Reflection quality is compromised. Check Hades.</pre>", "dm", "oragorn")

    active_cycle_id_for_journal = cycle_id_preview
    latest_journal_entry = sync_live_journal(active_cycle_id_for_journal)
    journal_sent = False
    if latest_journal_entry.strip():
        try:
            journal_proc = subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts", "send_quandalf_journal_dm.py")],
                capture_output=True,
                text=True,
                timeout=60,
            )
            journal_sent = journal_proc.returncode == 0
        except Exception:
            journal_sent = False

    log_event(
        "notification_sent",
        "oragorn",
        f"Sent {len(rows_for_dm)} current-cycle result updates to Hades, a cooking card to log, and Quandalf live journal DM sent={journal_sent}",
        pipeline="research_cycle",
        step="notify",
    )

    cycle_id = cycle_id_preview
    run_state = finalize_run_state(cycle_id)
    cycle_id = resolve_reporting_cycle_id(run_state)
    run_state = finalize_run_state(cycle_id)
    timing = compute_timing_metrics(run_state)
    elapsed = timing["run_elapsed_seconds"] or round(time.time() - start_time, 1)

    best_pf = 0
    for r in rows:
        if r["profit_factor"] and r["profit_factor"] > best_pf:
            best_pf = r["profit_factor"]

    backtest_count = count_backtests(rows)
    decision_required = backtest_count > 0 or int(run_state.get("queue_done", 0) or 0) > 0 or int(run_state.get("queue_skipped", 0) or 0) > 0
    if decision_required:
        decisions_ok, decisions_payload = ensure_decision_closure(cycle_id)
        if not decisions_ok:
            detail = json.dumps({"cycle_id": cycle_id, "decision_payload": decisions_payload}, ensure_ascii=False)[:900]
            log_event(
                "decision_closure_blocked_card",
                "logron",
                f"Cycle {cycle_id} card suppressed until Quandalf completes all required decisions. {detail}",
                severity="warn",
                pipeline="research_cycle",
                step="postprocess",
            )
            print(json.dumps({"status": "awaiting_complete_decisions", "cycle_id": cycle_id, "decision_payload": decisions_payload}, indent=2))
            raise SystemExit(1)
        try:
            conn_decisions = sqlite3.connect(DB, timeout=30)
            conn_decisions.execute("PRAGMA busy_timeout = 30000")
            apply_queue_decisions(conn_decisions, cycle_id)
            conn_decisions.commit()
            conn_decisions.close()
        except Exception:
            pass
        try:
            subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts", "build_quandalf_experiment_memory.py")],
                capture_output=True,
                text=True,
                timeout=60,
            )
            subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts", "build_quandalf_learning_memory.py")],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception:
            pass

    log_card, metrics = build_log_card(cycle_id, rows, elapsed, backtest_count, run_state=run_state)
    write_cycle_metrics(metrics)
    log_card_sent = send_log_card(cycle_id, log_card, metrics=metrics)

    if metrics.get("state_warning"):
        log_event("cycle_state_warning", "logron", f"Cycle state warning: {metrics['state_warning']}", severity="warn", pipeline="research_cycle", step="postprocess")
    should_post_oragorn_summary = (
        bool(metrics.get("state_warning"))
        or int(metrics.get("pass_count", 0) or 0) > 0
        or int(metrics.get("promote_count", 0) or 0) > 0
        or int(metrics.get("queue_terminal_failures", 0) or 0) > 0
        or int(metrics.get("queue_pending", 0) or 0) > 0
    )
    should_post_oragorn_integrity = (
        int(metrics.get("queue_integrity_skips", 0) or 0) > 0
        and not metrics.get("cycle_results_present")
        and int(metrics.get("queue_terminal_failures", 0) or 0) > 0
    )

    if log_card_sent and should_post_oragorn_summary:
        post_agent_message(
            "logron",
            "oragorn",
            "observation",
            f"Cycle batch postprocess: {metrics['specs_produced']} specs, {metrics['backtests_completed']}/{metrics['backtests_queued']} backtests complete, passes {metrics['pass_count']}, promotions {metrics['promote_count']}, best QS {best_qscore:.2f}",
        )
    elif log_card_sent and should_post_oragorn_integrity:
        post_agent_message(
            "logron",
            "oragorn",
            "observation",
            f"Cycle batch postprocess: {metrics['specs_produced']} specs, 0 DB backtests saved, {metrics['queue_integrity_skips']} integrity skips ({metrics['target_asset'] or '?'} {metrics['target_timeframe'] or '?'}) — zero-trade families were filtered before persistence.",
        )

    conn_portability = sqlite3.connect(DB, timeout=30)
    portability_updates = update_portability_scores(conn_portability)
    conn_portability.commit()
    conn_portability.close()

    conn2 = sqlite3.connect(DB, timeout=30)
    conn2.execute("PRAGMA busy_timeout = 30000")
    priors_updated = update_mechanism_priors(conn2)
    conn2.commit()
    conn2.close()
    lessons_added = extract_lessons(rows)
    log_event(
        "lessons_extracted",
        "logron",
        f"Extracted {lessons_added} lessons",
        pipeline="research_cycle",
        step="postprocess",
    )

    if metrics.get("cycle_results_present") or int(metrics.get("queue_terminal_failures", 0) or 0) > 0 or int(metrics.get("queue_integrity_skips", 0) or 0) > 0 or int(metrics.get("queue_pending", 0) or 0) > 0 or int(metrics.get("pass_count", 0) or 0) > 0 or int(metrics.get("promote_count", 0) or 0) > 0:
        record_pipeline_completion(
            record_prefix="CYCLE-{0}".format(cycle_id),
            actor="logron",
            summary="Cycle {0} postprocess completed: {1} specs, {2}/{3} backtests complete, passes {4}, promotions {5}.".format(
                cycle_id,
                metrics.get("specs_produced", 0),
                metrics.get("backtests_completed", 0),
                metrics.get("backtests_queued", 0),
                metrics.get("pass_count", 0),
                metrics.get("promote_count", 0),
            ),
            outcome="success" if int(metrics.get("promote_count", 0) or 0) > 0 or int(metrics.get("pass_count", 0) or 0) > 0 else "partial",
            significance="high" if int(metrics.get("promote_count", 0) or 0) > 0 else "medium",
            files_touched=[
                "data/state/current_cycle_metrics.json",
                "data/state/current_cycle_batch_summary.json",
                "agents/quandalf/memory/current_cycle_status.json",
            ],
            evidence=[
                "data/state/current_cycle_metrics.json",
                "data/state/current_cycle_batch_summary.json",
            ],
            notes="best_qscore={0}; lessons_added={1}; terminal_failures={2}".format(
                round(float(metrics.get("best_qscore", 0) or 0), 2),
                lessons_added,
                metrics.get("queue_terminal_failures", 0),
            ),
            task_ids=["TASK-0004"],
        )

    print(
        json.dumps(
            {
                "status": "processed",
                "new_backtests": new_backtests,
                "card_backtests": backtest_count,
                "new_results": len(rows),
                "total_in_db": total_rows,
                "best_qscore": best_qscore,
                "dm_sent": True,
                "log_card_sent": log_card_sent,
                "journal_sent": journal_sent,
                "lessons_added": lessons_added,
                "portability_updates": portability_updates[:5],
                "priors_updated": priors_updated[:5],
                "card_metrics": metrics,
            }
        )
    )


if __name__ == "__main__":
    main()
