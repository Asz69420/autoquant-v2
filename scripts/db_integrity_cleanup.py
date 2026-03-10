#!/usr/bin/env python3
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone

ROOT = os.environ.get("AUTOQUANT_ROOT", r"C:\Users\Clamps\.openclaw\workspace-oragorn")
DB = os.path.join(ROOT, "db", "autoquant.db")
BACKUP_DIR = os.path.join(ROOT, "artifacts", "db_backups")


def backup_db():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst = os.path.join(BACKUP_DIR, f"autoquant-pre-integrity-cleanup-{ts}.db")
    shutil.copy2(DB, dst)
    return dst


def main():
    backup_path = backup_db()
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    before = conn.execute("SELECT COUNT(*) FROM backtest_results").fetchone()[0]

    deleted = {}
    deleted["zero_trade_rows"] = conn.execute("DELETE FROM backtest_results WHERE total_trades = 0").rowcount
    deleted["sentinel_minus_half"] = conn.execute("DELETE FROM backtest_results WHERE score_total = -0.5").rowcount
    deleted["impossible_pf_wr"] = conn.execute("DELETE FROM backtest_results WHERE profit_factor > 1.0 AND win_rate_pct = 0 AND total_trades > 0").rowcount
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM backtest_results").fetchone()[0]
    conn.close()

    print(json.dumps({
        "status": "ok",
        "backup": backup_path,
        "rows_before": before,
        "rows_after": after,
        "deleted": deleted,
        "total_deleted": before - after,
    }, indent=2))


if __name__ == "__main__":
    main()
