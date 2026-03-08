#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
STATE_DIR = os.path.join(ROOT, "data", "state")
OUT_PATH = os.path.join(STATE_DIR, "research_cycle_started_at.json")

os.makedirs(STATE_DIR, exist_ok=True)
payload = {
    "started_at_epoch": time.time(),
    "started_at_iso": datetime.now(timezone.utc).isoformat(),
}
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(payload, f)

print(json.dumps({"status": "ok", "path": OUT_PATH, **payload}))
