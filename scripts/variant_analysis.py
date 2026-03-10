"""Check if the 'validation' variants are real OOS or just more in-sample."""
import sqlite3

DB = r"C:\Users\Clamps\.openclaw\workspace-oragorn\db\autoquant.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Check a promoted strategy's variants
print("## Top promoted strategy variant breakdown")
rows = conn.execute("""
    SELECT variant_id, score_total, profit_factor, total_trades, period_start, period_end
    FROM backtest_results 
    WHERE strategy_spec_id = 'strategy-spec-20260301-claude-st9k3m5x.strategy_spec'
    ORDER BY score_total DESC LIMIT 15
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  {d['variant_id']}: QS={d['score_total']:.2f} PF={d['profit_factor']:.2f} trades={d['total_trades']} period={d['period_start']} to {d['period_end']}")

# Check: are WR=0% strategies real? That's suspicious
print("\n## WR=0% promoted strategies — is win rate actually 0?")
rows = conn.execute("""
    SELECT strategy_spec_id, variant_id, win_rate_pct, total_trades, profit_factor, score_total
    FROM backtest_results WHERE score_total >= 3.0 AND win_rate_pct = 0
    ORDER BY score_total DESC LIMIT 5
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  QS={d['score_total']:.2f} WR={d['win_rate_pct']}% trades={d['total_trades']} PF={d['profit_factor']:.2f} | {d['variant_id']}")

# Check the walk-forward engine schema
print("\n## Walk-forward tables")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%walk%'").fetchall()
for t in tables:
    print(f"  {t[0]}")
if not tables:
    print("  No walk-forward tables found")
    tables2 = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"  All tables: {[t[0] for t in tables2]}")

conn.close()
