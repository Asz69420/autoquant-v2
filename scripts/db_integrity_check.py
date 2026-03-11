#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta

ROOT = os.environ.get("AUTOQUANT_ROOT", r"C:\Users\Clamps\.openclaw\workspace-oragorn")
DB = os.path.join(ROOT, "db", "autoquant.db")
RESET_BASELINE_PATH = os.path.join(ROOT, "data", "state", "system_reset_baseline.json")


def load_reset_baseline():
    try:
        if os.path.exists(RESET_BASELINE_PATH):
            with open(RESET_BASELINE_PATH, "r", encoding="utf-8") as f:
                payload = json.load(f)
            ts_iso = payload.get("ts_iso")
            if ts_iso:
                return datetime.fromisoformat(str(ts_iso).replace("Z", "+00:00"))
    except Exception:
        pass
    return None


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc)
    cutoff_dt = now - timedelta(hours=24)
    baseline = load_reset_baseline()
    if baseline and baseline > cutoff_dt:
        cutoff_dt = baseline
    cutoff = cutoff_dt.isoformat()

    checks = {
        "zero_trade_rows": "SELECT COUNT(*) FROM backtest_results WHERE total_trades = 0",
        "sentinel_minus_half": "SELECT COUNT(*) FROM backtest_results WHERE score_total = -0.5",
        "impossible_pf_wr": "SELECT COUNT(*) FROM backtest_results WHERE profit_factor > 1.0 AND win_rate_pct = 0 AND total_trades > 0",
        "period_start_eq_end": "SELECT COUNT(*) FROM backtest_results WHERE CAST(period_start AS TEXT) = CAST(period_end AS TEXT)",
        "recent_zero_trade_rows": "SELECT COUNT(*) FROM backtest_results WHERE total_trades = 0 AND ts_iso >= ?",
        "recent_impossible_pf_wr": "SELECT COUNT(*) FROM backtest_results WHERE profit_factor > 1.0 AND win_rate_pct = 0 AND total_trades > 0 AND ts_iso >= ?",
        "recent_sentinel_minus_half": "SELECT COUNT(*) FROM backtest_results WHERE score_total = -0.5 AND ts_iso >= ?",
        "recent_healthy_rows": "SELECT COUNT(*) FROM backtest_results WHERE total_trades >= 15 AND win_rate_pct > 0 AND profit_factor > 0 AND ts_iso >= ?",
    }
    out = {}
    for key, sql in checks.items():
        if "?" in sql:
            out[key] = conn.execute(sql, (cutoff,)).fetchone()[0]
        else:
            out[key] = conn.execute(sql).fetchone()[0]
    out["status"] = "ok"
    issues = []
    grace_minutes = 30
    baseline_age_minutes = None
    if baseline:
        baseline_age_minutes = (now - baseline).total_seconds() / 60.0
        out["minutes_since_reset"] = round(baseline_age_minutes, 1)
    if out["recent_zero_trade_rows"] > 0:
        issues.append(f"recent_zero_trade_rows={out['recent_zero_trade_rows']}")
    if out["recent_impossible_pf_wr"] > 0:
        issues.append(f"recent_impossible_pf_wr={out['recent_impossible_pf_wr']}")
    if out["recent_sentinel_minus_half"] > 0:
        issues.append(f"recent_sentinel_minus_half={out['recent_sentinel_minus_half']}")
    if out["recent_healthy_rows"] == 0:
        if baseline_age_minutes is not None and baseline_age_minutes < grace_minutes:
            out["healthy_rows_grace_suppressed"] = True
        else:
            issues.append("recent_healthy_rows=0")
    if issues:
        out["status"] = "fail"
        out["issues"] = issues
    conn.close()
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
