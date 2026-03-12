import json, sqlite3, os
ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, 'db', 'autoquant.db')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, cycle_id, status, stage, strategy_spec_id, variant_id, asset, timeframe, validation_target, result_id, substr(COALESCE(notes,''),1,400) AS notes FROM research_funnel_queue WHERE cycle_id=? ORDER BY id", (65,)).fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))
conn.close()
