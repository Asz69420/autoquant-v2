#!/usr/bin/env python3
import json
from pathlib import Path
src = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
out = Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\cron_jobs_normalized.json')
obj = json.loads(src.read_text(encoding='utf-8'))
jobs = obj if isinstance(obj, list) else (obj.get('jobs') or obj.get('items') or [])
normalized = []
for j in jobs:
    normalized.append({
        'id': j.get('id'),
        'name': j.get('name'),
        'enabled': j.get('enabled'),
        'schedule': j.get('schedule'),
        'sessionTarget': j.get('sessionTarget'),
        'wakeMode': j.get('wakeMode'),
        'payload': j.get('payload'),
        'delivery': j.get('delivery'),
    })
out.write_text(json.dumps(normalized, indent=2), encoding='utf-8')
print(str(out))
