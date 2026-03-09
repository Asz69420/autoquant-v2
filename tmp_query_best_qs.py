import sqlite3, json
conn = sqlite3.connect(r'C:\Users\Clamps\.openclaw\workspace-oragorn\db\autoquant.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('''
SELECT id, ts_iso, strategy_spec_id, variant_id, asset, timeframe,
       score_total, qscore_outofsample, qscore_insample, degradation_pct,
       walk_forward_folds, total_trades, profit_factor, status
FROM backtest_results
ORDER BY score_total DESC, ts_iso DESC
LIMIT 10
''').fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))
