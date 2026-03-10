#!/usr/bin/env python3
"""Quick status summary for memory governance health and progress."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "data" / "state" / "task_board.json"
AUDIT = ROOT / "data" / "state" / "memory_governance_audit.json"
COMPACTION = ROOT / "data" / "state" / "memory_compaction_state.json"
SHARED = ROOT / "memory" / "shared" / "INDEX.json"
EXT = ROOT / "data" / "state" / "external_intel_state.json"
OUT = ROOT / "data" / "state" / "memory_governance_status.json"


def load(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def main():
    board = load(BOARD, {"summary": {}, "tasks": []})
    audit = load(AUDIT, {})
    compaction = load(COMPACTION, {})
    shared = load(SHARED, {"entries": []})
    ext = load(EXT, {})
    payload = {
        "version": "memory-governance-status-v1",
        "task_summary": board.get("summary", {}),
        "active_tasks": [
            {"id": t.get("id"), "title": t.get("title"), "owner": t.get("owner")}
            for t in board.get("tasks", []) if t.get("status") == "active"
        ],
        "shared_memory_entries": len(shared.get("entries", [])),
        "audit_status": audit.get("status", "unknown"),
        "audit_warnings": audit.get("warnings", []),
        "compaction_status": compaction.get("status", "unknown"),
        "compaction_duplicates_removed": compaction.get("shared_duplicates_removed", 0),
        "enabled_external_sources": ext.get("enabled_sources", []),
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
