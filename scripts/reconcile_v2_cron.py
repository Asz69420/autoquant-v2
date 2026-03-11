#!/usr/bin/env python3
import copy, json, uuid
from pathlib import Path

CRON = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.json')
BACKUP = Path(r'C:\Users\Clamps\.openclaw\cron\jobs.20260311-reconcile-backup.json')
MANIFEST = Path(r'C:\Users\Clamps\.openclaw\workspace\config\automation_v2_manifest.json')
STATE = Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\cron_reconcile_state.json')
OLD = r'C:\Users\Clamps\.openclaw\workspace'
NEW = r'C:\Users\Clamps\.openclaw\workspace-oragorn'


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


def find_candidate_jobs(node, found):
    if isinstance(node, dict):
        keys = set(node.keys())
        if 'name' in keys and ('schedule' in keys or 'cron' in keys or 'payload' in keys or 'delivery' in keys):
            found.append(node)
        for v in node.values():
            find_candidate_jobs(v, found)
    elif isinstance(node, list):
        for item in node:
            find_candidate_jobs(item, found)


def get_jobs_container(obj):
    if isinstance(obj, list):
        return obj, None
    if isinstance(obj, dict):
        if isinstance(obj.get('jobs'), list):
            return obj['jobs'], 'jobs'
        if isinstance(obj.get('items'), list):
            return obj['items'], 'items'
    raise RuntimeError('Unsupported cron jobs format')


current_obj = load(CRON)
manifest_obj = load(MANIFEST)
current_jobs, container_key = get_jobs_container(current_obj)

candidates = []
find_candidate_jobs(manifest_obj, candidates)
# de-dupe by name while preserving first occurrence
seen = set()
desired = []
for job in candidates:
    name = job.get('name')
    if not name or name in seen:
        continue
    seen.add(name)
    desired.append(deep_replace(copy.deepcopy(job)))

# prune to meaningful automation names only
keep_tokens = ['loop', 'youtube', 'intel', 'journal', 'catalog', 'tv', 'health', 'reporter', 'git', 'memory']
desired = [j for j in desired if any(tok in str(j.get('name','')).lower() for tok in keep_tokens)]

# build by name, preserving ids from current if matching
current_by_name = {j.get('name'): j for j in current_jobs if j.get('name')}
final_jobs = []
for job in desired:
    name = job.get('name')
    if name in current_by_name and current_by_name[name].get('id'):
        job['id'] = current_by_name[name]['id']
    job['enabled'] = True if job.get('enabled') is None else job.get('enabled')
    if not job.get('id'):
        job['id'] = str(uuid.uuid4())
    final_jobs.append(job)

# Always backup once
if not BACKUP.exists():
    BACKUP.write_text(json.dumps(current_obj, indent=2), encoding='utf-8')

# Write back same container shape
if container_key is None:
    new_obj = final_jobs
else:
    new_obj = current_obj
    new_obj[container_key] = final_jobs
CRON.write_text(json.dumps(new_obj, indent=2), encoding='utf-8')

state = {
    'status': 'ok',
    'backup': str(BACKUP),
    'final_count': len(final_jobs),
    'names': [j.get('name') for j in final_jobs],
}
STATE.write_text(json.dumps(state, indent=2), encoding='utf-8')
print(json.dumps(state, indent=2))
