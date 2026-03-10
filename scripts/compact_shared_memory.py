#!/usr/bin/env python3
"""Dedupe and compact shared memory index and stale task evidence without deleting meaning."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "memory" / "shared" / "INDEX.json"
BOARD_PATH = ROOT / "data" / "state" / "task_board.json"
STATE_PATH = ROOT / "data" / "state" / "memory_compaction_state.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def compact_shared_index(index_data):
    entries = index_data.get("entries", [])
    seen = set()
    kept = []
    dropped = []
    for entry in entries:
        key = (
            str(entry.get("bucket", "")).lower(),
            str(entry.get("title", "")).strip().lower(),
            str(entry.get("summary", "")).strip().lower(),
        )
        if key in seen:
            dropped.append(entry)
            continue
        seen.add(key)
        kept.append(entry)
    index_data["entries"] = kept
    index_data["generated_at"] = now_iso()
    return index_data, dropped


def compact_task_evidence(board, keep_done_days=30, max_evidence_per_done_task=3):
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_done_days)
    trimmed = []
    for task in board.get("tasks", []):
        evidence = list(task.get("evidence", []))
        if task.get("status") == "done":
            completed_at = task.get("completed_at")
            try:
                completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00")) if completed_at else None
            except Exception:
                completed_dt = None
            if completed_dt and completed_dt < cutoff and len(evidence) > max_evidence_per_done_task:
                kept = evidence[:max_evidence_per_done_task]
                removed = evidence[max_evidence_per_done_task:]
                task["evidence"] = kept
                trimmed.append({"task_id": task.get("id"), "removed_count": len(removed)})
    board["generated_at"] = now_iso()
    return board, trimmed


def main():
    index_data = load_json(INDEX_PATH, {"version": "shared-memory-index-v1", "generated_at": now_iso(), "entries": []})
    board = load_json(BOARD_PATH, {"version": "task-board-v1", "generated_at": now_iso(), "summary": {}, "tasks": []})

    index_data, dropped_entries = compact_shared_index(index_data)
    board, trimmed_evidence = compact_task_evidence(board)

    INDEX_PATH.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
    BOARD_PATH.write_text(json.dumps(board, indent=2), encoding="utf-8")

    state = {
        "version": "memory-compaction-state-v1",
        "updated_at": now_iso(),
        "shared_duplicates_removed": len(dropped_entries),
        "task_evidence_trimmed": trimmed_evidence,
        "status": "ok"
    }
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
