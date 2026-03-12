import json
from pathlib import Path
ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
state_path = ROOT / 'data' / 'state' / 'current_cycle_state.json'
status_path = ROOT / 'agents' / 'quandalf' / 'memory' / 'current_cycle_status.json'
manifest_path = ROOT / 'data' / 'state' / 'current_cycle_specs.json'
state = json.loads(state_path.read_text(encoding='utf-8'))
cycle_id = int(state.get('cycle_id', 0) or 0)
patterns = [f'QD-20260312-C{cycle_id:03d}-*.strategy_spec.json', f'QD-20260312-C{cycle_id}-*.strategy_spec.json']
paths = []
for pat in patterns:
    for p in sorted((ROOT / 'artifacts' / 'strategy_specs').glob(pat)):
        paths.append(str(p))
paths = list(dict.fromkeys(paths))
state['spec_paths'] = paths
state['specs_produced'] = len(paths)
if paths and str(state.get('phase') or '') in {'started', 'designing'}:
    state['phase'] = 'specs_ready'
state_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
status = json.loads(status_path.read_text(encoding='utf-8')) if status_path.exists() else {}
status['cycle_id'] = cycle_id
status['spec_paths'] = paths
status['specs_produced'] = len(paths)
status['canonical_phase'] = state.get('phase')
status_path.write_text(json.dumps(status, indent=2), encoding='utf-8')
manifest = {
    'status': 'ready' if paths else 'pending',
    'cycle_id': cycle_id,
    'spec_count': len(paths),
    'latest_spec_path': paths[-1] if paths else None,
    'spec_paths': paths,
    'spec_ids': [Path(p).name.replace('.strategy_spec.json','') for p in paths],
    'specs': [{'path': p, 'name': Path(p).name, 'spec_id': Path(p).name.replace('.strategy_spec.json','')} for p in paths],
    'canonical_phase': state.get('phase'),
}
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps({'cycle_id': cycle_id, 'specs_produced': len(paths), 'phase': state.get('phase')}, indent=2))
