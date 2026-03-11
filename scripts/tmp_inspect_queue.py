import json, sqlite3, os
ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, 'db', 'autoquant.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()
print('recent queue rows')
for row in cur.execute("SELECT id, cycle_id, status, stage, strategy_spec_id, variant_id, substr(COALESCE(notes,''),1,220) FROM research_funnel_queue ORDER BY id DESC LIMIT 18"):
    print(row)
print('status counts by cycle')
for row in cur.execute("SELECT cycle_id, status, count(*) FROM research_funnel_queue GROUP BY cycle_id, status ORDER BY cycle_id DESC, status"):
    print(row)
conn.close()
