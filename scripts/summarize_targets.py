#!/usr/bin/env python3
import json
from pathlib import Path
for path in [Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json'), Path(r'C:\Users\Clamps\.openclaw\workspace\config\automation_v2_manifest.json')]:
    print('FILE', path)
    obj=json.loads(path.read_text(encoding='utf-8'))
    def walk(x):
        if isinstance(x, dict):
            if 'name' in x or 'sessionTarget' in x or 'target' in x:
                print({k:x.get(k) for k in ['name','sessionTarget','target','schedule','enabled']})
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for i in x: walk(i)
    walk(obj)
