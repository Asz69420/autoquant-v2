#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEARNING = ROOT / 'data' / 'state' / 'quandalf_learning_loop.json'
REFLECTION = ROOT / 'agents' / 'quandalf' / 'memory' / 'reflection_packet.json'
DECISIONS = ROOT / 'agents' / 'quandalf' / 'memory' / 'refinement_decisions.json'
FALLBACK = ROOT / 'agents' / 'quandalf' / 'memory' / 'latest_journal.md'
TG_NOTIFY = ROOT / 'scripts' / 'tg_notify.py'

BOLD = {
    'A':'𝐀','B':'𝐁','C':'𝐂','D':'𝐃','E':'𝐄','F':'𝐅','G':'𝐆','H':'𝐇','I':'𝐈','J':'𝐉','K':'𝐊','L':'𝐋','M':'𝐌','N':'𝐍','O':'𝐎','P':'𝐏','Q':'𝐐','R':'𝐑','S':'𝐒','T':'𝐓','U':'𝐔','V':'𝐕','W':'𝐖','X':'𝐗','Y':'𝐘','Z':'𝐙',
    'a':'𝐚','b':'𝐛','c':'𝐜','d':'𝐝','e':'𝐞','f':'𝐟','g':'𝐠','h':'𝐡','i':'𝐢','j':'𝐣','k':'𝐤','l':'𝐥','m':'𝐦','n':'𝐧','o':'𝐨','p':'𝐩','q':'𝐪','r':'𝐫','s':'𝐬','t':'𝐭','u':'𝐮','v':'𝐯','w':'𝐰','x':'𝐱','y':'𝐲','z':'𝐳',
    '0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗'
}


def bold(text: str) -> str:
    return ''.join(BOLD.get(ch, ch) for ch in text)


def load_json(path: Path, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def load_learning():
    return load_json(LEARNING, None) if LEARNING.exists() else None


def first(items, default='—'):
    if not items:
        return default
    if isinstance(items, list):
        for item in items:
            text = str(item).strip()
            if text:
                return text
        return default
    text = str(items).strip()
    return text or default


def compact(text, limit=220):
    text = ' '.join(str(text or '').split())
    if not text:
        return '—'
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def to_first_person(text):
    text = compact(text, limit=320)
    if text == '—':
        return text
    replacements = [
        ('Quandalf must explicitly choose iterate or abort.', 'I must explicitly choose refine or abort.'),
        ('Quandalf must explicitly choose refine or abort.', 'I must explicitly choose refine or abort.'),
        ('allowed next actions -> refine, abort', 'my legal next actions are refine or abort'),
        ('allowed next actions -> pass, refine, abort', 'my legal next actions are pass, refine, or abort'),
        ('This does not justify iteration.', 'I do not think this justifies refinement.'),
        ('This strategy produced', 'I saw this strategy produce'),
        ('This strategy', 'I designed this strategy and'),
        ('The strategy produced', 'I saw the strategy produce'),
        ('The strategy', 'I found that the strategy'),
        ('Both completed screen lanes ended with zero-trade integrity skips, so', 'I saw both completed screen lanes end with zero-trade integrity skips, so'),
        ('Both completed screen lanes ended in integrity_skip:zero_trades_both_samples, so', 'I saw both completed screen lanes end in integrity_skip:zero_trades_both_samples, so'),
        ('0 trades on valid data', 'I got 0 trades on valid data'),
        ('abort: fail with', 'I aborted it after a fail with'),
        ('decision ', ''),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    if ': my legal next actions are ' in text:
        text = text.replace(': my legal next actions are ', ': I see that my legal next actions are ')
    if text.startswith('QD-') and ': ' in text:
        spec_id, rest = text.split(': ', 1)
        if rest.startswith('I got ') or rest.startswith('I aborted ') or rest.startswith('I saw ') or rest.startswith('I found ') or rest.startswith('I designed ') or rest.startswith('I see '):
            return f'On {spec_id}, {rest[0].lower() + rest[1:]}'
        return f'On {spec_id}, {rest}'
    return text


def summarize_list(items, limit=4):
    clean = []
    seen = set()
    for item in items or []:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        clean.append(text)
    if not clean:
        return '—'
    shown = clean[:limit]
    suffix = '' if len(clean) <= limit else f' +{len(clean) - limit} more'
    return ', '.join(shown) + suffix


def extract_batch_summary(reflection, decisions):
    outcomes = reflection.get('strategy_outcomes') or []
    strategy_decisions = decisions.get('strategy_decisions') or []

    assets = []
    timeframes = []
    queue_total = 0
    result_total = 0
    best_result = None
    best_reason = None

    for item in outcomes:
        if not isinstance(item, dict):
            continue
        asset = str(item.get('asset') or '').strip()
        timeframe = str(item.get('timeframe') or '').strip()
        if asset:
            assets.append(asset)
        if timeframe:
            timeframes.append(timeframe)
        queue = item.get('queue') or []
        queue_total += len(queue)
        results = item.get('results') or []
        result_total += len(results)
        for result in results:
            if not isinstance(result, dict):
                continue
            r_asset = str(result.get('asset') or '').strip()
            r_tf = str(result.get('timeframe') or '').strip()
            if r_asset:
                assets.append(r_asset)
            if r_tf:
                timeframes.append(r_tf)
            score = result.get('score_total')
            if score is None:
                continue
            if best_result is None or float(score) > float(best_result.get('score_total') or -999):
                best_result = result
                best_reason = item.get('strategy_spec_id')

    decision_counts = {'pass': 0, 'refine': 0, 'abort': 0}
    for item in strategy_decisions:
        if not isinstance(item, dict):
            continue
        decision = str(item.get('decision') or '').strip().lower()
        if decision in decision_counts:
            decision_counts[decision] += 1

    return {
        'assets': sorted(set(assets)),
        'timeframes': sorted(set(timeframes)),
        'strategy_count': len([x for x in outcomes if isinstance(x, dict)]),
        'queue_total': queue_total,
        'result_total': result_total,
        'decision_counts': decision_counts,
        'best_result': best_result,
        'best_reason': best_reason,
    }


def build_from_learning(data, reflection, decisions):
    ctx = data.get('cycle_context') or {}
    dims = data.get('dimensions') or {}
    strategy_reviews = dims.get('strategy_reviews') or []
    summary = extract_batch_summary(reflection, decisions)
    cycle_id = ctx.get('cycle_id') or reflection.get('cycle_id') or decisions.get('cycle_id') or '—'
    mode = ctx.get('mode') or '—'
    direction = ctx.get('research_direction') or '—'
    decision_summary = data.get('decision_summary') or {}
    diagnosis = data.get('diagnosis_breakdown') or {}

    best_result = summary.get('best_result') or {}
    best_line = '—'
    if best_result:
        best_line = (
            f"{summary.get('best_reason') or 'unknown'} → "
            f"{best_result.get('asset') or '?'} {best_result.get('timeframe') or '?'} | "
            f"QS {best_result.get('score_total') or 0:.2f} | "
            f"PF {best_result.get('profit_factor') or 0:.2f} | "
            f"Trades {best_result.get('total_trades') or 0}"
        )

    failed_items = dims.get('what_failed') or []
    why_items = dims.get('why_it_failed') or []
    next_items = dims.get('iterate_next') or []
    abandon_items = dims.get('abandon') or []
    lines = [
        f"🧠 {bold('Quandalf Journal — Cycle')} {cycle_id}",
        f"I ran in {mode} mode with direction {direction}.",
        f"I touched assets: {summarize_list(summary.get('assets'))}",
        f"I touched timeframes: {summarize_list(summary.get('timeframes'))}",
        f"I tested {summary.get('strategy_count', 0)} strategies across {summary.get('queue_total', 0)} queue rows and saved {summary.get('result_total', 0)} result rows.",
        '',
        f"{bold('My decision summary')}",
        f"• I ended with Pass {decision_summary.get('pass', 0) or summary['decision_counts'].get('pass', 0)} | Refine {decision_summary.get('refine', 0)} | Abort {decision_summary.get('abort', 0) or summary['decision_counts'].get('abort', 0)} | Zero-trade flags {decision_summary.get('zero_trade', 0)}",
        f"• My diagnoses were: {summarize_list([f'{k}={v}' for k, v in diagnosis.items()], limit=6)}",
        '',
        f"{bold('Best evidence I saw')}",
        f"• {to_first_person(best_line)}",
        '',
        f"{bold('What failed')}",
        f"• {to_first_person(first(failed_items))}",
        f"• {to_first_person(first(failed_items[1:] if isinstance(failed_items, list) else []))}",
        '',
        f"{bold('Why I judged it that way')}",
        f"• {to_first_person(first(why_items))}",
        f"• {to_first_person(first(why_items[1:] if isinstance(why_items, list) else []))}",
        '',
        f"{bold('What I would improve next')}",
        f"• {to_first_person(first(next_items),)}",
        f"• {to_first_person(first(next_items[1:] if isinstance(next_items, list) else []))}",
        '',
        f"{bold('What I am aborting')}",
        f"• {to_first_person(first(abandon_items),)}",
        '',
        f"{bold('Strategy-by-strategy reasons')}",
    ]
    if strategy_reviews:
        for item in strategy_reviews:
            if not isinstance(item, dict):
                continue
            lines.append(f"• {item.get('strategy_spec_id') or '?'} | asset={item.get('asset') or '?'} | timeframe={item.get('timeframe') or '?'} | decision={item.get('decision') or '?'}")
            if item.get('edge_mechanism'):
                lines.append(f"  mechanism: {compact(item.get('edge_mechanism'))}")
            if item.get('hypothesis'):
                lines.append(f"  thesis: {compact(item.get('hypothesis'))}")
            if item.get('decision_rationale'):
                lines.append(f"  why: {to_first_person(item.get('decision_rationale'))}")
            for evidence in (item.get('queue_evidence') or [])[:3]:
                lines.append(f"  evidence: {compact(evidence)}")
    else:
        lines.append('• none')
    return '\n'.join(lines).strip()


def build_fallback():
    text = FALLBACK.read_text(encoding='utf-8') if FALLBACK.exists() else 'No journal available.'
    text = text.strip().splitlines()
    preview = '\n'.join(text[:24]).strip()
    return f"🧠 {bold('Quandalf Journal')}\n\n{preview}"


def trim_message(message, limit=3400):
    text = str(message or '').strip()
    if len(text) <= limit:
        return text
    marker = f"\n\n{bold('Strategy-by-strategy reasons')}"
    if marker in text:
        head, tail = text.split(marker, 1)
        trimmed = head.strip()
        budget = max(0, limit - len(trimmed) - len(marker) - 20)
        return (trimmed + marker + "\n" + tail.strip()[:budget].rstrip() + "…").strip()
    return text[:limit].rstrip() + '…'


def main():
    learning = load_learning()
    reflection = load_json(REFLECTION, {})
    decisions = load_json(DECISIONS, {})
    message = build_from_learning(learning, reflection, decisions) if learning else build_fallback()
    message = message.replace('Why he judged it that way', 'Why I judged it that way').replace('What he would improve next', 'What I would improve next')
    message = trim_message(message)
    subprocess.run(['python', str(TG_NOTIFY), '--bot', 'quandalf', '--channel', 'dm', '--message', message], check=False)
    try:
        print(message.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore'))
    except Exception:
        pass


if __name__ == '__main__':
    main()
