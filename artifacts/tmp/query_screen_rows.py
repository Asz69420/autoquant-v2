import sqlite3, json
conn = sqlite3.connect(r'C:\Users\Clamps\.openclaw\workspace-oragorn\db\autoquant.db')
cur = conn.cursor()
rows = cur.execute("SELECT id, stage, asset, timeframe, score_decision, total_trades, ts_iso FROM backtest_results WHERE stage='screen' ORDER BY id DESC LIMIT 5").fetchall()
print(json.dumps(rows, indent=2))
conn.close()
