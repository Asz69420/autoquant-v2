#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
STATE_DIR = ROOT / "data" / "state"
START_MARKER = STATE_DIR / "research_cycle_started_at.json"
MANIFEST_PATH = STATE_DIR / "current_cycle_specs.json"
SPECS_DIR = ROOT / "artifacts" / "strategy_specs"
BRIEFING_PATH = ROOT / "agents" / "quandalf" / "memory" / "briefing_packet.json"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    if not START_MARKER.exists():
        print(json.dumps({"status": "error", "message": f"start marker missing: {START_MARKER}"}))
        return 1

    if not SPECS_DIR.exists():
        print(json.dumps({"status": "error", "message": f"spec dir missing: {SPECS_DIR}"}))
        return 1

    start_payload = load_json(START_MARKER)
    started_at_epoch = float(start_payload.get("started_at_epoch", 0) or 0)
    if started_at_epoch <= 0:
        print(json.dumps({"status": "error", "message": "invalid start marker"}))
        return 1

    briefing = load_json(BRIEFING_PATH)
    cycle_id = int(briefing.get("cycle_id", 0) or 0)

    discovered = []
    for path in SPECS_DIR.glob("*.strategy_spec.json"):
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_mtime + 1 < started_at_epoch:
            continue
        discovered.append(
            {
                "path": str(path.resolve()),
                "name": path.name,
                "mtime_epoch": stat.st_mtime,
                "mtime_iso": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "size_bytes": stat.st_size,
            }
        )

    discovered.sort(key=lambda item: (item["mtime_epoch"], item["name"]))
    if not discovered:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "no strategy specs created/updated since cycle start",
                    "cycle_id": cycle_id,
                    "started_at_epoch": started_at_epoch,
                    "started_at_iso": start_payload.get("started_at_iso"),
                }
            )
        )
        return 1

    manifest = {
        "status": "ready",
        "cycle_id": cycle_id,
        "started_at_epoch": started_at_epoch,
        "started_at_iso": start_payload.get("started_at_iso"),
        "captured_at_epoch": time.time(),
        "captured_at_iso": datetime.now(timezone.utc).isoformat(),
        "spec_count": len(discovered),
        "latest_spec_path": discovered[-1]["path"],
        "spec_paths": [item["path"] for item in discovered],
        "specs": discovered,
    }

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
