#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = ROOT / 'agents' / 'quandalf' / 'memory' / 'latest_journal.md'
REFLECTION = ROOT / 'agents' / 'quandalf' / 'memory' / 'reflection_packet.json'
DECISIONS = ROOT / 'agents' / 'quandalf' / 'memory' / 'refinement_decisions.json'
STATUS = ROOT / 'agents' / 'quandalf' / 'memory' / 'current_cycle_status.json'
STATE_OUT = ROOT / 'data' / 'state' / 'quandalf_learning_loop.json'
MEMORY_OUT = ROOT / 'agents' / 'quandalf' / 'memory' / 'latest_learning_loop.json'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def load_text(path):
    try:
        return path.read_text(encoding='utf-8')
    except Exception:
        return ''


def first_lines(text, limit=12):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s:
            out.append(s)
        if len(out) >= limit:
            break
    return out


def main():
    reflection = load_json(REFLECTION, {})
    decisions = load_json(DECISIONS, {})
    status = load_json(STATUS, {})
    journal_text = load_text(JOURNAL)

    outcomes = reflection.get('strategy_outcomes') or []
    strategy_decisions = decisions.get('strategy_decisions') or []

    what_failed = []
    what_worked = []
    why_it_failed = []
    iterate_next = []
    abandon = []
    indicator_role_notes = []
    management_notes = []
    diagnosis_breakdown = {}

    for item in outcomes:
        if not isinstance(item, dict):
            continue
        name = item.get('strategy_spec_id') or item.get('name') or 'unknown'
        action = item.get('recommended_action') or item.get('outcome') or 'unknown'
        diagnosis = item.get('diagnosis_category') or 'unknown'
        diagnosis_breakdown[diagnosis] = diagnosis_breakdown.get(diagnosis, 0) + 1
        rationale = str(item.get('rationale') or '').strip()
        if action in ('promote', 'refine'):
            what_worked.append(f"{name}: {rationale}")
        else:
            what_failed.append(f"{name}: {rationale}")
            why_it_failed.append(f"{name}: {diagnosis}")
        if item.get('allowed_next_actions'):
            iterate_next.append(f"{name}: allowed next actions -> {', '.join(item.get('allowed_next_actions') or [])}")
        if action == 'abort':
            abandon.append(f"{name}: {diagnosis}")
        for variant in item.get('variants') or []:
            if isinstance(variant, dict) and variant.get('risk_policy'):
                management_notes.append(f"{name}: risk/management -> {json.dumps(variant.get('risk_policy'), sort_keys=True)[:220]}")
        if item.get('trade_management'):
            management_notes.append(f"{name}: trade_management -> {json.dumps(item.get('trade_management'), sort_keys=True)[:220]}")

    for d in strategy_decisions:
        if not isinstance(d, dict):
            continue
        name = d.get('strategy_spec_id') or 'unknown'
        diag = d.get('diagnosis_category')
        if diag:
            why_it_failed.append(f"{name}: {diag}")
        rationale = str(d.get('rationale') or '').strip()
        if rationale:
            iterate_next.append(f"decision {name}: {rationale}")

    payload = {
        'version': 'quandalf-learning-loop-v2',
        'ts_iso': now_iso(),
        'sources': {
            'reflection_packet': str(REFLECTION.relative_to(ROOT)),
            'refinement_decisions': str(DECISIONS.relative_to(ROOT)),
            'current_cycle_status': str(STATUS.relative_to(ROOT)),
            'latest_journal': str(JOURNAL.relative_to(ROOT)) if JOURNAL.exists() else None,
        },
        'cycle_context': {
            'cycle_id': reflection.get('cycle_id') or status.get('cycle_id'),
            'asset': reflection.get('target_asset') or status.get('target_asset'),
            'timeframe': reflection.get('target_timeframe') or status.get('target_timeframe'),
            'mode': reflection.get('mode') or status.get('mode'),
            'research_direction': reflection.get('research_direction') or status.get('research_direction'),
        },
        'decision_summary': reflection.get('decision_summary') or {},
        'diagnosis_breakdown': diagnosis_breakdown,
        'dimensions': {
            'what_worked': what_worked[:12],
            'what_failed': what_failed[:12],
            'why_it_failed': why_it_failed[:12],
            'iterate_next': iterate_next[:12],
            'abandon': abandon[:12],
            'bench_for_later': [],
            'regime_notes': [json.dumps(status.get('regime_context') or {}, sort_keys=True)[:240]] if status.get('regime_context') else [],
            'strategy_family_notes': [json.dumps(status.get('new_families') or [])[:240], json.dumps(status.get('iterated_families') or [])[:240]],
            'indicator_role_notes': indicator_role_notes[:12],
            'management_notes': management_notes[:12],
        },
        'journal_excerpt': first_lines(journal_text, limit=10),
        'learning_requirements': [
            'Every cycle must yield diagnosis, lesson extraction, and durable learning update.',
            'Zero-trade outcomes require explicit diagnosis and one rescue attempt at most.',
            'PASS should flow into structured refinement variants, not cosmetic tweaks.',
        ],
    }

    journal_lines = [
        f"# Quandalf Journal — Cycle {payload['cycle_context']['cycle_id']}",
        "",
        f"- ts_iso: {payload['ts_iso']}",
        f"- mode: {payload['cycle_context'].get('mode')}",
        f"- lane: {payload['cycle_context'].get('asset')} / {payload['cycle_context'].get('timeframe')}",
        f"- research_direction: {payload['cycle_context'].get('research_direction')}",
        "",
        "## Decision Summary",
        json.dumps(payload.get('decision_summary') or {}, indent=2),
        "",
        "## Diagnosis Breakdown",
        json.dumps(payload.get('diagnosis_breakdown') or {}, indent=2),
        "",
        "## What Worked",
    ]
    journal_lines.extend([f"- {x}" for x in (payload.get('dimensions') or {}).get('what_worked', [])] or ["- none"])
    journal_lines.extend(["", "## What Failed"])
    journal_lines.extend([f"- {x}" for x in (payload.get('dimensions') or {}).get('what_failed', [])] or ["- none"])
    journal_lines.extend(["", "## Why It Failed"])
    journal_lines.extend([f"- {x}" for x in (payload.get('dimensions') or {}).get('why_it_failed', [])] or ["- none"])
    journal_lines.extend(["", "## Iterate Next"])
    journal_lines.extend([f"- {x}" for x in (payload.get('dimensions') or {}).get('iterate_next', [])] or ["- none"])
    journal_text_out = "\n".join(journal_lines) + "\n"

    STATE_OUT.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATE_OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    MEMORY_OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    JOURNAL.write_text(journal_text_out, encoding='utf-8')
    print(json.dumps({'status': 'ok', 'state': str(STATE_OUT), 'memory': str(MEMORY_OUT), 'journal': str(JOURNAL), 'cycle_id': payload['cycle_context']['cycle_id']}, indent=2))


if __name__ == '__main__':
    main()
