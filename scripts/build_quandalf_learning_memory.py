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
ROLLING_WINDOW = 5


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


def dedupe_keep_order(items, limit=12):
    out = []
    seen = set()
    for item in items or []:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def compact_json(value, limit=240):
    try:
        text = json.dumps(value, sort_keys=True)
    except Exception:
        text = str(value)
    return text[:limit]


def summarize_current_cycle(reflection, decisions, status, journal_text):
    outcomes = reflection.get('strategy_outcomes') or []
    strategy_decisions = decisions.get('strategy_decisions') or []

    decision_by_spec = {}
    for item in strategy_decisions:
        if isinstance(item, dict):
            decision_by_spec[str(item.get('strategy_spec_id') or '').strip()] = item

    what_failed = []
    what_worked = []
    why_it_failed = []
    iterate_next = []
    abandon = []
    indicator_role_notes = []
    management_notes = []
    strategy_reviews = []
    diagnosis_breakdown = {}
    assets_touched = []
    timeframes_touched = []
    queue_total = 0
    decided_queue_total = 0
    result_total = 0

    decision_summary = {'pass': 0, 'refine': 0, 'abort': 0, 'zero_trade': 0}

    for item in outcomes:
        if not isinstance(item, dict):
            continue
        spec_id = str(item.get('strategy_spec_id') or item.get('name') or 'unknown').strip()
        assets_touched.append(str(item.get('asset') or '').strip())
        timeframes_touched.append(str(item.get('timeframe') or '').strip())

        queue = item.get('queue') or []
        results = item.get('results') or []
        queue_total += len(queue)
        result_total += len(results)
        if item.get('has_zero_trade_signal'):
            decision_summary['zero_trade'] += 1

        train_result = item.get('train_result') or {}
        test_results = item.get('test_results') or []
        latest_result = item.get('latest_result') or {}
        queue_evidence_present = bool(item.get('queue') or [])
        result_evidence_present = bool(results or latest_result)
        enough_evidence = result_evidence_present or queue_evidence_present

        diagnosis = str(item.get('diagnosis_category') or 'unknown').strip() or 'unknown'
        rationale = str(item.get('rationale') or '').strip()
        action = str(item.get('recommended_action') or item.get('outcome') or 'unknown').strip().lower()

        if not enough_evidence:
            diagnosis = 'untested'
            action = 'untested'
            rationale = 'insufficient evidence: no recorded backtest or queue outcome yet'

        diagnosis_breakdown[diagnosis] = diagnosis_breakdown.get(diagnosis, 0) + 1

        if action in ('pass', 'refine'):
            what_worked.append(f"{spec_id}: {rationale}")
        elif action == 'untested':
            what_failed.append(f"{spec_id}: {rationale}")
            why_it_failed.append(f"{spec_id}: untested")
        else:
            what_failed.append(f"{spec_id}: {rationale}")
            why_it_failed.append(f"{spec_id}: {diagnosis}")

        if enough_evidence and item.get('allowed_next_actions'):
            iterate_next.append(f"{spec_id}: allowed next actions -> {', '.join(item.get('allowed_next_actions') or [])}")
        elif not enough_evidence:
            iterate_next.append(f"{spec_id}: await tested evidence before deciding whether the mechanism is weak, the lane is wrong, or the idea deserves refinement")
        if enough_evidence and action == 'abort':
            abandon.append(f"{spec_id}: {diagnosis}")

        for variant in item.get('variants') or []:
            if isinstance(variant, dict) and variant.get('risk_policy'):
                management_notes.append(f"{spec_id}: risk/management -> {compact_json(variant.get('risk_policy'))}")
        if item.get('trade_management'):
            management_notes.append(f"{spec_id}: trade_management -> {compact_json(item.get('trade_management'))}")

        matched_decision = decision_by_spec.get(spec_id) or {}
        decision = str(matched_decision.get('decision') or '').strip().lower()
        if enough_evidence and decision in ('pass', 'refine', 'abort'):
            decision_summary[decision] += 1
        queue_decisions = matched_decision.get('queue_decisions') or []
        if isinstance(queue_decisions, list):
            decided_queue_total += len(queue_decisions)
        diag = str(matched_decision.get('diagnosis_category') or '').strip()
        if enough_evidence and diag:
            why_it_failed.append(f"{spec_id}: {diag}")
        decision_rationale = str(matched_decision.get('rationale') or '').strip()
        if decision_rationale:
            iterate_next.append(f"decision {spec_id}: {decision_rationale}")

        queue_evidence = []
        for qd in queue_decisions if isinstance(queue_decisions, list) else []:
            if not isinstance(qd, dict):
                continue
            queue_id = str(qd.get('queue_id') or '').strip()
            qdecision = str(qd.get('decision') or '').strip().lower()
            qrationale = str(qd.get('rationale') or '').strip()
            if queue_id and (qdecision or qrationale):
                queue_evidence.append(f"{queue_id}={qdecision or 'n/a'} ({qrationale or 'no rationale'})")

        stage_metrics = item.get('stage_metrics') or {}
        strategy_reviews.append({
            'strategy_spec_id': spec_id,
            'asset': item.get('asset'),
            'timeframe': item.get('timeframe'),
            'edge_mechanism': item.get('edge_mechanism'),
            'hypothesis': item.get('hypothesis'),
            'diagnosis_category': ('untested' if not enough_evidence else (diag or diagnosis)),
            'decision': ('untested' if not enough_evidence else (decision or action)),
            'decision_rationale': ('insufficient evidence: no recorded backtest or queue outcome yet' if not enough_evidence else (decision_rationale or rationale)),
            'why_asset': f"asset={item.get('asset') or 'unknown'} from chosen lane / result context",
            'why_timeframe': f"timeframe={item.get('timeframe') or 'unknown'} from chosen lane / result context",
            'queue_evidence': queue_evidence,
            'train_result': train_result,
            'test_results': test_results,
            'stage_metrics': stage_metrics,
            'latest_result': latest_result,
        })

        for result in results:
            if not isinstance(result, dict):
                continue
            assets_touched.append(str(result.get('asset') or '').strip())
            timeframes_touched.append(str(result.get('timeframe') or '').strip())

    cycle_id = reflection.get('cycle_id') or status.get('cycle_id') or decisions.get('cycle_id') or 0
    cycle_summary = {
        'cycle_id': cycle_id,
        'ts_iso': now_iso(),
        'mode': reflection.get('mode') or status.get('mode'),
        'research_direction': reflection.get('research_direction') or status.get('research_direction'),
        'assets_touched': sorted({x for x in assets_touched if x}),
        'timeframes_touched': sorted({x for x in timeframes_touched if x}),
        'strategy_count': len([x for x in outcomes if isinstance(x, dict)]),
        'queue_total': queue_total,
        'queue_decided_total': decided_queue_total,
        'result_total': result_total,
        'decision_summary': decision_summary,
        'diagnosis_breakdown': diagnosis_breakdown,
    }

    payload = {
        'version': 'quandalf-learning-loop-v3',
        'ts_iso': now_iso(),
        'sources': {
            'reflection_packet': str(REFLECTION.relative_to(ROOT)),
            'refinement_decisions': str(DECISIONS.relative_to(ROOT)),
            'current_cycle_status': str(STATUS.relative_to(ROOT)),
            'latest_journal': str(JOURNAL.relative_to(ROOT)) if JOURNAL.exists() else None,
        },
        'cycle_context': {
            'cycle_id': cycle_id,
            'asset': reflection.get('target_asset') or status.get('target_asset'),
            'timeframe': reflection.get('target_timeframe') or status.get('target_timeframe'),
            'mode': reflection.get('mode') or status.get('mode'),
            'research_direction': reflection.get('research_direction') or status.get('research_direction'),
        },
        'decision_summary': decision_summary,
        'diagnosis_breakdown': diagnosis_breakdown,
        'dimensions': {
            'what_worked': dedupe_keep_order(what_worked),
            'what_failed': dedupe_keep_order(what_failed),
            'why_it_failed': dedupe_keep_order(why_it_failed),
            'iterate_next': dedupe_keep_order(iterate_next),
            'abandon': dedupe_keep_order(abandon),
            'bench_for_later': [],
            'regime_notes': [compact_json(status.get('regime_context') or {})] if status.get('regime_context') else [],
            'strategy_family_notes': dedupe_keep_order([
                compact_json(status.get('new_families') or []),
                compact_json(status.get('iterated_families') or []),
                compact_json(status.get('abandoned_families') or []),
            ], limit=6),
            'indicator_role_notes': dedupe_keep_order(indicator_role_notes),
            'management_notes': dedupe_keep_order(management_notes),
            'strategy_reviews': strategy_reviews,
        },
        'journal_excerpt': first_lines(journal_text, limit=10),
        'learning_requirements': [
            'Every cycle must yield diagnosis, lesson extraction, and durable learning update.',
            'Zero-trade outcomes require explicit diagnosis and one rescue attempt at most.',
            'Only three terminal decisions are legal: pass, refine, abort.',
            'PASS should flow into structured refinement variants, not cosmetic tweaks.',
        ],
        'rolling_recent_cycles': [],
        'rolling_insights': {},
    }
    return payload, cycle_summary


def merge_recent_cycles(previous_payload, cycle_summary):
    recent = []
    for item in (previous_payload.get('rolling_recent_cycles') or []):
        if isinstance(item, dict):
            recent.append(item)
    recent = [item for item in recent if int(item.get('cycle_id') or 0) != int(cycle_summary.get('cycle_id') or 0)]
    recent.append(cycle_summary)
    recent = sorted(recent, key=lambda x: int(x.get('cycle_id') or 0))[-ROLLING_WINDOW:]
    return recent


def build_rolling_insights(recent_cycles):
    totals = {
        'cycles_considered': len(recent_cycles),
        'pass': 0,
        'refine': 0,
        'abort': 0,
        'zero_trade': 0,
        'strategies': 0,
        'queue_rows': 0,
        'queue_rows_decided': 0,
        'saved_results': 0,
    }
    diagnosis_totals = {}
    assets = set()
    timeframes = set()

    for item in recent_cycles:
        if not isinstance(item, dict):
            continue
        ds = item.get('decision_summary') or {}
        db = item.get('diagnosis_breakdown') or {}
        totals['pass'] += int(ds.get('pass') or 0)
        totals['refine'] += int(ds.get('refine') or 0)
        totals['abort'] += int(ds.get('abort') or 0)
        totals['zero_trade'] += int(ds.get('zero_trade') or 0)
        totals['strategies'] += int(item.get('strategy_count') or 0)
        totals['queue_rows'] += int(item.get('queue_total') or 0)
        totals['queue_rows_decided'] += int(item.get('queue_decided_total') or 0)
        totals['saved_results'] += int(item.get('result_total') or 0)
        for key, value in db.items():
            diagnosis_totals[key] = diagnosis_totals.get(key, 0) + int(value or 0)
        for asset in item.get('assets_touched') or []:
            if asset:
                assets.add(asset)
        for tf in item.get('timeframes_touched') or []:
            if tf:
                timeframes.add(tf)

    return {
        'window_size': len(recent_cycles),
        'totals': totals,
        'diagnosis_breakdown': diagnosis_totals,
        'assets_touched': sorted(assets),
        'timeframes_touched': sorted(timeframes),
        'note': 'untested items are tracked separately and must not be treated as strategic failure judgments',
    }


def normalize_first_person_line(text):
    text = str(text or '').strip()
    if not text:
        return 'none'
    replacements = [
        ('Quandalf must explicitly choose iterate or abort.', ''),
        ('Quandalf must explicitly choose refine or abort.', ''),
        ('allowed next actions -> refine, abort', 'The only legal next actions were refine or abort'),
        ('allowed next actions -> pass, refine, abort', 'The legal next actions were pass, refine, or abort'),
        ('decision ', ''),
        ('Both completed screen lanes ended with zero-trade integrity skips, so', 'Both completed screen lanes ended with zero-trade integrity skips, so'),
        ('Both completed screen lanes ended in integrity_skip:zero_trades_both_samples, so', 'Both completed screen lanes ended in integrity_skip:zero_trades_both_samples, so'),
        ('This strategy produced', 'This strategy produced'),
        ('The strategy produced', 'The strategy produced'),
        ('The strategy', 'The strategy'),
        ('0 trades on valid data', '0 trades on valid data'),
        ('abort: fail with', 'abort: fail with'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = ' '.join(text.split()).strip(' -')
    if not text:
        return 'none'
    if text.startswith('QD-') and ': ' in text:
        spec_id, rest = text.split(': ', 1)
        rest = ' '.join(str(rest).split()).strip(' -')
        return f'On {spec_id}, {rest}' if rest else f'On {spec_id}'
    return text


def build_journal_text(payload):
    recent = payload.get('rolling_recent_cycles') or []
    rolling = payload.get('rolling_insights') or {}
    totals = rolling.get('totals') or {}
    dims = payload.get('dimensions') or {}
    journal_lines = [
        f"# Quandalf Journal — Cycle {payload['cycle_context']['cycle_id']}",
        "",
        f"- ts_iso: {payload['ts_iso']}",
        f"- mode: {payload['cycle_context'].get('mode')}",
        f"- lane: {payload['cycle_context'].get('asset')} / {payload['cycle_context'].get('timeframe')}",
        f"- research_direction: {payload['cycle_context'].get('research_direction')}",
        "",
        "## My Current Decision Summary",
        json.dumps(payload.get('decision_summary') or {}, indent=2),
        "",
        "## My Current Diagnosis Breakdown",
        json.dumps(payload.get('diagnosis_breakdown') or {}, indent=2),
        "",
        "## Rolling Last 5 Cycles",
        json.dumps({
            'window_size': rolling.get('window_size', 0),
            'totals': totals,
            'diagnosis_breakdown': rolling.get('diagnosis_breakdown') or {},
            'assets_touched': rolling.get('assets_touched') or [],
            'timeframes_touched': rolling.get('timeframes_touched') or [],
            'cycle_ids': [item.get('cycle_id') for item in recent],
        }, indent=2),
        "",
        "## What Worked",
    ]
    journal_lines.extend([f"- {normalize_first_person_line(x)}" for x in dims.get('what_worked', [])] or ["- none"])
    awaiting = [x for x in (dims.get('what_failed', []) or []) if 'insufficient evidence' in str(x).lower() or 'untested' in str(x).lower()]
    failed = [x for x in (dims.get('what_failed', []) or []) if x not in awaiting]
    judged = [x for x in (dims.get('why_it_failed', []) or []) if 'untested' not in str(x).lower()]
    awaiting_next = [x for x in (dims.get('iterate_next', []) or []) if 'await tested evidence' in str(x).lower()]
    improve_next = [x for x in (dims.get('iterate_next', []) or []) if x not in awaiting_next]

    journal_lines.extend(["", "## Awaiting Evidence"])
    journal_lines.extend([f"- {normalize_first_person_line(x)}" for x in awaiting] or ["- none"])
    journal_lines.extend(["", "## What Failed"])
    journal_lines.extend([f"- {normalize_first_person_line(x)}" for x in failed] or ["- none"])
    journal_lines.extend(["", "## Why I Judged It That Way"])
    journal_lines.extend([f"- {normalize_first_person_line(x)}" for x in judged] or ["- none"])
    journal_lines.extend(["", "## What I Would Improve Next"])
    journal_lines.extend([f"- {normalize_first_person_line(x)}" for x in improve_next] or ["- none"])
    journal_lines.extend(["", "## What Still Needs Testing"])
    journal_lines.extend([f"- {normalize_first_person_line(x)}" for x in awaiting_next] or ["- none"])
    journal_lines.extend(["", "## Strategy-by-Strategy Reasons"])
    reviews = dims.get('strategy_reviews') or []
    if reviews:
        for item in reviews:
            if not isinstance(item, dict):
                continue
            journal_lines.append(f"- {item.get('strategy_spec_id')}: asset={item.get('asset') or '?'} | timeframe={item.get('timeframe') or '?'} | decision={item.get('decision') or '?'} | diagnosis={item.get('diagnosis_category') or '?'}")
            if item.get('edge_mechanism'):
                journal_lines.append(f"  mechanism: {item.get('edge_mechanism')}")
            if item.get('hypothesis'):
                journal_lines.append(f"  thesis: {item.get('hypothesis')}")
            train_result = item.get('train_result') or {}
            if train_result:
                journal_lines.append(f"  train: QS {train_result.get('score_total') or train_result.get('qscore') or 0} | Sharpe {train_result.get('sharpe_ratio') or 0} | PF {train_result.get('profit_factor') or 0} | DD {train_result.get('max_drawdown_pct') or 0}% | Trades {train_result.get('total_trades') or 0}")
            stage_metrics = item.get('stage_metrics') or {}
            test_stage = stage_metrics.get('test') or {}
            if test_stage and int(test_stage.get('runs') or 0) > 0:
                journal_lines.append(f"  test: runs={test_stage.get('runs') or 0} | trades={test_stage.get('trades') or 0} | best QS {test_stage.get('best_qscore') or 0} | best Sharpe {test_stage.get('best_sharpe') or 0} | best PF {test_stage.get('best_pf') or 0} | max DD {test_stage.get('max_dd') or 0}%")
            if item.get('decision_rationale'):
                journal_lines.append(f"  why: {normalize_first_person_line(item.get('decision_rationale'))}")
            for evidence in (item.get('queue_evidence') or [])[:3]:
                journal_lines.append(f"  evidence: {evidence}")
    else:
        journal_lines.append("- none")
    return "\n".join(journal_lines) + "\n"


def main():
    reflection = load_json(REFLECTION, {})
    decisions = load_json(DECISIONS, {})
    status = load_json(STATUS, {})
    previous = load_json(STATE_OUT, {})
    journal_text = load_text(JOURNAL)

    payload, cycle_summary = summarize_current_cycle(reflection, decisions, status, journal_text)
    payload['rolling_recent_cycles'] = merge_recent_cycles(previous, cycle_summary)
    payload['rolling_insights'] = build_rolling_insights(payload['rolling_recent_cycles'])
    journal_text_out = build_journal_text(payload)

    STATE_OUT.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATE_OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    MEMORY_OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    JOURNAL.write_text(journal_text_out, encoding='utf-8')
    print(json.dumps({
        'status': 'ok',
        'state': str(STATE_OUT),
        'memory': str(MEMORY_OUT),
        'journal': str(JOURNAL),
        'cycle_id': payload['cycle_context']['cycle_id'],
        'rolling_window': len(payload['rolling_recent_cycles']),
    }, indent=2))


if __name__ == '__main__':
    main()
