import sqlite3, json
conn=sqlite3.connect('db/autoquant.db')
q={}
for s in ['queued','running','done','failed']:
    q[s]=conn.execute('select count(*) from research_funnel_queue where status=?',(s,)).fetchone()[0]
print(json.dumps({'by_status':q}, indent=2))
rows=conn.execute('select stage,status,count(*) from research_funnel_queue group by stage,status order by stage,status').fetchall()
print(json.dumps({'by_stage_status':[{'stage':r[0],'status':r[1],'count':r[2]} for r in rows]}, indent=2))
rows=conn.execute('select cycle_id, stage, status, count(*) from research_funnel_queue group by cycle_id,stage,status order by cycle_id desc limit 20').fetchall()
print(json.dumps({'recent':[{'cycle_id':r[0],'stage':r[1],'status':r[2],'count':r[3]} for r in rows]}, indent=2))
conn.close()
