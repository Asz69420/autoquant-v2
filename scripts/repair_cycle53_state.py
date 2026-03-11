import json
import os
import sqlite3
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
REFLECTION = os.path.join(ROOT, "agents", "quandalf", "memory", "reflection_packet.json")
DECISIONS = os.path.join(ROOT, "agents", "quandalf", "memory", "refinement_decisions.json")
CURRENT_STATUS = os.path.join(ROOT, "agents", "quandalf", "memory", "current_cycle_status.json")
CURRENT_SPECS = os.path.join(ROOT, "data", "state", "current_cycle_specs.json")
RUN_STATE = os.path.join(ROOT, "data", "state", "research_cycle_started_at.json")
CYCLE_ORDERS = os.path.join(ROOT, "agents", "quandalf", "memory", "cycle_orders.json")
CYCLE_ID = 53
SPEC_IDS = [
    "QD-20260311-C053-ETH-1H-VWAP-RECLAIM-ROTATION-v1",
    "QD-20260311-C053-BTC-4H-RANGE-EDGE-ABSORPTION-v1",
    "QD-20260311-C053-TAO-4H-FLUSH-RECLAIM-PERSISTENCE-v1",
]
RATIONALES = {
    "QD-20260311-C053-ETH-1H-VWAP-RECLAIM-ROTATION-v1": "I aborted this ETH 1h VWAP reclaim rotation idea because the lane stayed too sparse on valid data and never produced enough executable trade density.",
    "QD-20260311-C053-BTC-4H-RANGE-EDGE-ABSORPTION-v1": "I aborted this BTC 4h range-edge absorption idea because the 4h grammar remained structurally too sparse and the evidence did not justify another refinement pass.",
    "QD-20260311-C053-TAO-4H-FLUSH-RECLAIM-PERSISTENCE-v1": "I aborted this TAO 4h flush reclaim persistence idea because both completed screen lanes showed zero-trade behavior on valid data, which points to a bad sparse design rather than a small implementation miss.",
}
DIAG = {sid: "too sparse" for sid in SPEC_IDS}


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, payload):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)


def find_spec_path(spec_id):
    for base, _, files in os.walk(os.path.join(ROOT, 'artifacts', 'strategy_specs')):
        for name in files:
            if name in {spec_id + '.strategy_spec.json', spec_id + '.json'}:
                return os.path.join(base, name)
    return ''


def load_spec(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
strategy_outcomes = []
strategy_decisions = []
resolved_queue_ids = []
for spec_id in SPEC_IDS:
    spec_path = find_spec_path(spec_id)
    spec = load_spec(spec_path)
    rows = [dict(r) for r in conn.execute("SELECT id, cycle_id, strategy_spec_id, variant_id, stage, status, result_id, notes, queued_at, started_at, completed_at FROM research_funnel_queue WHERE cycle_id=? AND strategy_spec_id=? ORDER BY queued_at ASC", (CYCLE_ID, spec_id)).fetchall()]
    queue_summary = []
    queue_decisions = []
    for row in rows:
        notes = row.get('notes')
        try:
            notes_json = json.loads(notes) if isinstance(notes, str) and notes else (notes or {})
        except Exception:
            notes_json = {'raw': notes}
        queue_summary.append({
            'queue_id': row['id'],
            'stage': row.get('stage'),
            'status': row.get('status'),
            'result_id': row.get('result_id'),
            'notes': notes_json,
            'queued_at': row.get('queued_at'),
            'completed_at': row.get('completed_at'),
        })
        queue_decisions.append({
            'queue_id': row['id'],
            'decision': 'abort',
            'rationale': f"I aborted queue row {row['id']} because its evidence was {notes_json.get('error') or notes_json.get('reason') or notes_json.get('status') or 'too sparse / zero-trade behavior'}.",
            'source_result_id': row.get('result_id'),
        })
        if str(row.get('status') or '').lower() in {'queued', 'running'}:
            resolved_queue_ids.append(row['id'])
    strategy_outcomes.append({
        'strategy_spec_id': spec_id,
        'spec_path': spec_path,
        'name': spec.get('name') or spec_id,
        'asset': spec.get('asset'),
        'timeframe': spec.get('timeframe'),
        'strategy_family': spec.get('family_name'),
        'edge_mechanism': spec.get('edge_mechanism'),
        'hypothesis': spec.get('hypothesis') or spec.get('thesis') or spec.get('rationale'),
        'queue': queue_summary,
        'results': [],
        'latest_result': None,
        'result_count': 0,
        'outcome': 'abort',
        'recommended_action': 'abort',
        'decision_required': False,
        'allowed_next_actions': ['refine', 'abort'],
        'diagnosis_category': DIAG[spec_id],
        'rationale': RATIONALES[spec_id],
        'has_zero_trade_signal': True,
    })
    strategy_decisions.append({
        'strategy_spec_id': spec_id,
        'decision': 'abort',
        'rationale': RATIONALES[spec_id],
        'diagnosis_category': DIAG[spec_id],
        'queue_decisions': queue_decisions,
    })

for qid in resolved_queue_ids:
    conn.execute("UPDATE research_funnel_queue SET status='done', completed_at=?, started_at=NULL, notes=? WHERE id=?", (
        datetime.now(timezone.utc).isoformat(),
        json.dumps({'status': 'decision_resolved', 'decision': 'abort', 'reason': 'legacy_cycle_abort_normalized', 'resolved_at': datetime.now(timezone.utc).isoformat()}),
        qid,
    ))
conn.commit()
conn.close()

orders = load_json(CYCLE_ORDERS, {})
reflection = {
    'ts_iso': datetime.now(timezone.utc).isoformat(),
    'type': 'reflection',
    'cycle_id': CYCLE_ID,
    'mode': orders.get('mode') or 'explore',
    'research_direction': orders.get('research_direction') or 'explore_new',
    'target_asset': orders.get('target_asset'),
    'target_timeframe': orders.get('target_timeframe'),
    'strategy_outcomes': strategy_outcomes,
    'recent_results': strategy_outcomes,
    'external_context_results': [],
    'recent_lessons': [],
    'result_count': 0,
    'current_cycle_result_count': 0,
    'current_cycle_strategy_count': len(strategy_outcomes),
    'external_result_count': 0,
    'any_promising': False,
    'best_pf': 0,
    'best_qscore': 0,
    'decision_summary': {'promote': 0, 'refine': 0, 'abort': len(strategy_outcomes), 'zero_trade': len(strategy_outcomes)},
    'guidance': {
        'focus_level': 'strategy_and_queue',
        'instruction': 'Cycle repaired into new schema. Strategy decisions and queue decisions are explicit and authoritative.'
    }
}
write_json(REFLECTION, reflection)
write_json(DECISIONS, {'cycle_id': CYCLE_ID, 'ts_iso': datetime.now(timezone.utc).isoformat(), 'strategy_decisions': strategy_decisions, 'jobs': []})

status = load_json(CURRENT_STATUS, {})
if int(status.get('cycle_id') or 0) == CYCLE_ID:
    status['next_cycle_focus'] = 'abort sparse 4h families and move to new active cycle'
    status['rationale'] = 'Cycle 53 repaired into the new decision schema; sparse zero-trade families were aborted explicitly.'
    write_json(CURRENT_STATUS, status)

print(json.dumps({'status': 'ok', 'cycle_id': CYCLE_ID, 'resolved_queue_ids': resolved_queue_ids, 'strategy_decisions': len(strategy_decisions)}, indent=2))
