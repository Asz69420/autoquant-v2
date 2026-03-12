#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from cycle_state import PHASE_COMPLETED, load_cycle_state

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
RUN_STATE_PATH = ROOT / "data" / "state" / "research_cycle_started_at.json"


def main() -> int:
    cycle_state = load_cycle_state()
    cycle_id = int(cycle_state.get("cycle_id", 0) or 0)
    if cycle_id <= 0:
        return 0

    started_at_iso = cycle_state.get("started_at_iso") or datetime.now(timezone.utc).isoformat()
    try:
        started_at_dt = datetime.fromisoformat(str(started_at_iso).replace("Z", "+00:00"))
        started_at_epoch = started_at_dt.timestamp()
    except Exception:
        started_at_dt = datetime.now(timezone.utc)
        started_at_epoch = started_at_dt.timestamp()
        started_at_iso = started_at_dt.isoformat()

    payload = {
        "cycle_id": cycle_id,
        "status": "completed" if cycle_state.get("phase") == PHASE_COMPLETED else "started",
        "started_at_epoch": started_at_epoch,
        "started_at_iso": started_at_iso,
        "ended_at_epoch": None,
        "ended_at_iso": None,
        "run_elapsed_seconds": None,
        "reporting_last_seen_at_epoch": datetime.now(timezone.utc).timestamp(),
        "reporting_last_seen_at_iso": datetime.now(timezone.utc).isoformat(),
    }

    if payload["status"] == "completed":
        ended_dt = datetime.now(timezone.utc)
        payload["ended_at_epoch"] = ended_dt.timestamp()
        payload["ended_at_iso"] = ended_dt.isoformat()
        payload["run_elapsed_seconds"] = round(max(0.0, payload["ended_at_epoch"] - started_at_epoch), 1)

    RUN_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "cycle_id": cycle_id, "run_state_status": payload["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
