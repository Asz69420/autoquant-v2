#!/usr/bin/env python3
import json
from pathlib import Path
src = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
out = Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\cron_jobs_snapshot.json')
obj = json.loads(src.read_text(encoding='utf-8'))
out.write_text(json.dumps(obj, indent=2), encoding='utf-8')
print(str(out))
