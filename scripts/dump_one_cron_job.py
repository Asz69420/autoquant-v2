#!/usr/bin/env python3
import json
from pathlib import Path
src = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
out = Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\cron_one_job.json')
obj = json.loads(src.read_text(encoding='utf-8'))
jobs = obj if isinstance(obj, list) else (obj.get('jobs') or obj.get('items') or [])
out.write_text(json.dumps(jobs[0] if jobs else {}, indent=2), encoding='utf-8')
print(str(out))
