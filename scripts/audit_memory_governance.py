#!/usr/bin/env python3
"""Audit memory-governance health using deterministic checks."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "memory" / "shared" / "INDEX.json"
BOARD_PATH = ROOT / "data" / "state" / "task_board.json"
COMPACTION_STATE_PATH = ROOT / "data" / "state" / "memory_compaction_state.json"
EXTERNAL_INTEL_STATE_PATH = ROOT / "data" / "state" / "external_intel_state.json"
OUTPUT_PATH = ROOT / "data" / "state" / "memory_governance_audit.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_dt(text):
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except Exception:
        return None


def main():
    index_data = load_json(INDEX_PATH, {"entries": []})
    board = load_json(BOARD_PATH, {"tasks": []})
    compaction = load_json(COMPACTION_STATE_PATH, {})
    external_state = load_json(EXTERNAL_INTEL_STATE_PATH, {})

    warnings = []
    info = []

    entries = index_data.get("entries", [])
    if not entries:
        warnings.append("shared_memory_empty")
    else:
        info.append("shared_entries={0}".format(len(entries)))

    tasks = board.get("tasks", [])
    active_tasks = [t for t in tasks if t.get("status") == "active"]
    blocked_tasks = [t for t in tasks if t.get("status") == "blocked"]
    if blocked_tasks:
        warnings.append("blocked_tasks_present:{0}".format(len(blocked_tasks)))
    info.append("active_tasks={0}".format(len(active_tasks)))

    stale_active = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    for task in active_tasks:
        updated_at = parse_dt(task.get("updated_at"))
        if updated_at and updated_at < cutoff:
            stale_active.append(task.get("id"))
    if stale_active:
        warnings.append("stale_active_tasks:" + ",".join(stale_active))

    compaction_updated = parse_dt(compaction.get("updated_at"))
    if not compaction_updated:
        warnings.append("compaction_state_missing")
    elif compaction_updated < datetime.now(timezone.utc) - timedelta(days=2):
        warnings.append("compaction_state_stale")

    enabled_sources = external_state.get("enabled_sources") or []
    info.append("enabled_external_sources={0}".format(len(enabled_sources)))
    if enabled_sources and not external_state.get("last_ingested_at"):
        warnings.append("external_intel_enabled_but_no_ingest_history")

    status = "ok" if not warnings else "warn"
    payload = {
        "version": "memory-governance-audit-v1",
        "ts_iso": now_iso(),
        "status": status,
        "warnings": warnings,
        "info": info,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
