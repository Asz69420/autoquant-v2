#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DECISIONS = os.path.join(ROOT, "agents", "quandalf", "memory", "refinement_decisions.json")
RUNNER = os.path.join(ROOT, "scripts", "refinement_cycle.py")


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def main():
    payload = load_json(DECISIONS, default={})
    jobs = payload.get("jobs") or []
    strategy_decisions = payload.get("strategy_decisions") or []
    if not isinstance(jobs, list):
        jobs = []
    if not isinstance(strategy_decisions, list):
        strategy_decisions = []

    refine_jobs = [j for j in jobs if isinstance(j, dict) and str(j.get("decision") or "").lower() == "refine"]
    if not refine_jobs:
        print(json.dumps({
            "status": "idle",
            "reason": "no_refinement_jobs_queued",
            "cycle_id": payload.get("cycle_id"),
            "strategy_decisions": len(strategy_decisions),
            "jobs": 0,
            "ts_iso": datetime.now(timezone.utc).isoformat(),
        }))
        return 0

    proc = subprocess.run([sys.executable, RUNNER], cwd=ROOT, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
