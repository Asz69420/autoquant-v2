import json
from pathlib import Path
ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
REFLECTION = ROOT / 'agents' / 'quandalf' / 'memory' / 'reflection_packet.json'
DECISIONS = ROOT / 'agents' / 'quandalf' / 'memory' / 'refinement_decisions.json'
reflection = json.loads(REFLECTION.read_text(encoding='utf-8'))
current = json.loads(DECISIONS.read_text(encoding='utf-8')) if DECISIONS.exists() else {}
strategy_map = {}
for item in (current.get('strategy_decisions') or []):
    if isinstance(item, dict) and item.get('strategy_spec_id'):
        strategy_map[str(item['strategy_spec_id'])] = item
job_map = {}
for item in (current.get('jobs') or []):
    if isinstance(item, dict) and item.get('queue_id'):
        job_map[str(item['queue_id'])] = item
out = {'cycle_id': int(reflection.get('cycle_id') or current.get('cycle_id') or 0), 'ts_iso': current.get('ts_iso') or reflection.get('ts_iso'), 'strategy_decisions': [], 'jobs': []}
for outcome in (reflection.get('strategy_outcomes') or []):
    if not isinstance(outcome, dict):
        continue
    spec_id = str(outcome.get('strategy_spec_id') or '').strip()
    if not spec_id:
        continue
    legacy = strategy_map.get(spec_id, {})
    decision = str(legacy.get('decision') or legacy.get('strategy_decision') or 'abort').strip().lower()
    if decision not in {'pass','refine','abort'}:
        decision = 'abort'
    entry = {
        'strategy_spec_id': spec_id,
        'decision': decision,
        'rationale': str(outcome.get('rationale') or outcome.get('diagnosis_category') or f'{decision} based on reflected cycle evidence.').strip(),
        'diagnosis_category': outcome.get('diagnosis_category') or None,
        'queue_decisions': []
    }
    if decision == 'refine':
        entry['iteration_intent'] = str(legacy.get('iteration_intent') or 'target density / mechanism repair').strip()
        entry['structural_change'] = str(legacy.get('structural_change') or 'refine according to reflected failure mode').strip()
        entry['expected_effect'] = str(legacy.get('expected_effect') or 'convert zero-trade or weak-edge outcome into a denser, testable thesis').strip()
    for q in (outcome.get('queue') or []):
        if not isinstance(q, dict):
            continue
        queue_id = str(q.get('queue_id') or '').strip()
        if not queue_id:
            continue
        legacy_job = job_map.get(queue_id, {})
        qdecision = str(legacy_job.get('decision') or legacy_job.get('job_decision') or decision).strip().lower()
        if qdecision not in {'pass','refine','abort'}:
            qdecision = decision
        notes = q.get('notes') or {}
        if isinstance(notes, dict):
            note_text = notes.get('error') or notes.get('reason') or notes.get('status') or 'row evidence reviewed'
        else:
            note_text = str(notes).strip() or 'row evidence reviewed'
        qentry = {
            'queue_id': queue_id,
            'decision': qdecision,
            'rationale': str(legacy_job.get('rationale') or f'{qdecision} based on queue evidence: {note_text}.').strip()
        }
        if q.get('result_id'):
            qentry['source_result_id'] = q.get('result_id')
        entry['queue_decisions'].append(qentry)
    out['strategy_decisions'].append(entry)
out['jobs'] = [j for j in (current.get('jobs') or []) if isinstance(j, dict) and str(j.get('decision') or j.get('job_decision') or '').strip().lower() == 'refine']
DECISIONS.write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps({'status':'ok','cycle_id':out['cycle_id'],'strategy_decisions':len(out['strategy_decisions'])}, indent=2))
