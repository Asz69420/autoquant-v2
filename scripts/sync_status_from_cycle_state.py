#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from cycle_state import load_cycle_state

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
STATUS_PATH = ROOT / "agents" / "quandalf" / "memory" / "current_cycle_status.json"


def load_json(path: Path, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main() -> int:
    canonical = load_cycle_state()
    cycle_id = int(canonical.get("cycle_id", 0) or 0)
    if cycle_id <= 0:
        return 0
    status = load_json(STATUS_PATH, {})
    status["cycle_id"] = cycle_id
    status["spec_paths"] = list(canonical.get("spec_paths") or status.get("spec_paths") or [])
    status["specs_produced"] = int(canonical.get("specs_produced", 0) or len(status.get("spec_paths") or []))
    status["canonical_phase"] = canonical.get("phase")
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "cycle_id": cycle_id, "canonical_phase": canonical.get("phase")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
