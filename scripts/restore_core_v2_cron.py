#!/usr/bin/env python3
import copy, json
from pathlib import Path

CRON = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
BACKUP = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.20260311-core-restore-backup.json')
MANIFEST = Path(r'C:\Users\Clamps\.openclaw\workspace\config\automation_v2_manifest.json')
STATE = Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\core_cron_restore_state.json')
OLD = r'C:\Users\Clamps\.openclaw\workspace'
NEW = r'C:\Users\Clamps\.openclaw\workspace-oragorn'
WANTED = {
    'frodex-ops-loop-15m',
    'frodex-youtube-watch-2h',
    'frodex-tv-catalog-daily',
    'frodex-daily-intel-0530',
    'quandalf-journal-1730',
}
LEGACY = {
    'AutoQuant-autopilot','AutoQuant-V2-ContinuousLoop','AutoQuant-tv-catalog','AutoQuant-V2-TVCatalog','AutoQuant-youtube-watch','AutoQuant-V2-YouTubeWatch',
    'AutoQuant-daily-intel','AutoQuant-V2-DailyIntel','AutoQuant-quandalf-journal','AutoQuant-V2-QuandalfJournal'
}

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def deep_replace(value):
    if isinstance(value, str):
        return value.replace(OLD, NEW)
    if isinstance(value, list):
        return [deep_replace(v) for v in value]
    if isinstance(value, dict):
        return {k: deep_replace(v) for k, v in value.items()}
    return value

def find_jobs(node, found):
    if isinstance(node, dict):
        if 'name' in node and ('schedule' in node or 'payload' in node or 'sessionTarget' in node):
            found.append(node)
        for v in node.values():
            find_jobs(v, found)
    elif isinstance(node, list):
        for item in node:
            find_jobs(item, found)

cron_obj = load(CRON)
manifest_obj = load(MANIFEST)
cron_jobs = cron_obj if isinstance(cron_obj, list) else (cron_obj.get('jobs') or cron_obj.get('items') or [])
found = []
find_jobs(manifest_obj, found)
manifest_by_name = {}
for j in found:
    name = j.get('name')
    if name and name not in manifest_by_name:
        manifest_by_name[name] = deep_replace(copy.deepcopy(j))

current_by_name = {j.get('name'): j for j in cron_jobs if isinstance(j, dict) and j.get('name')}
kept = [j for j in cron_jobs if j.get('name') not in WANTED and j.get('name') not in LEGACY]
restored = []
for name in WANTED:
    job = manifest_by_name.get(name)
    if not job:
        continue
    if name in current_by_name and current_by_name[name].get('id'):
        job['id'] = current_by_name[name]['id']
    job['enabled'] = True
    restored.append(job)
final_jobs = kept + restored
if not BACKUP.exists():
    BACKUP.write_text(json.dumps(cron_obj, indent=2), encoding='utf-8')
if isinstance(cron_obj, list):
    new_obj = final_jobs
else:
    new_obj = cron_obj
    if isinstance(new_obj.get('jobs'), list):
        new_obj['jobs'] = final_jobs
    elif isinstance(new_obj.get('items'), list):
        new_obj['items'] = final_jobs
    else:
        new_obj['jobs'] = final_jobs
CRON.write_text(json.dumps(new_obj, indent=2), encoding='utf-8')
state = {'status':'ok','restored':sorted([j.get('name') for j in restored]),'final_count':len(final_jobs),'backup':str(BACKUP)}
STATE.write_text(json.dumps(state, indent=2), encoding='utf-8')
print(json.dumps(state, indent=2))
