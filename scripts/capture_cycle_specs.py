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
STATUS_PATH = ROOT / "agents" / "quandalf" / "memory" / "current_cycle_status.json"
ORDERS_PATH = ROOT / "agents" / "quandalf" / "memory" / "cycle_orders.json"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def normalize_spec_id(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    name = Path(text).name
    for suffix in (".strategy_spec.json", ".json"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def spec_matches_cycle(path: Path, cycle_id: int) -> bool:
    spec_id = normalize_spec_id(path.name)
    cycle_token = f"-C{int(cycle_id)}-"
    return cycle_token in spec_id


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

    cycle_id = int(start_payload.get("cycle_id", 0) or 0)
    if cycle_id <= 0:
        briefing = load_json(BRIEFING_PATH)
        cycle_id = int(briefing.get("cycle_id", 0) or 0)

    status_payload = load_json(STATUS_PATH)
    orders_payload = load_json(ORDERS_PATH)
    status_cycle_id = int(status_payload.get("cycle_id", 0) or 0)
    orders_cycle_id = int(orders_payload.get("cycle_id", 0) or 0)

    preferred_paths = []
    if status_cycle_id == cycle_id:
        preferred_paths = [Path(str(p)) for p in (status_payload.get("spec_paths") or []) if str(p).strip()]

    discovered = []
    seen_ids = set()

    def add_path(path: Path):
        try:
            if not path.exists() or not path.is_file():
                return
            stat = path.stat()
        except OSError:
            return
        spec_id = normalize_spec_id(path.name)
        if spec_id in seen_ids:
            return
        seen_ids.add(spec_id)
        discovered.append(
            {
                "path": str(path.resolve()),
                "name": path.name,
                "spec_id": spec_id,
                "mtime_epoch": stat.st_mtime,
                "mtime_iso": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "size_bytes": stat.st_size,
            }
        )

    for path in preferred_paths:
        if spec_matches_cycle(path, cycle_id):
            add_path(path)

    if not discovered:
        for path in SPECS_DIR.glob("*.strategy_spec.json"):
            try:
                stat = path.stat()
            except OSError:
                continue
            if spec_matches_cycle(path, cycle_id):
                add_path(path)
                continue
            if stat.st_mtime + 1 < started_at_epoch:
                continue
            add_path(path)

    discovered.sort(key=lambda item: (item["mtime_epoch"], item["name"]))
    if not discovered:
        # No new specs in this cycle — this is allowed (agent may not have completed, dry-run, or no orders issued).
        # Return empty manifest so pipeline can continue. Backtest step will be skipped.
        manifest = {
            "status": "empty",
            "message": "no new strategy specs in this cycle",
            "cycle_id": cycle_id,
            "started_at_epoch": started_at_epoch,
            "started_at_iso": start_payload.get("started_at_iso"),
            "captured_at_epoch": time.time(),
            "captured_at_iso": datetime.now(timezone.utc).isoformat(),
            "status_cycle_id": status_cycle_id,
            "orders_cycle_id": orders_cycle_id,
            "spec_count": 0,
            "latest_spec_path": None,
            "spec_paths": [],
            "spec_ids": [],
            "specs": [],
        }
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 0

    manifest = {
        "status": "ready",
        "cycle_id": cycle_id,
        "started_at_epoch": started_at_epoch,
        "started_at_iso": start_payload.get("started_at_iso"),
        "captured_at_epoch": time.time(),
        "captured_at_iso": datetime.now(timezone.utc).isoformat(),
        "status_cycle_id": status_cycle_id,
        "orders_cycle_id": orders_cycle_id,
        "spec_count": len(discovered),
        "latest_spec_path": discovered[-1]["path"],
        "spec_paths": [item["path"] for item in discovered],
        "spec_ids": [item["spec_id"] for item in discovered],
        "specs": discovered,
    }

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
