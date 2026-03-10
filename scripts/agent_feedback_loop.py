#!/usr/bin/env python3
"""Compact agent feedback + Oragorn synthesis with noise reduction."""
import json
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / 'config' / 'agent-feedback.json'
OUT = ROOT / 'data' / 'state' / 'agent_feedback_summary.json'


def load(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def read_text(path):
    try:
        return Path(path).read_text(encoding='utf-8')
    except Exception:
        return ''


def parse_dt(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except Exception:
        return None


def main():
    cfg = load(CFG, {})
    sources = cfg.get('sources', {})
    hours = int(cfg.get('cadence', {}).get('operational_window_hours', 6))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    messages = load(ROOT / sources.get('message_board', ''), {}).get('messages', [])
    recent = []
    for m in messages:
        ts = parse_dt(m.get('ts_iso'))
        if ts and ts >= cutoff:
            recent.append(m)

    counts = Counter()
    compressed = []
    for m in recent:
        msg = re.sub(r'\(\d+\)', '(n)', str(m.get('message', '')).strip())
        key = (m.get('from'), m.get('type'), msg)
        counts[key] += 1
    for (sender, msg_type, msg), count in counts.most_common(12):
        compressed.append({
            'from': sender,
            'type': msg_type,
            'message': msg,
            'count': count,
        })

    quandalf_status = load(ROOT / sources.get('quandalf_status', ''), {})
    governance_audit = load(ROOT / sources.get('governance_audit', ''), {})
    task_board = load(ROOT / sources.get('task_board', ''), {'summary': {}})
    frodex_status = read_text(ROOT / sources.get('frodex_status', ''))[:300]
    logron_status = read_text(ROOT / sources.get('logron_status', ''))[:300]
    quandalf_journal = read_text(ROOT / sources.get('quandalf_journal', ''))[:500]

    high_gateway = any('gateway errors' in item['message'].lower() for item in compressed)
    strategy_concern = 'too sparse' in quandalf_journal.lower() or 'event-driven' in quandalf_journal.lower()

    actions = []
    if high_gateway:
        actions.append('investigate_gateway_error_growth')
    if strategy_concern:
        actions.append('bias_next_orders_toward_broader_continuous_expressions')
    if governance_audit.get('status') == 'warn':
        actions.append('check_memory_governance_warnings')

    payload = {
        'version': 'agent-feedback-summary-v1',
        'ts_iso': datetime.now(timezone.utc).isoformat(),
        'window_hours': hours,
        'task_summary': task_board.get('summary', {}),
        'quandalf_cycle_status': {
            'cycle_id': quandalf_status.get('cycle_id'),
            'target_asset': quandalf_status.get('target_asset'),
            'target_timeframe': quandalf_status.get('target_timeframe'),
            'specs_produced': quandalf_status.get('specs_produced'),
            'next_cycle_focus': quandalf_status.get('next_cycle_focus'),
        },
        'compressed_signals': compressed,
        'actions': actions,
        'status_snippets': {
            'frodex': frodex_status,
            'logron': logron_status,
            'quandalf_journal': quandalf_journal,
        }
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
