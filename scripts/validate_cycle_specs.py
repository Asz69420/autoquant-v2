#!/usr/bin/env python3
"""
Validate manifest after capture-cycle-specs. 
If spec count is 0, skip backtest and return early.
Otherwise, return status 'ready' to continue.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
MANIFEST_PATH = ROOT / "data" / "state" / "current_cycle_specs.json"


def main():
    if not MANIFEST_PATH.exists():
        print(json.dumps({"status": "error", "message": "manifest missing"}))
        return 1

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"manifest parse failed: {e}"}))
        return 1

    spec_count = int(manifest.get("spec_count", 0) or 0)
    status = manifest.get("status", "unknown")

    if spec_count == 0 or status == "empty":
        # Safe early-exit: no specs to backtest. Cycle-postprocess will handle empty results gracefully.
        print(json.dumps({"status": "empty", "spec_count": 0, "skip_backtest": True, "message": "Zero specs in this cycle; backtest will be skipped."}))
        return 0

    # Specs are ready, continue with backtest.
    print(json.dumps({"status": "ready", "spec_count": spec_count, "skip_backtest": False}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
