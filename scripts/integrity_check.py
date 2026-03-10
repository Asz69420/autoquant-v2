"""Check data integrity of backtest results."""
import sqlite3

DB = r"C:\Users\Clamps\.openclaw\workspace-oragorn\db\autoquant.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Impossible: PF > 1.0 with WR = 0%
print("## INTEGRITY: PF > 1.0 but WR = 0% (mathematically impossible)")
rows = conn.execute("""
    SELECT COUNT(*) as n FROM backtest_results 
    WHERE profit_factor > 1.0 AND win_rate_pct = 0 AND total_trades > 0
""").fetchone()
total = conn.execute("SELECT COUNT(*) FROM backtest_results WHERE total_trades > 0").fetchone()[0]
print(f"  {dict(rows)['n']} out of {total} results have PF>1 with WR=0% — DATA BUG")

# Check: period_start == period_end
print("\n## INTEGRITY: period_start == period_end")
rows = conn.execute("""
    SELECT COUNT(*) as n FROM backtest_results WHERE period_start = period_end
""").fetchone()
print(f"  {dict(rows)['n']} results have identical start/end periods")

# Check: score_total = -0.5 pattern
print("\n## INTEGRITY: score_total = -0.5 exactly")
rows = conn.execute("""
    SELECT COUNT(*) as n FROM backtest_results WHERE score_total = -0.5
""").fetchone()
print(f"  {dict(rows)['n']} results have score exactly -0.5 (likely error sentinel)")

# Check: total_trades = 0 
print("\n## INTEGRITY: total_trades = 0")
rows = conn.execute("""
    SELECT COUNT(*) as n FROM backtest_results WHERE total_trades = 0
""").fetchone()
print(f"  {dict(rows)['n']} results have 0 trades")

# Check: what does a healthy result look like?
print("\n## HEALTHY: PF > 1.0 AND WR > 0 AND trades >= 15")
rows = conn.execute("""
    SELECT COUNT(*) as n, ROUND(AVG(score_total), 3) as avg_qs
    FROM backtest_results WHERE profit_factor > 1.0 AND win_rate_pct > 0 AND total_trades >= 15
""").fetchone()
print(f"  {dict(rows)['n']} healthy results, avg QS = {dict(rows)['avg_qs']}")

# Sample a healthy promoted result
print("\n## Sample healthy promoted result")
rows = conn.execute("""
    SELECT * FROM backtest_results 
    WHERE score_total >= 3.0 AND win_rate_pct > 0 AND total_trades >= 15
    ORDER BY score_total DESC LIMIT 1
""").fetchall()
for r in rows:
    d = dict(r)
    for k, v in d.items():
        if v is not None and k != 'metrics' and k != 'regime_metrics':
            print(f"  {k}: {v}")

conn.close()
