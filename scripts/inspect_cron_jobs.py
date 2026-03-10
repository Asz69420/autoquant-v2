#!/usr/bin/env python3
import json
from pathlib import Path
p = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
obj = json.loads(p.read_text(encoding='utf-8'))
if isinstance(obj, list):
    jobs = obj
elif isinstance(obj, dict):
    jobs = obj.get('jobs') or obj.get('items') or []
else:
    jobs = []
print(json.dumps(jobs, indent=2))
