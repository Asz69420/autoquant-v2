#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
STATE_DIR = os.path.join(ROOT, "data", "state")
OUT_PATH = os.path.join(STATE_DIR, "research_cycle_started_at.json")
COUNTER_PATH = os.path.join(STATE_DIR, "cycle_counter.json")
ACTIVE_RUN_STALE_MINUTES = 25

# Files that carry a cycle_id and should be coherent
CYCLE_ID_FILES = {
    "cycle_counter": COUNTER_PATH,
    "run_state": OUT_PATH,
    "manifest": os.path.join(STATE_DIR, "current_cycle_specs.json"),
    "batch_summary": os.path.join(STATE_DIR, "current_cycle_batch_summary.json"),
    "metrics": os.path.join(STATE_DIR, "current_cycle_metrics.json"),
    "briefing": os.path.join(ROOT, "agents", "quandalf", "memory", "briefing_packet.json"),
    "cycle_status": os.path.join(ROOT, "agents", "quandalf", "memory", "current_cycle_status.json"),
    "cycle_orders": os.path.join(ROOT, "agents", "quandalf", "memory", "cycle_orders.json"),
}
ACTIVE_CYCLE_FILES = {"run_state", "briefing", "cycle_status", "cycle_orders", "manifest", "metrics"}
LAST_COMPLETED_FILES = {"batch_summary"}


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def check_cycle_coherence(new_cycle_id):
    """Sanity check: warn and sync if state files disagree on cycle_id."""
    found = {}
    for label, path in CYCLE_ID_FILES.items():
        data = load_json(path)
        if label == "cycle_counter":
            cid = data.get("last_cycle_id")
        else:
            cid = data.get("cycle_id")
        if cid is not None:
            found[label] = int(cid)

    unique_ids = set(found.values())
    if len(unique_ids) <= 1:
        return  # all coherent

    warnings = []
    for label, cid in sorted(found.items()):
        warnings.append(f"  {label}: {cid}")
    warning_text = "\n".join(warnings)
    print(
        f"[cycle-start] WARNING: cycle_id drift detected before cycle {new_cycle_id}:\n{warning_text}",
        file=sys.stderr,
    )

    last_cycle = new_cycle_id - 1
    for label, path in CYCLE_ID_FILES.items():
        if label == "cycle_counter":
            continue  # counter is already correct (we just incremented it)
        data = load_json(path)
        if not data:
            continue
        target_cycle = new_cycle_id if label in ACTIVE_CYCLE_FILES else last_cycle
        old_cid = data.get("cycle_id")
        if old_cid is not None and int(old_cid) != target_cycle:
            data["cycle_id"] = target_cycle
            if label == "cycle_status":
                data["mode"] = "pending"
                data["research_direction"] = "pending"
                data["target_asset"] = None
                data["target_timeframe"] = None
                data["exploration_targets"] = {}
                data["iterate_target"] = None
                data["specific_family_to_iterate"] = None
                data["spec_paths"] = []
                data["specs_produced"] = 0
                data["new_families"] = []
                data["iterated_families"] = []
                data["abandoned_families"] = []
                data["next_cycle_focus"] = "pending"
                data["rationale"] = "pending"
            elif label == "manifest":
                data["status"] = "pending"
                data["spec_count"] = 0
                data["latest_spec_path"] = None
                data["spec_paths"] = []
                data["spec_ids"] = []
                data["specs"] = []
                data["started_at_epoch"] = None
                data["started_at_iso"] = None
                data["captured_at_epoch"] = None
                data["captured_at_iso"] = None
            elif label == "metrics":
                data = {
                    "cycle_id": target_cycle,
                    "status": "pending",
                    "mode": "pending",
                    "research_direction": "pending",
                    "target_asset": None,
                    "target_timeframe": None,
                    "exploration_targets": {},
                    "spec_paths": [],
                    "spec_ids": [],
                    "specs_produced": 0,
                    "specs_written": 0,
                    "cycle_rows": 0,
                    "external_rows": 0,
                    "cycle_results_present": False,
                    "external_results_present": False,
                    "backtests_queued": 0,
                    "backtests_completed": 0,
                    "pass_count": 0,
                    "fail_count": 0,
                    "promote_count": 0,
                    "best_result": None,
                    "best_qscore": 0,
                    "next_cycle_focus": "pending",
                    "rationale": "pending",
                    "status_matches_cycle": True,
                    "manifest_matches_cycle": False,
                    "state_warning": None,
                }
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                print(f"[cycle-start] synced {label} cycle_id {old_cid} -> {target_cycle}", file=sys.stderr)
            except Exception as e:
                print(f"[cycle-start] failed to sync {label}: {e}", file=sys.stderr)


def next_cycle_id():
    try:
        with open(COUNTER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"last_cycle_id": 0}

    data["last_cycle_id"] = int(data.get("last_cycle_id", 0)) + 1
    with open(COUNTER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data["last_cycle_id"]


def resolve_next_cycle_id_or_exit():
    """Serialize research cycles: reject overlapping starts, roll forward only after stale abandonment."""
    run_state = load_json(OUT_PATH)
    prev_status = run_state.get("status")
    prev_cycle = run_state.get("cycle_id")
    prev_ended = run_state.get("ended_at_epoch")
    prev_started = float(run_state.get("started_at_epoch", 0) or 0)

    if prev_cycle and prev_status == "started" and not prev_ended:
        age_seconds = max(0.0, time.time() - prev_started) if prev_started else 0.0
        if age_seconds < ACTIVE_RUN_STALE_MINUTES * 60:
            payload = {
                "status": "busy",
                "reason": "active_cycle_in_progress",
                "active_cycle_id": int(prev_cycle),
                "active_age_seconds": round(age_seconds, 1),
                "stale_after_minutes": ACTIVE_RUN_STALE_MINUTES,
            }
            print(
                f"[cycle-start] active cycle {prev_cycle} is still in progress; refusing overlapping start",
                file=sys.stderr,
            )
            print(json.dumps(payload))
            raise SystemExit(2)

        abandoned_at = datetime.now(timezone.utc)
        run_state["status"] = "stale_abandoned"
        run_state["ended_at_epoch"] = abandoned_at.timestamp()
        run_state["ended_at_iso"] = abandoned_at.isoformat()
        run_state["run_elapsed_seconds"] = round(max(0.0, run_state["ended_at_epoch"] - prev_started), 1) if prev_started else None
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(run_state, f, indent=2)
        print(
            f"[cycle-start] previous cycle {prev_cycle} exceeded {ACTIVE_RUN_STALE_MINUTES}m; marked stale and starting a new cycle",
            file=sys.stderr,
        )

    return next_cycle_id()


os.makedirs(STATE_DIR, exist_ok=True)
started_at_epoch = time.time()
started_at_iso = datetime.now(timezone.utc).isoformat()
cycle_id = resolve_next_cycle_id_or_exit()

# Coherence check: warn and auto-sync drifted state files
check_cycle_coherence(cycle_id)

payload = {
    "cycle_id": cycle_id,
    "status": "started",
    "started_at_epoch": started_at_epoch,
    "started_at_iso": started_at_iso,
    "ended_at_epoch": None,
    "ended_at_iso": None,
    "run_elapsed_seconds": None,
    "reporting_last_seen_at_epoch": started_at_epoch,
    "reporting_last_seen_at_iso": started_at_iso,
}
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)

print(json.dumps({"status": "ok", "path": OUT_PATH, **payload}))
