import sqlite3, json
from datetime import datetime, timezone, timedelta

conn=sqlite3.connect('db/autoquant.db')
cutoff=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
rows=conn.execute("select id,cycle_id,stage,strategy_spec_id,variant_id,started_at from research_funnel_queue where status='running' and started_at < ?", (cutoff,)).fetchall()
reset=[]
for r in rows:
    conn.execute("update research_funnel_queue set status='queued', started_at=NULL, notes=? where id=?", (json.dumps({'status':'reset_stale_running','reason':'stale_running_timeout','reset_at':datetime.now(timezone.utc).isoformat()}), r[0]))
    reset.append({'id':r[0],'cycle_id':r[1],'stage':r[2],'strategy_spec_id':r[3],'variant_id':r[4],'started_at':r[5]})
conn.commit()
conn.close()
print(json.dumps({'reset_count':len(reset),'rows':reset}, indent=2))
