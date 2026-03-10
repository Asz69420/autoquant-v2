import sqlite3, json
conn=sqlite3.connect('db/autoquant.db')
conn.row_factory=sqlite3.Row
rows=conn.execute("select id,cycle_id,stage,status,notes,result_id,strategy_spec_id,variant_id,asset,timeframe,queued_at,started_at from research_funnel_queue where status='running'").fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))
conn.close()
