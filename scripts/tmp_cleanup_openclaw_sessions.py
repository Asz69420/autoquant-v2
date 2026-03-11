import json
import os
import shutil
from pathlib import Path

root = Path(os.environ['USERPROFILE']) / '.openclaw'
archive = root / 'cleanup-archive' / 'sessions-orphans-2026-03-11'
archive.mkdir(parents=True, exist_ok=True)
summary = {}
for agent in ['oragorn', 'quandalf', 'logron', 'frodex', 'main']:
    sdir = root / 'agents' / agent / 'sessions'
    sjson = sdir / 'sessions.json'
    if not sdir.exists() or not sjson.exists():
        continue
    try:
        data = json.loads(sjson.read_text(encoding='utf-8'))
    except Exception:
        data = {}
    referenced = set()
    def scan(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ('transcriptPath','jsonlPath','path') and isinstance(v, str):
                    referenced.add(Path(v).name)
                else:
                    scan(v)
        elif isinstance(obj, list):
            for item in obj:
                scan(item)
    scan(data)
    moved = 0
    for f in sdir.glob('*.jsonl'):
        if f.name not in referenced:
            target_dir = archive / agent
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(target_dir / f.name))
            moved += 1
    summary[agent] = moved
print(json.dumps(summary, indent=2))
