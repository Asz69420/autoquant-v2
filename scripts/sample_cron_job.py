#!/usr/bin/env python3
import json
from pathlib import Path
p = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
obj = json.loads(p.read_text(encoding='utf-8'))
jobs = obj if isinstance(obj, list) else (obj.get('jobs') or obj.get('items') or [])
for j in jobs[:3]:
    out = {
        'id': j.get('id'),
        'name': j.get('name'),
        'enabled': j.get('enabled'),
        'schedule': j.get('schedule'),
        'sessionTarget': j.get('sessionTarget'),
        'wakeMode': j.get('wakeMode'),
        'payload': j.get('payload'),
        'delivery': j.get('delivery'),
    }
    print(json.dumps(out, indent=2))
    print('---')
