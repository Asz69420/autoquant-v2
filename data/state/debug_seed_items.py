import json, sys, sqlite3
sys.path.insert(0, r'C:\Users\Clamps\.openclaw\workspace-oragorn\scripts')
import parallel_runner as pr
conn = sqlite3.connect(r'C:\Users\Clamps\.openclaw\workspace-oragorn\db\autoquant.db')
items = pr.build_seed_items(conn, r'C:\Users\Clamps\.openclaw\workspace-oragorn\artifacts\strategy_specs\DEBUG-MULTI-LANE.strategy_spec.json', cycle_id=1)
conn.close()
print(json.dumps([{'asset':i['asset'],'timeframe':i['timeframe'],'validation_target':i.get('validation_target')} for i in items], indent=2))
