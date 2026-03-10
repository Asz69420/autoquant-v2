"""Find what's writing -0.5 and 0-trade results."""
import sqlite3

DB = r"C:\Users\Clamps\.openclaw\workspace-oragorn\db\autoquant.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Sample -0.5 results
print("## Sample -0.5 score results")
rows = conn.execute("""
    SELECT id, strategy_spec_id, variant_id, asset, timeframe, score_total, 
           total_trades, profit_factor, win_rate_pct, walk_forward, stage,
           score_decision, score_details, status
    FROM backtest_results WHERE score_total = -0.5 LIMIT 5
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  id={d['id']} spec={d['strategy_spec_id'][:40]} variant={d['variant_id']}")
    print(f"    trades={d['total_trades']} PF={d['profit_factor']} WR={d['win_rate_pct']} stage={d['stage']}")
    print(f"    walk_forward={d['walk_forward']} status={d['status']} decision={d['score_decision']}")
    print(f"    score_details={str(d['score_details'])[:200]}")
    print()

# Sample 0-trade results that scored > 0
print("## Sample 0-trade results with positive scores")
rows = conn.execute("""
    SELECT id, strategy_spec_id, variant_id, score_total, profit_factor, win_rate_pct, 
           walk_forward, stage, score_details, status
    FROM backtest_results WHERE total_trades = 0 AND score_total > 0 LIMIT 5
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  id={d['id']} variant={d['variant_id']} QS={d['score_total']} PF={d['profit_factor']} stage={d['stage']}")
    print(f"    score_details={str(d['score_details'])[:200]}")
    print()

# Sample WR=0 with PF>1
print("## Sample WR=0 with PF>1 (impossible)")
rows = conn.execute("""
    SELECT id, strategy_spec_id, variant_id, score_total, profit_factor, win_rate_pct,
           total_trades, walk_forward, stage, fold_results
    FROM backtest_results WHERE win_rate_pct = 0 AND profit_factor > 1.0 AND total_trades > 0 LIMIT 3
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  id={d['id']} variant={d['variant_id']} QS={d['score_total']:.2f} PF={d['profit_factor']:.2f} WR={d['win_rate_pct']} trades={d['total_trades']}")
    folds = d['fold_results']
    if folds:
        print(f"    fold_results={str(folds)[:300]}")
    print()

conn.close()
