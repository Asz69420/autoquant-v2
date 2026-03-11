#!/usr/bin/env python3
import json
from pathlib import Path
p=Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
obj=json.loads(p.read_text(encoding='utf-8'))
jobs=obj if isinstance(obj,list) else (obj.get('jobs') or obj.get('items') or [])
lines=[]
for j in jobs:
    lines.append(f"{j.get('name')} | enabled={j.get('enabled')} | schedule={j.get('schedule')} | target={j.get('sessionTarget')}")
Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\cron_jobs_human.txt').write_text('\n'.join(lines), encoding='utf-8')
print('\n'.join(lines))