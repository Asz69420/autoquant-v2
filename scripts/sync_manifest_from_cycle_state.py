#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from cycle_state import load_cycle_state

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
MANIFEST_PATH = ROOT / "data" / "state" / "current_cycle_specs.json"


def main() -> int:
    canonical = load_cycle_state()
    cycle_id = int(canonical.get("cycle_id", 0) or 0)
    if cycle_id <= 0:
        return 0

    spec_paths = [str(p) for p in (canonical.get("spec_paths") or []) if str(p).strip()]
    specs = []
    for raw in spec_paths:
        path = Path(raw)
        try:
            stat = path.stat()
            specs.append({
                "path": str(path),
                "name": path.name,
                "spec_id": path.name.replace('.strategy_spec.json', ''),
                "mtime_epoch": stat.st_mtime,
                "mtime_iso": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "size_bytes": stat.st_size,
            })
        except OSError:
            continue

    payload = {
        "status": "ready" if specs else "pending",
        "cycle_id": cycle_id,
        "started_at_epoch": None,
        "started_at_iso": canonical.get("started_at_iso"),
        "captured_at_epoch": datetime.now(timezone.utc).timestamp(),
        "captured_at_iso": datetime.now(timezone.utc).isoformat(),
        "status_cycle_id": cycle_id,
        "orders_cycle_id": cycle_id,
        "spec_count": len(specs),
        "latest_spec_path": specs[-1]["path"] if specs else None,
        "spec_paths": [item["path"] for item in specs],
        "spec_ids": [item["spec_id"] for item in specs],
        "specs": specs,
        "canonical_phase": canonical.get("phase"),
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "cycle_id": cycle_id, "spec_count": len(specs), "canonical_phase": canonical.get("phase")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
