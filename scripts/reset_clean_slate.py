#!/usr/bin/env python3
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
DB = ROOT / "db" / "autoquant.db"
BACKUP_DIR = ROOT / "artifacts" / "reset_backups" / datetime.now(timezone.utc).strftime("pre_reset_%Y%m%dT%H%M%SZ")
SPECS_DIR = ROOT / "artifacts" / "strategy_specs"
QUANDALF_MEMORY = ROOT / "agents" / "quandalf" / "memory"
STATE_DIR = ROOT / "data" / "state"


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB, BACKUP_DIR / "autoquant.db")

    for rel in [
        Path("data/state/cycle_counter.json"),
        Path("data/state/cycle_postprocess_card_state.json"),
        Path("data/state/current_cycle_specs.json"),
        Path("data/state/current_cycle_metrics.json"),
        Path("data/state/current_cycle_batch_summary.json"),
        Path("data/state/refinement_jobs.json"),
        Path("data/state/refinement_cycle_run_state.json"),
        Path("data/state/quandalf_learning_loop.json"),
        Path("data/state/quandalf_experiment_memory.json"),
        Path("agents/quandalf/memory/current_cycle_status.json"),
        Path("agents/quandalf/memory/cycle_orders.json"),
        Path("agents/quandalf/memory/reflection_packet.json"),
        Path("agents/quandalf/memory/refinement_decisions.json"),
        Path("agents/quandalf/memory/latest_learning_loop.json"),
        Path("agents/quandalf/memory/latest_experiment_memory.json"),
        Path("agents/quandalf/memory/research_program.json"),
        Path("agents/quandalf/memory/strategy_status.json"),
        Path("agents/quandalf/memory/latest_journal.md"),
    ]:
        src = ROOT / rel
        if src.exists():
            dst = BACKUP_DIR / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    if SPECS_DIR.exists():
        spec_backup = BACKUP_DIR / "strategy_specs"
        shutil.copytree(SPECS_DIR, spec_backup, dirs_exist_ok=True)
        for path in SPECS_DIR.glob("*.strategy_spec.json"):
            path.unlink()
        for path in SPECS_DIR.glob("DEBUG-*.json"):
            path.unlink()

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    tables = ["backtest_results", "research_funnel_queue", "lessons"]
    counts = {}
    for tbl in tables:
        try:
            counts[tbl] = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            cur.execute(f"DELETE FROM {tbl}")
        except Exception as e:
            counts[tbl] = f"ERR: {e}"
    try:
        cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('backtest_results','research_funnel_queue','lessons')")
    except Exception:
        pass
    conn.commit()
    conn.close()

    write_json(STATE_DIR / "cycle_counter.json", {"last_cycle_id": 0})
    write_json(STATE_DIR / "cycle_postprocess_card_state.json", {"last_card": {"cycle_id": 0, "fingerprint": None, "sent_at_iso": None, "preview": []}})
    write_json(STATE_DIR / "current_cycle_specs.json", {"status": "pending", "cycle_id": 1, "started_at_epoch": None, "started_at_iso": None, "captured_at_epoch": None, "captured_at_iso": None, "status_cycle_id": 0, "orders_cycle_id": 0, "spec_count": 0, "latest_spec_path": None, "spec_paths": [], "spec_ids": [], "specs": []})
    write_json(STATE_DIR / "current_cycle_metrics.json", {"cycle_id": 0, "status": "reset", "note": "clean slate after poisoned backtest invalidation"})
    write_json(STATE_DIR / "current_cycle_batch_summary.json", {"cycle_id": 0, "status": "reset", "decision_summary": {"promote": 0, "refine": 0, "abort": 0, "zero_trade": 0}})
    write_json(STATE_DIR / "refinement_jobs.json", {"cycle_id": 0, "jobs": [], "strategy_decisions": [], "selected_by": "quandalf", "status": "reset"})
    write_json(STATE_DIR / "refinement_cycle_run_state.json", {"cycle_id": 0, "status": "idle", "note": "reset"})
    write_json(STATE_DIR / "quandalf_learning_loop.json", {"version": "quandalf-learning-loop-v2", "ts_iso": datetime.now(timezone.utc).isoformat(), "cycle_context": {"cycle_id": 0}, "decision_summary": {}, "diagnosis_breakdown": {}, "dimensions": {}, "journal_excerpt": [], "learning_requirements": []})
    write_json(STATE_DIR / "quandalf_experiment_memory.json", {"ts_iso": datetime.now(timezone.utc).isoformat(), "cycle_id": 0, "count": 0, "experiments": []})

    write_json(QUANDALF_MEMORY / "current_cycle_status.json", {"cycle_id": 0, "mode": "explore", "research_direction": "fresh_start", "minimum_spec_count": 3, "maximum_spec_count": 4, "spec_paths": [], "specs_produced": 0, "exploration_targets": [], "iterate_target": None, "new_families": [], "iterated_families": [], "abandoned_families": [], "next_cycle_focus": "fresh start", "rationale": "Clean slate after poisoned backtest invalidation."})
    write_json(QUANDALF_MEMORY / "cycle_orders.json", {"cycle_id": 0, "mode": "explore", "minimum_spec_count": 3, "maximum_spec_count": 4, "target_asset": None, "target_timeframe": None, "allowed_lanes": [], "validation_basket": [], "exploration_targets": {"concepts": [], "management_styles": [], "assets": [], "timeframes": []}, "thesis_hint": "Fresh start. Focus on strategies that should obviously generate trades.", "rotation_reason": "Reset after poisoned backtest invalidation."})
    write_json(QUANDALF_MEMORY / "reflection_packet.json", {"ts_iso": datetime.now(timezone.utc).isoformat(), "type": "reflection", "cycle_id": 0, "strategy_outcomes": [], "decision_summary": {"promote": 0, "refine": 0, "abort": 0, "zero_trade": 0}, "guidance": {"focus_level": "strategy", "instruction": "Fresh start. Generate only thesis-first strategies that should obviously trade."}})
    write_json(QUANDALF_MEMORY / "refinement_decisions.json", {"cycle_id": 0, "ts_iso": datetime.now(timezone.utc).isoformat(), "strategy_decisions": [], "jobs": []})
    write_json(QUANDALF_MEMORY / "latest_learning_loop.json", {"version": "quandalf-learning-loop-v2", "ts_iso": datetime.now(timezone.utc).isoformat(), "cycle_context": {"cycle_id": 0}, "decision_summary": {}, "diagnosis_breakdown": {}, "dimensions": {}, "journal_excerpt": [], "learning_requirements": []})
    write_json(QUANDALF_MEMORY / "latest_experiment_memory.json", {"ts_iso": datetime.now(timezone.utc).isoformat(), "cycle_id": 0, "count": 0, "experiments": []})
    write_json(QUANDALF_MEMORY / "research_program.json", {"ts_iso": datetime.now(timezone.utc).isoformat(), "cycle_id": 0, "search_priorities": ["fresh start", "thesis-first", "strategies that should obviously trade"], "active_hypotheses": [], "banned_failure_patterns": ["ceremonial sparse logic", "convenience-lane bias"], "lane_rotation_policy": {"use_validation_basket": True, "rotate_when_concentration_high": True}, "meaningful_refinement": ["simplify", "reassign roles", "change management", "change lane if thesis fits better"], "diagnosis_breakdown": {}, "current_directives": ["All recent backtests were invalidated.", "Start fresh with strategies expected to test well."]})
    (QUANDALF_MEMORY / "strategy_status.json").write_text("{}\n", encoding="utf-8")
    (QUANDALF_MEMORY / "latest_journal.md").write_text("# Quandalf Journal — Fresh Start\n\nAll recent backtests were invalidated after a poisoned evaluator period. Start from a clean slate with thesis-first strategies that should obviously generate trades.\n", encoding="utf-8")

    lock = STATE_DIR / "autopilot_continuous.lock"
    if lock.exists():
        try:
            lock.unlink()
        except Exception:
            pass

    print(json.dumps({
        "status": "ok",
        "backup_dir": str(BACKUP_DIR),
        "deleted_rows": counts,
        "cycle_reset_to": 0,
        "specs_cleared": True
    }, indent=2))

if __name__ == "__main__":
    main()
