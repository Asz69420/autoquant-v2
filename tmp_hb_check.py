import json, sqlite3, os
root = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
db = os.path.join(root, 'db', 'autoquant.db')
spec_dir = os.path.join(root, 'artifacts', 'strategy_specs')
conn = sqlite3.connect(db)
rows = conn.execute('select distinct strategy_spec_id from backtest_results').fetchall()
backtested = {r[0] for r in rows if r and r[0]}
new_specs = []
for fn in os.listdir(spec_dir):
    if not fn.endswith('.strategy_spec.json'):
        continue
    sid = fn[:-len('.strategy_spec.json')]
    if sid not in backtested:
        new_specs.append(fn)
print(json.dumps({'unbacktested_count': len(new_specs), 'examples': new_specs[:10]}))
