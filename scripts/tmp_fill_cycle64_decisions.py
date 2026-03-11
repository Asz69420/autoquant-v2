import json
from pathlib import Path
ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
REFLECTION = ROOT / 'agents' / 'quandalf' / 'memory' / 'reflection_packet.json'
DECISIONS = ROOT / 'agents' / 'quandalf' / 'memory' / 'refinement_decisions.json'
reflection = json.loads(REFLECTION.read_text(encoding='utf-8'))
out = {
    'cycle_id': int(reflection.get('cycle_id') or 0),
    'ts_iso': reflection.get('ts_iso'),
    'strategy_decisions': [],
    'jobs': []
}
for item in reflection.get('strategy_outcomes') or []:
    if not isinstance(item, dict):
        continue
    spec_id = str(item.get('strategy_spec_id') or '').strip()
    if not spec_id:
        continue
    diagnosis = str(item.get('diagnosis_category') or '').strip() or 'too sparse'
    rationale = str(item.get('rationale') or '').strip()
    decision = 'abort'
    if item.get('recommended_action') == 'promote':
        decision = 'pass'
    elif item.get('recommended_action') == 'refine':
        decision = 'refine'
    elif item.get('recommended_action') in {'abort', 'red_flag', 'pending', 'fix_only'}:
        decision = 'abort'
    queue_decisions = []
    for q in item.get('queue') or []:
        if not isinstance(q, dict):
            continue
        queue_id = str(q.get('queue_id') or '').strip()
        if not queue_id:
            continue
        notes = q.get('notes') or {}
        if isinstance(notes, dict):
            note_text = notes.get('error') or notes.get('reason') or notes.get('status') or 'queue evidence reviewed'
        else:
            note_text = str(notes).strip() or 'queue evidence reviewed'
        q_decision = decision
        if q.get('status') == 'queued' and decision == 'abort':
            q_decision = 'abort'
        queue_decisions.append({
            'queue_id': queue_id,
            'decision': q_decision,
            'rationale': f"{decision} based on {q.get('stage') or 'stage'} evidence: {note_text}.",
            'source_result_id': q.get('result_id')
        })
    entry = {
        'strategy_spec_id': spec_id,
        'decision': decision,
        'rationale': rationale or f"{decision} due to {diagnosis} evidence from the current cycle.",
        'diagnosis_category': diagnosis,
        'queue_decisions': queue_decisions
    }
    if decision == 'refine':
        entry['iteration_intent'] = 'increase trade density while preserving the core thesis'
        entry['structural_change'] = 'relax or restructure the current mechanism based on failure evidence'
        entry['expected_effect'] = 'produce enough valid trades to survive train before entering test'
    out['strategy_decisions'].append(entry)
DECISIONS.write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps({'status':'ok','cycle_id':out['cycle_id'],'strategy_decisions':len(out['strategy_decisions'])}, indent=2))
