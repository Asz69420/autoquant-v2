import json, sqlite3, os
ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, 'db', 'autoquant.db')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("""
SELECT strategy_spec_id, asset, timeframe, stage, validation_target, total_trades, profit_factor, max_drawdown_pct, total_return_pct, score_total, score_decision, ts_iso
FROM backtest_results
WHERE mutation_type = 'engine_fix_replay'
ORDER BY ts_iso DESC
LIMIT 20
""").fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))
conn.close()
