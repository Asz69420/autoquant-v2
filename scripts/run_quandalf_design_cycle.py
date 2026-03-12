#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
RUN_STATE = ROOT / "data" / "state" / "research_cycle_started_at.json"
STATUS_PATH = ROOT / "agents" / "quandalf" / "memory" / "current_cycle_status.json"
ORDERS_PATH = ROOT / "agents" / "quandalf" / "memory" / "cycle_orders.json"
MANIFEST_PATH = ROOT / "data" / "state" / "current_cycle_specs.json"
FALLBACK_CONTROL_PATH = ROOT / "data" / "state" / "fallback_control.json"
SPECS_DIR = ROOT / "artifacts" / "strategy_specs"
OPENCLAW = r"C:\Users\Clamps\AppData\Roaming\npm\openclaw.cmd"

PROMPT = """Read briefing_packet.json, cycle_orders.json, research_program.json, reflection_packet.json, current_cycle_status.json, latest_learning_loop.json, latest_experiment_memory.json, latest_journal.md, goals.md, decisions.md, current_status.md, and research_notes.md. You own the strategy decisions for this cycle. The pipeline only executes what you choose and returns results. HARD CONSTRAINT: every spec you write must stay inside the supported/fetchable backtest universe from briefing_packet.json and cycle_orders.json. You are allowed to choose the best-fit asset/timeframe from the validation basket based on thesis; do not confine yourself to the primary lane if another basket lane fits better. Think like a quant researcher, not a template-filler: tradeability before elegance, density before sophistication, mechanism before indicator decoration, lane fit before convenience, evidence before self-justification. Before writing any strategy, derive and internalize a compact working view from the last 5 cycles: top anti-patterns to stop repeating, top promising structures to preserve, expected density for this cycle's ideas, and likely failure modes. Do not treat untested items as failed ideas. Design strategies as market mechanism -> component roles -> testable rules -> failure modes -> refinement path, not decorative indicator stacks. For every strategy, include a mandatory pre-submit reasoning block covering: market behavior targeted, why edge should exist, asset/timeframe fit, indicator role map, expected regime, likely failure mode, first refinement path, expected trade density, expected outcome pattern, what would count as success, and what would count as failure. Each strategy may request a multi-lane test basket, not just one lane. For every chosen lane, explain why that asset/timeframe belongs in the test, what result would justify continuing, what result would justify rotating away, and what you expect to happen there if the thesis is actually right. Encode those lanes in the strategy spec using validation_basket or test_lanes so the backtester can run all requested lanes. Run the density sanity check before submission: plausible trade count, contradictory filters, event sparsity, and asset/timeframe mismatch. Reject ideas that probably will not trade enough. Treat indicators as components with roles, not standalone strategies. Write the FULL batch of strategy specs for this cycle to artifacts/strategy_specs/. Do not generate cosmetic variants like EMA 9 -> 10 unless you explicitly justify the expected effect. Do not write or update a per-cycle journal as part of the live research cycle. Hard contract: if mode is explore, produce 2-4 materially distinct specs across the best-fit lanes in the allowed basket; if mode is exploit, produce 1-3 focused variants of the named passing strategy. Do not drift into one lonely spec per cycle unless minimum_spec_count is 1 and the evidence justifies it. All spec files for the cycle must be written before you finish. Also write/update agents/quandalf/memory/current_cycle_status.json with the SAME cycle_id as cycle_orders.json for this run. Do not increment it. Write: cycle_id, mode, research_direction, minimum_spec_count, maximum_spec_count, spec_paths, specs_produced, exploration_targets, iterate_target, new_families, iterated_families, abandoned_families, next_cycle_focus, rationale, expected_density_notes, anti_patterns_avoided, and thesis_basis. Treat 0-trade grammar as a red flag and avoid reusing it. Your live working context is briefing packet + cycle orders + research program + reflection packet + current cycle status + latest learning loop + latest experiment memory + latest journal + core memory files."""


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def mark_force_fallback(cycle_id: int, reason: str) -> None:
    state = load_json(FALLBACK_CONTROL_PATH)
    recent = list(state.get("recent_cycles") or [])
    state["force_fallback_cycle_id"] = int(cycle_id)
    state["force_fallback_reason"] = str(reason)
    state["force_fallback_ts_iso"] = datetime.now(timezone.utc).isoformat()
    state["recent_cycles"] = recent
    FALLBACK_CONTROL_PATH.parent.mkdir(parents=True, exist_ok=True)
    FALLBACK_CONTROL_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def clear_force_fallback(cycle_id: int) -> None:
    state = load_json(FALLBACK_CONTROL_PATH)
    if int(state.get("force_fallback_cycle_id", 0) or 0) == int(cycle_id):
        state.pop("force_fallback_cycle_id", None)
        state.pop("force_fallback_reason", None)
        state.pop("force_fallback_ts_iso", None)
        FALLBACK_CONTROL_PATH.parent.mkdir(parents=True, exist_ok=True)
        FALLBACK_CONTROL_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def discover_cycle_specs(cycle_id: int) -> list[str]:
    patterns = [f"*C{cycle_id}-*.strategy_spec.json", f"*C{cycle_id:03d}-*.strategy_spec.json"]
    found: list[str] = []
    for pattern in patterns:
        for path in sorted(SPECS_DIR.glob(pattern)):
            found.append(str(path))
    return list(dict.fromkeys(found))


def sync_status_with_specs(cycle_id: int, spec_paths: list[str]) -> None:
    status = load_json(STATUS_PATH)
    orders = load_json(ORDERS_PATH)
    status["cycle_id"] = cycle_id
    if orders:
        status["mode"] = orders.get("mode", status.get("mode", "explore"))
        status["research_direction"] = orders.get("research_direction", status.get("research_direction", "explore_new"))
        status["minimum_spec_count"] = orders.get("minimum_spec_count", status.get("minimum_spec_count", 1))
        status["maximum_spec_count"] = orders.get("maximum_spec_count", status.get("maximum_spec_count", max(1, len(spec_paths))))
        status["exploration_targets"] = orders.get("exploration_targets", status.get("exploration_targets", {}))
        status["iterate_target"] = orders.get("iterate_target", status.get("iterate_target"))
        status["target_asset"] = orders.get("target_asset", status.get("target_asset"))
        status["target_timeframe"] = orders.get("target_timeframe", status.get("target_timeframe"))
    status["spec_paths"] = spec_paths
    status["specs_produced"] = len(spec_paths)
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")


def sync_manifest_with_specs(cycle_id: int, spec_paths: list[str]) -> None:
    run_state = load_json(RUN_STATE)
    status = load_json(STATUS_PATH)
    orders = load_json(ORDERS_PATH)
    specs = []
    for raw_path in spec_paths:
        path = Path(raw_path)
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
        "started_at_epoch": run_state.get("started_at_epoch"),
        "started_at_iso": run_state.get("started_at_iso"),
        "captured_at_epoch": datetime.now(timezone.utc).timestamp(),
        "captured_at_iso": datetime.now(timezone.utc).isoformat(),
        "status_cycle_id": status.get("cycle_id"),
        "orders_cycle_id": orders.get("cycle_id"),
        "spec_count": len(specs),
        "latest_spec_path": specs[-1]["path"] if specs else None,
        "spec_paths": [item["path"] for item in specs],
        "spec_ids": [item["spec_id"] for item in specs],
        "specs": specs,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    run_state = load_json(RUN_STATE)
    cycle_id = int(run_state.get("cycle_id", 0) or 0)
    if cycle_id <= 0:
        print(json.dumps({"status": "error", "message": "no active cycle_id"}, indent=2))
        return 1

    session_id = f"quandalf-cycle-{cycle_id}"
    cmd = [
        OPENCLAW,
        "agent",
        "--agent",
        "quandalf",
        "--session-id",
        session_id,
        "--thinking",
        "off",
        "--timeout",
        "420",
        "--json",
        "--message",
        PROMPT,
    ]

    started = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=480)
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        spec_paths = discover_cycle_specs(cycle_id)
        if spec_paths:
            clear_force_fallback(cycle_id)
            sync_status_with_specs(cycle_id, spec_paths)
            sync_manifest_with_specs(cycle_id, spec_paths)
            print(json.dumps({
                "status": "ok",
                "cycle_id": cycle_id,
                "session_id": session_id,
                "started_at": started,
                "specs_detected": len(spec_paths),
                "returncode": proc.returncode,
            }, indent=2))
            return 0
        mark_force_fallback(cycle_id, f"design_step_returncode_{proc.returncode}")
        print(json.dumps({
            "status": "soft_fail",
            "cycle_id": cycle_id,
            "session_id": session_id,
            "started_at": started,
            "returncode": proc.returncode,
            "stdout": stdout[:2000],
            "stderr": stderr[:2000],
            "message": "design step produced no specs; forcing fallback so the cycle can continue"
        }, indent=2))
        return 0
    except subprocess.TimeoutExpired:
        spec_paths = discover_cycle_specs(cycle_id)
        if spec_paths:
            clear_force_fallback(cycle_id)
            sync_status_with_specs(cycle_id, spec_paths)
            sync_manifest_with_specs(cycle_id, spec_paths)
            print(json.dumps({
                "status": "ok",
                "cycle_id": cycle_id,
                "session_id": session_id,
                "started_at": started,
                "specs_detected": len(spec_paths),
                "timeout_recovered": True,
            }, indent=2))
            return 0
        mark_force_fallback(cycle_id, "design_step_timeout")
        print(json.dumps({
            "status": "soft_fail",
            "cycle_id": cycle_id,
            "session_id": session_id,
            "started_at": started,
            "message": "design step timed out with no specs; forcing fallback so the cycle can continue"
        }, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
