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
    PHASE_STARTED,
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

    existing_state = load_cycle_state()
    existing_cycle_id = int(existing_state.get("cycle_id", 0) or 0)
    existing_phase = str(existing_state.get("phase") or "")
    resumable_phases = {PHASE_STARTED, PHASE_DESIGNING, PHASE_SPECS_READY, PHASE_BACKTESTING, PHASE_RESULTS_READY, PHASE_REFLECTION_READY, PHASE_DECISIONS_READY}

    if existing_cycle_id > 0 and existing_phase in resumable_phases:
        cycle_id = existing_cycle_id
        steps.append({"step": "resume-cycle", "returncode": 0, "stdout": f"resuming cycle {cycle_id} in phase {existing_phase}", "stderr": ""})
    else:
        steps.append(run_step("cycle-start", [PY, "scripts/cycle-start.py"]))
        cycle_id = current_cycle_id()
        if cycle_id <= 0:
            raise RuntimeError("cycle-start did not create active cycle_id")
        existing_phase = PHASE_STARTED

    phase_order = {
        PHASE_STARTED: 0,
        PHASE_DESIGNING: 1,
        PHASE_SPECS_READY: 2,
        PHASE_BACKTESTING: 3,
        PHASE_RESULTS_READY: 4,
        PHASE_REFLECTION_READY: 5,
        PHASE_DECISIONS_READY: 6,
        PHASE_COMPLETED: 7,
    }

    def phase_rank() -> int:
        return phase_order.get(str(load_cycle_state().get("phase") or existing_phase), -1)

    if phase_rank() <= phase_order[PHASE_STARTED]:
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
        fallback_state_path = ROOT / "data" / "state" / "fallback_control.json"
        fallback_state = load_json(fallback_state_path, {})
        fallback_state["force_fallback_cycle_id"] = cycle_id
        fallback_state["force_fallback_reason"] = "run_cycle_once_zero_specs_guard"
        fallback_state_path.write_text(json.dumps(fallback_state, indent=2), encoding="utf-8")
        steps.append(run_step("fallback-cook-specs-forced", [PY, "scripts/fallback_cook_specs.py"]))
        steps.append(run_step("capture-cycle-specs-forced", [PY, "scripts/capture_cycle_specs.py"]))
        steps.append(run_step("sync-manifest-forced", [PY, "scripts/sync_manifest_from_cycle_state.py"]))
        steps.append(run_step("sync-status-forced", [PY, "scripts/sync_status_from_cycle_state.py"]))
        manifest = load_json(ROOT / "data" / "state" / "current_cycle_specs.json", {})
        spec_count = int(manifest.get("spec_count", 0) or 0)
    if spec_count <= 0:
        append_note(cycle_id, "Cycle ended with no specs after forced fallback/capture")
        raise RuntimeError("capture-cycle-specs completed with zero specs")

    if phase_rank() <= phase_order[PHASE_SPECS_READY]:
        steps.append(run_step("prepare-cycle-lanes", [PY, "scripts/prepare_cycle_lanes.py"]))
        steps.append(run_step("backtest", [PY, "scripts/parallel_runner.py", "--manifest", "data/state/current_cycle_specs.json", "--variant", "all"]))
        steps.append(run_step("sync-manifest-post-backtest", [PY, "scripts/sync_manifest_from_cycle_state.py"]))
        steps.append(run_step("sync-status-post-backtest", [PY, "scripts/sync_status_from_cycle_state.py"]))
        assert_phase(cycle_id, {PHASE_BACKTESTING, PHASE_RESULTS_READY}, "after backtest")

    if phase_rank() <= phase_order[PHASE_RESULTS_READY]:
        steps.append(run_step("research-card", [PY, "scripts/cycle-postprocess.py", "--send-card-only", "--since-minutes", "180"], allow_soft_fail=True))
        steps.append(run_step("leaderboard-preview", [PY, "scripts/leaderboard_render.py", "--preview"], allow_soft_fail=True))
        steps.append(run_step("build-reflection-packet", [PY, "scripts/build-reflection-packet.py"]))
        steps.append(run_step("sync-status-post-reflection", [PY, "scripts/sync_status_from_cycle_state.py"]))
        assert_phase(cycle_id, {PHASE_REFLECTION_READY, PHASE_RESULTS_READY}, "after build-reflection-packet")

    if phase_rank() <= phase_order[PHASE_REFLECTION_READY]:
        steps.append(run_step("ensure-decisions", [PY, "scripts/ensure_quandalf_decisions_complete.py"]))
        steps.append(run_step("validate-decisions", [PY, "scripts/validate_quandalf_decisions.py"]))
        steps.append(run_step("sync-status-post-decisions", [PY, "scripts/sync_status_from_cycle_state.py"]))
        assert_phase(cycle_id, {PHASE_DECISIONS_READY, PHASE_COMPLETED}, "after validate-decisions")

    if phase_rank() <= phase_order[PHASE_DECISIONS_READY]:
        steps.append(run_step("experiment-memory", [PY, "scripts/build_quandalf_experiment_memory.py"], allow_soft_fail=True))
        steps.append(run_step("learning-memory", [PY, "scripts/build_quandalf_learning_memory.py"]))
        steps.append(run_step("cycle-postprocess", [PY, "scripts/cycle-postprocess.py"]))
        assert_phase(cycle_id, {PHASE_COMPLETED}, "after cycle-postprocess")
        steps.append(run_step("sync-run-state", [PY, "scripts/sync_run_state_from_cycle_state.py"]))
        steps.append(run_step("sync-manifest-final", [PY, "scripts/sync_manifest_from_cycle_state.py"]))
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
