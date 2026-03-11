#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFLECTION = ROOT / 'agents' / 'quandalf' / 'memory' / 'reflection_packet.json'
DECISIONS = ROOT / 'agents' / 'quandalf' / 'memory' / 'refinement_decisions.json'
RUN_STATE = ROOT / 'data' / 'state' / 'research_cycle_started_at.json'
METRICS = ROOT / 'data' / 'state' / 'current_cycle_metrics.json'
OUT = ROOT / 'data' / 'state' / 'current_cycle_snapshot.json'


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main():
    reflection = load_json(REFLECTION, {})
    decisions = load_json(DECISIONS, {})
    run_state = load_json(RUN_STATE, {})
    metrics = load_json(METRICS, {})

    reflection_cycle = int(reflection.get('cycle_id') or 0)
    decision_cycle = int(decisions.get('cycle_id') or 0)
    run_cycle = int(run_state.get('cycle_id') or 0)

    canonical_cycle = 0
    if reflection_cycle and reflection_cycle == decision_cycle:
        canonical_cycle = reflection_cycle
    elif reflection_cycle:
        canonical_cycle = reflection_cycle
    elif decision_cycle:
        canonical_cycle = decision_cycle
    else:
        canonical_cycle = run_cycle

    strategy_outcomes = [x for x in (reflection.get('strategy_outcomes') or []) if isinstance(x, dict)]
    strategy_decisions = [x for x in (decisions.get('strategy_decisions') or []) if isinstance(x, dict)]

    executed_queue_ids = []
    for item in strategy_outcomes:
        for q in (item.get('queue') or []):
            if not isinstance(q, dict):
                continue
            qid = str(q.get('queue_id') or '').strip()
            status = str(q.get('status') or '').strip().lower()
            if qid and status in {'done', 'skipped', 'failed', 'error', 'complete', 'completed'}:
                executed_queue_ids.append(qid)

    queue_decisions = []
    for item in strategy_decisions:
        for qd in (item.get('queue_decisions') or []):
            if isinstance(qd, dict):
                queue_decisions.append(qd)

    snapshot = {
        'version': 'cycle-snapshot-v1',
        'ts_iso': now_iso(),
        'cycle_id': canonical_cycle,
        'sources': {
            'run_cycle_id': run_cycle,
            'reflection_cycle_id': reflection_cycle,
            'decision_cycle_id': decision_cycle,
        },
        'status': {
            'cycle_aligned': canonical_cycle > 0 and reflection_cycle == decision_cycle == canonical_cycle,
            'run_state_ahead_of_snapshot': bool(run_cycle and canonical_cycle and run_cycle > canonical_cycle),
        },
        'counts': {
            'strategies_reflected': len(strategy_outcomes),
            'strategy_decisions': len(strategy_decisions),
            'executed_backtest_rows': len(executed_queue_ids),
            'queue_row_decisions': len(queue_decisions),
            'db_backtests_saved': int(metrics.get('backtests_completed', 0) or 0),
        },
        'decision_summary': {
            'pass': sum(1 for x in strategy_decisions if str(x.get('decision') or '').lower() == 'pass'),
            'refine': sum(1 for x in strategy_decisions if str(x.get('decision') or '').lower() == 'refine'),
            'abort': sum(1 for x in strategy_decisions if str(x.get('decision') or '').lower() == 'abort'),
            'queue_pass': sum(1 for x in queue_decisions if str(x.get('decision') or '').lower() == 'pass'),
            'queue_refine': sum(1 for x in queue_decisions if str(x.get('decision') or '').lower() == 'refine'),
            'queue_abort': sum(1 for x in queue_decisions if str(x.get('decision') or '').lower() == 'abort'),
        },
        'strategy_outcomes': strategy_outcomes,
        'strategy_decisions': strategy_decisions,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'ok', 'snapshot': str(OUT), 'cycle_id': canonical_cycle}, indent=2))


if __name__ == '__main__':
    main()
