import json
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
(counter_path, run_state_path, current_specs_path) = (
    ROOT / 'data' / 'state' / 'cycle_counter.json',
    ROOT / 'data' / 'state' / 'research_cycle_started_at.json',
    ROOT / 'data' / 'state' / 'current_cycle_specs.json',
)
counter = json.loads(counter_path.read_text(encoding='utf-8')) if counter_path.exists() else {}
counter['last_cycle_id'] = 65
counter_path.write_text(json.dumps(counter, indent=2), encoding='utf-8')
run = json.loads(run_state_path.read_text(encoding='utf-8')) if run_state_path.exists() else {}
run['cycle_id'] = 65
run['status'] = 'started'
run['ts_iso'] = datetime.now(timezone.utc).isoformat()
run_state_path.write_text(json.dumps(run, indent=2), encoding='utf-8')
specs = json.loads(current_specs_path.read_text(encoding='utf-8')) if current_specs_path.exists() else {}
specs['cycle_id'] = 65
specs['spec_paths'] = []
specs['spec_ids'] = []
specs['captured_at'] = datetime.now(timezone.utc).isoformat()
current_specs_path.write_text(json.dumps(specs, indent=2), encoding='utf-8')
print(json.dumps({'status':'ok','cycle_id':65}, indent=2))
