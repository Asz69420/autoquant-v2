#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
CARD_STATE_PATH = ROOT / "data" / "state" / "cycle_postprocess_card_state.json"
RUN_STATE_PATH = ROOT / "data" / "state" / "research_cycle_started_at.json"
STATUS_PATH = ROOT / "agents" / "quandalf" / "memory" / "current_cycle_status.json"


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_iso(value: str):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold-minutes", type=float, default=10.0)
    args = ap.parse_args()

    state = load_json(CARD_STATE_PATH, {"cards": {}})
    cards = (state or {}).get("cards") or {}
    latest = None
    latest_key = None
    for key, value in cards.items():
        if not isinstance(value, dict):
            continue
        if value.get("kind") not in {"research", "reflection"}:
            continue
        ts = parse_iso(value.get("sent_at_iso"))
        if ts is None:
            continue
        if latest is None or ts > latest:
            latest = ts
            latest_key = key

    now = datetime.now(timezone.utc)
    age_seconds = None if latest is None else max(0.0, (now - latest).total_seconds())
    threshold_seconds = max(60.0, float(args.threshold_minutes) * 60.0)

    run_state = load_json(RUN_STATE_PATH, {})
    status = load_json(STATUS_PATH, {})

    payload = {
        "status": "stale" if latest is None or age_seconds > threshold_seconds else "ok",
        "threshold_minutes": args.threshold_minutes,
        "latest_card_key": latest_key,
        "latest_card_sent_at_iso": latest.isoformat() if latest else None,
        "age_seconds": age_seconds,
        "active_cycle_id": int(run_state.get("cycle_id", 0) or 0),
        "active_cycle_status": run_state.get("status"),
        "quandalf_cycle_id": int(status.get("cycle_id", 0) or 0),
        "quandalf_specs_produced": int(status.get("specs_produced", 0) or 0),
        "quandalf_spec_paths": list(status.get("spec_paths") or []),
    }
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if payload["status"] == "ok" else 2)


if __name__ == "__main__":
    main()
