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
ACTIVE_CYCLE_FILES = {"run_state", "briefing", "cycle_status", "cycle_orders"}
LAST_COMPLETED_FILES = {"manifest", "batch_summary", "metrics"}


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
                data.setdefault("mode", "pending")
                data.setdefault("research_direction", "pending")
                data.setdefault("spec_paths", [])
                data.setdefault("specs_produced", 0)
                data.setdefault("next_cycle_focus", "pending")
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


os.makedirs(STATE_DIR, exist_ok=True)
started_at_epoch = time.time()
started_at_iso = datetime.now(timezone.utc).isoformat()
cycle_id = next_cycle_id()

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
