import sqlite3, json, os
root=r'C:\\Users\\Clamps\\.openclaw\\workspace-oragorn'
db=os.path.join(root,'db','autoquant.db')
conn=sqlite3.connect(db)
conn.row_factory=sqlite3.Row
out={}
out['recent_queue']=[dict(r) for r in conn.execute("select id, cycle_id, strategy_spec_id, variant_id, status, stage, result_id, notes, completed_at from research_funnel_queue order by completed_at desc limit 8").fetchall()]
out['recent_results']=[dict(r) for r in conn.execute("select id, ts_iso, strategy_spec_id, variant_id, asset, timeframe from backtest_results order by ts_iso desc limit 8").fetchall()]
print(json.dumps(out, indent=2))
