#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
STATE_PATH = ROOT / "data" / "state" / "current_cycle_state.json"

PHASE_PENDING = "pending"
PHASE_STARTED = "started"
PHASE_DESIGNING = "designing"
PHASE_SPECS_READY = "specs_ready"
PHASE_BACKTESTING = "backtesting"
PHASE_RESULTS_READY = "results_ready"
PHASE_REFLECTION_READY = "reflection_ready"
PHASE_DECISIONS_READY = "decisions_ready"
PHASE_COMPLETED = "completed"
PHASE_STALE = "stale_abandoned"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict[str, Any]:
    return {
        "cycle_id": 0,
        "phase": PHASE_PENDING,
        "started_at_iso": None,
        "updated_at_iso": now_iso(),
        "specs_produced": 0,
        "spec_paths": [],
        "queue_seeded": 0,
        "queue_snapshot": [],
        "result_count": 0,
        "decision_count": 0,
        "log_card_sent": False,
        "notes": [],
    }


def load_cycle_state() -> dict[str, Any]:
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return _default_state()


def save_cycle_state(state: dict[str, Any]) -> dict[str, Any]:
    state = dict(state or {})
    state.setdefault("cycle_id", 0)
    state.setdefault("phase", PHASE_PENDING)
    state.setdefault("specs_produced", 0)
    state.setdefault("spec_paths", [])
    state.setdefault("queue_seeded", 0)
    state.setdefault("queue_snapshot", [])
    state.setdefault("result_count", 0)
    state.setdefault("decision_count", 0)
    state.setdefault("log_card_sent", False)
    state.setdefault("notes", [])
    state["updated_at_iso"] = now_iso()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def start_cycle(cycle_id: int, started_at_iso: str | None = None) -> dict[str, Any]:
    state = _default_state()
    state["cycle_id"] = int(cycle_id)
    state["phase"] = PHASE_STARTED
    state["started_at_iso"] = started_at_iso or now_iso()
    return save_cycle_state(state)


def advance_cycle(cycle_id: int, phase: str, **updates: Any) -> dict[str, Any]:
    state = load_cycle_state()
    if int(state.get("cycle_id", 0) or 0) != int(cycle_id):
        state = _default_state()
        state["cycle_id"] = int(cycle_id)
        state["started_at_iso"] = updates.pop("started_at_iso", None) or now_iso()
    state["phase"] = phase
    for key, value in updates.items():
        state[key] = value
    return save_cycle_state(state)


def append_note(cycle_id: int, note: str) -> dict[str, Any]:
    state = load_cycle_state()
    if int(state.get("cycle_id", 0) or 0) != int(cycle_id):
        state = _default_state()
        state["cycle_id"] = int(cycle_id)
        state["started_at_iso"] = now_iso()
    notes = list(state.get("notes") or [])
    notes.append({"ts_iso": now_iso(), "note": str(note)})
    state["notes"] = notes[-50:]
    return save_cycle_state(state)
