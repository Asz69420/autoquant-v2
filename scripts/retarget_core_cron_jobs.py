#!/usr/bin/env python3
import json
from pathlib import Path

CRON = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
BACKUP = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.20260311-retarget-backup.json')
STATE = Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\cron_retarget_state.json')

obj = json.loads(CRON.read_text(encoding='utf-8'))
is_list = isinstance(obj, list)
jobs = obj if is_list else (obj.get('jobs') or obj.get('items') or [])
if not BACKUP.exists():
    BACKUP.write_text(json.dumps(obj, indent=2), encoding='utf-8')

mapping = {
    'frodex-ops-loop-15m': 'agent:frodex',
    'frodex-youtube-watch-2h': 'agent:frodex',
    'frodex-tv-catalog-daily': 'agent:frodex',
    'frodex-daily-intel-0530': 'agent:frodex',
    'quandalf-journal-1730': 'agent:frodex',
}
changed = []
for j in jobs:
    name = j.get('name')
    if name in mapping:
        if j.get('sessionTarget') != mapping[name]:
            j['sessionTarget'] = mapping[name]
            changed.append(name)
        j['enabled'] = True

CRON.write_text(json.dumps(obj if not is_list else jobs, indent=2), encoding='utf-8')
state = {'status':'ok','changed':changed,'backup':str(BACKUP)}
STATE.write_text(json.dumps(state, indent=2), encoding='utf-8')
print(json.dumps(state, indent=2))
