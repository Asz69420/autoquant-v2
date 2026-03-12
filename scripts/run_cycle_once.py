#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cycle_state import (
    PHASE_BACKTESTING,
    PHASE_COMPLETED,
    PHASE_DECISIONS_READY,
    PHASE_DESIGNING,
    PHASE_REFLECTION_READY,
    PHASE_RESULTS_READY,
    PHASE_SPECS_READY,
    append_note,
    load_cycle_state,
)

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
PY = sys.executable
STATE_PATH = ROOT / "data" / "state" / "current_cycle_state.json"


def load_json(path: Path, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def current_cycle_id() -> int:
    return int(load_cycle_state().get("cycle_id", 0) or 0)


def run_step(name: str, cmd: list[str], allow_soft_fail: bool = False) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    payload = {
        "step": name,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }
    if proc.returncode != 0 and not allow_soft_fail:
        raise RuntimeError(json.dumps(payload, indent=2)[:4000])
    return payload


def assert_phase(cycle_id: int, allowed: set[str], context: str) -> None:
    state = load_cycle_state()
    if int(state.get("cycle_id", 0) or 0) != int(cycle_id):
        raise RuntimeError(f"{context}: cycle_state cycle_id mismatch; expected {cycle_id}, got {state.get('cycle_id')}")
    phase = str(state.get("phase") or "")
    if phase not in allowed:
        raise RuntimeError(f"{context}: unexpected cycle_state phase {phase}; allowed={sorted(allowed)}")


def main() -> int:
    steps = []

    steps.append(run_step("cycle-start", [PY, "scripts/cycle-start.py"]))
    cycle_id = current_cycle_id()
    if cycle_id <= 0:
        raise RuntimeError("cycle-start did not create active cycle_id")

    steps.append(run_step("regime-refresh", [PY, "scripts/refresh_regimes.py"]))
    steps.append(run_step("briefing", [PY, "scripts/research-cycle.py"]))
    steps.append(run_step("build-cycle-orders", [PY, "scripts/build_cycle_orders.py"]))
    steps.append(run_step("build-research-program", [PY, "scripts/build_quandalf_research_program.py"]))

    steps.append(run_step("quandalf-design", [PY, "scripts/run_quandalf_design_cycle.py"], allow_soft_fail=True))
    assert_phase(cycle_id, {PHASE_DESIGNING, PHASE_SPECS_READY}, "after quandalf-design")

    steps.append(run_step("fallback-cook-specs", [PY, "scripts/fallback_cook_specs.py"]))
    steps.append(run_step("capture-cycle-specs", [PY, "scripts/capture_cycle_specs.py"]))
    steps.append(run_step("sync-manifest", [PY, "scripts/sync_manifest_from_cycle_state.py"]))
    steps.append(run_step("sync-status-early", [PY, "scripts/sync_status_from_cycle_state.py"]))
    assert_phase(cycle_id, {PHASE_SPECS_READY}, "after capture-cycle-specs")

    manifest = load_json(ROOT / "data" / "state" / "current_cycle_specs.json", {})
    spec_count = int(manifest.get("spec_count", 0) or 0)
    if spec_count <= 0:
        append_note(cycle_id, "Cycle ended with no specs after capture")
        raise RuntimeError("capture-cycle-specs completed with zero specs")

    steps.append(run_step("prepare-cycle-lanes", [PY, "scripts/prepare_cycle_lanes.py"]))
    steps.append(run_step("backtest", [PY, "scripts/parallel_runner.py", "--manifest", "data/state/current_cycle_specs.json", "--variant", "all"]))
    assert_phase(cycle_id, {PHASE_BACKTESTING, PHASE_RESULTS_READY}, "after backtest")

    steps.append(run_step("research-card", [PY, "scripts/cycle-postprocess.py", "--send-card-only", "--since-minutes", "180"], allow_soft_fail=True))
    steps.append(run_step("leaderboard-preview", [PY, "scripts/leaderboard_render.py", "--preview"], allow_soft_fail=True))
    steps.append(run_step("build-reflection-packet", [PY, "scripts/build-reflection-packet.py"]))
    assert_phase(cycle_id, {PHASE_REFLECTION_READY, PHASE_RESULTS_READY}, "after build-reflection-packet")

    steps.append(run_step("ensure-decisions", [PY, "scripts/ensure_quandalf_decisions_complete.py"]))
    steps.append(run_step("validate-decisions", [PY, "scripts/validate_quandalf_decisions.py"]))
    assert_phase(cycle_id, {PHASE_DECISIONS_READY}, "after validate-decisions")

    steps.append(run_step("experiment-memory", [PY, "scripts/build_quandalf_experiment_memory.py"], allow_soft_fail=True))
    steps.append(run_step("learning-memory", [PY, "scripts/build_quandalf_learning_memory.py"]))
    steps.append(run_step("cycle-postprocess", [PY, "scripts/cycle-postprocess.py"]))
    assert_phase(cycle_id, {PHASE_COMPLETED}, "after cycle-postprocess")
    steps.append(run_step("sync-run-state", [PY, "scripts/sync_run_state_from_cycle_state.py"]))
    steps.append(run_step("sync-status", [PY, "scripts/sync_status_from_cycle_state.py"]))

    print(json.dumps({
        "status": "ok",
        "cycle_id": cycle_id,
        "steps": [{"step": s["step"], "returncode": s["returncode"]} for s in steps],
        "state_path": str(STATE_PATH),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
