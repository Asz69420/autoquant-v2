"""Compact strategy_status.json — trim bloated refinement entries."""
import json
from pathlib import Path

PATH = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn\agents\quandalf\memory\strategy_status.json")
KEEP_KEYS = {"cycle_id", "started_at", "finished_at", "run_elapsed_seconds", 
             "jobs_requested", "had_error", "best_qscore", "promote_count",
             "pass_count", "fail_count", "target_asset", "target_timeframe",
             "mode", "specs_produced", "backtests_completed"}

data = json.loads(PATH.read_text(encoding="utf-8"))
before = len(json.dumps(data))

if "refinement_cycles" in data:
    trimmed = []
    for entry in data["refinement_cycles"][-50:]:
        if isinstance(entry, dict):
            slim = {k: v for k, v in entry.items() if k in KEEP_KEYS}
            # Keep runner summary if it's short
            runner = entry.get("runner")
            if isinstance(runner, dict):
                slim["runner_summary"] = {
                    "total": runner.get("total"),
                    "success": runner.get("success"),
                    "failed": runner.get("failed"),
                }
            trimmed.append(slim)
        else:
            trimmed.append(entry)
    data["refinement_cycles"] = trimmed

after_str = json.dumps(data, indent=2)
after = len(after_str)
PATH.write_text(after_str, encoding="utf-8")
print(f"Size: {before:,} -> {after:,} chars ({100-after*100//before}% reduction)")
print(f"Bytes: {before//1024}KB -> {after//1024}KB")
