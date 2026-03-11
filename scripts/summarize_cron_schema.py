#!/usr/bin/env python3
import json
from pathlib import Path
cron = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
obj = json.loads(cron.read_text(encoding='utf-8'))
jobs = obj if isinstance(obj, list) else (obj.get('jobs') or obj.get('items') or [])
out = []
out.append(f'COUNT={len(jobs)}')
if jobs:
    j = jobs[0]
    out.append('KEYS=' + ','.join(sorted(j.keys())))
    for k in ['id','name','enabled','schedule','sessionTarget','wakeMode','payload','delivery']:
        out.append(f'{k}={type(j.get(k)).__name__}:{repr(j.get(k))[:300]}')
Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\cron_schema_summary.txt').write_text('\n'.join(out), encoding='utf-8')
print('\n'.join(out))