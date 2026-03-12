#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from cycle_state import load_cycle_state

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
STATUS_PATH = ROOT / "agents" / "quandalf" / "memory" / "current_cycle_status.json"
ORDERS_PATH = ROOT / "agents" / "quandalf" / "memory" / "cycle_orders.json"


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

    orders = load_json(ORDERS_PATH, {})
    status = {
        "cycle_id": cycle_id,
        "mode": orders.get("mode", "explore"),
        "research_direction": orders.get("research_direction", "explore_new"),
        "minimum_spec_count": orders.get("minimum_spec_count", 1),
        "maximum_spec_count": orders.get("maximum_spec_count", max(1, int(canonical.get("specs_produced", 0) or 1))),
        "spec_paths": list(canonical.get("spec_paths") or []),
        "specs_produced": int(canonical.get("specs_produced", 0) or len(canonical.get("spec_paths") or [])),
        "exploration_targets": orders.get("exploration_targets", {}),
        "iterate_target": orders.get("iterate_target"),
        "new_families": [],
        "iterated_families": [],
        "abandoned_families": [],
        "next_cycle_focus": "pending",
        "rationale": "pending",
        "target_asset": orders.get("target_asset"),
        "target_timeframe": orders.get("target_timeframe"),
        "canonical_phase": canonical.get("phase"),
        "queue_seeded": canonical.get("queue_seeded", 0),
        "result_count": canonical.get("result_count", 0),
        "decision_count": canonical.get("decision_count", 0),
        "log_card_sent": canonical.get("log_card_sent", False),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "cycle_id": cycle_id, "canonical_phase": canonical.get("phase")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
