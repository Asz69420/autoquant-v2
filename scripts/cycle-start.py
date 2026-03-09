#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
STATE_DIR = os.path.join(ROOT, "data", "state")
OUT_PATH = os.path.join(STATE_DIR, "research_cycle_started_at.json")
COUNTER_PATH = os.path.join(STATE_DIR, "cycle_counter.json")


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
