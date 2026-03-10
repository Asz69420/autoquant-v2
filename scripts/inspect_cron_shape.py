#!/usr/bin/env python3
import json
from pathlib import Path
p = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
obj = json.loads(p.read_text(encoding='utf-8'))
jobs = obj if isinstance(obj, list) else (obj.get('jobs') or obj.get('items') or [])
out = {'count': len(jobs)}
if jobs:
    j = jobs[0]
    out['keys'] = sorted(j.keys())
    out['types'] = {k: type(v).__name__ for k,v in j.items()}
Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\cron_jobs_shape.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out, indent=2))
