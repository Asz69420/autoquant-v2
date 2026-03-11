import sqlite3, os, json
root=r'C:\Users\Clamps\.openclaw\workspace-oragorn'
db=os.path.join(root,'db','autoquant.db')
conn=sqlite3.connect(db)
conn.row_factory=sqlite3.Row
rows=[dict(r) for r in conn.execute("select strategy_spec_id, asset, timeframe, total_trades, profit_factor, score_total, score_decision, ts_iso from backtest_results where asset='SOL' and timeframe='4h' order by ts_iso desc limit 12").fetchall()]
print(json.dumps(rows, indent=2))
