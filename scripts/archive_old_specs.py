"""Archive old strategy specs that aren't promoted. Keep last 48h + any with QS >= 3.0."""
import json
import os
import shutil
import sqlite3
import time
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
SPECS_DIR = ROOT / "artifacts" / "strategy_specs"
ARCHIVE_DIR = ROOT / "artifacts" / "strategy_specs_archive"
DB = ROOT / "db" / "autoquant.db"
CUTOFF_HOURS = 48


def get_promoted_spec_ids():
    """Get spec IDs that scored >= 3.0 (promoted)."""
    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA journal_mode=WAL")
    rows = conn.execute(
        "SELECT DISTINCT strategy_spec_id FROM backtest_results WHERE score_total >= 3.0"
    ).fetchall()
    conn.close()
    return {r[0] for r in rows if r[0]}


def main():
    promoted = get_promoted_spec_ids()
    cutoff = time.time() - (CUTOFF_HOURS * 3600)
    
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    archived = 0
    kept = 0
    for f in sorted(SPECS_DIR.glob("*.json")):
        # Keep if modified recently
        if f.stat().st_mtime > cutoff:
            kept += 1
            continue
        
        # Keep if promoted
        try:
            spec = json.loads(f.read_text(encoding="utf-8"))
            spec_id = spec.get("id") or spec.get("spec_id") or f.stem
        except Exception:
            spec_id = f.stem
        
        if spec_id in promoted:
            kept += 1
            continue
        
        # Archive it
        shutil.move(str(f), str(ARCHIVE_DIR / f.name))
        archived += 1
    
    print(json.dumps({
        "status": "ok",
        "archived": archived,
        "kept": kept,
        "promoted_protected": len(promoted),
        "archive_dir": str(ARCHIVE_DIR),
    }, indent=2))


if __name__ == "__main__":
    main()
