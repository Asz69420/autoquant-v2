import sqlite3, json, os
root=r'C:\Users\Clamps\.openclaw\workspace-oragorn'
db=os.path.join(root,'db','autoquant.db')
conn=sqlite3.connect(db)
conn.row_factory=sqlite3.Row
for cycle_id in (321,322,323):
    print('\n### cycle', cycle_id)
    rows=[dict(r) for r in conn.execute("select id, cycle_id, strategy_spec_id, variant_id, stage, status, result_id, notes, queued_at, started_at, completed_at from research_funnel_queue where cycle_id=? order by queued_at", (cycle_id,)).fetchall()]
    print(json.dumps(rows, indent=2))
