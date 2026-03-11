#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'agents' / 'quandalf' / 'memory' / 'latest_journal.md'
STATE_OUT = ROOT / 'data' / 'state' / 'quandalf_learning_loop.json'
MEMORY_OUT = ROOT / 'agents' / 'quandalf' / 'memory' / 'latest_learning_loop.json'

KEYWORDS = {
    'what_worked': ['worked', 'best', 'edge', 'strongest', 'improved'],
    'what_failed': ['failed', 'weak', 'broke', 'bad', 'problem'],
    'why_it_failed': ['because', 'too sparse', 'event-driven', 'non-selective', 'cost drag', 'zero trades'],
    'iterate_next': ['iterate', 'next', 'improve', 'refine', 'focus'],
    'abandon': ['abandon', 'kill', 'drop'],
    'bench_for_later': ['bench', 'later', 'archive for now'],
    'regime_notes': ['regime', 'transition', 'trend', 'chop', 'compression', 'expansion'],
    'strategy_family_notes': ['family', 'channel', 'snapback', 'supertrend', 'reversion'],
    'indicator_role_notes': ['indicator', 'filter', 'trigger', 'entry', 'exit', 'validation'],
    'management_notes': ['partial', 'runner', 'trailing', 'scale', 'take-profit', 'de-risk']
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def split_sections(text: str):
    sections = []
    current_title = 'intro'
    current_lines = []
    for line in text.splitlines():
        if re.match(r'^#{1,6}\s+', line.strip()):
            if current_lines:
                sections.append((current_title, '\n'.join(current_lines).strip()))
            current_title = re.sub(r'^#{1,6}\s+', '', line.strip()).strip().lower()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, '\n'.join(current_lines).strip()))
    return sections


def extract_cycle_context(text: str):
    m = re.search(r'(cycle\s*\d+)', text, re.I)
    cycle_id = m.group(1) if m else None
    asset = None
    timeframe = None
    for token in ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'DOGE', 'ARB', 'OP', 'INJ', 'TAO', 'BABY', 'VVV', 'AXS']:
        if re.search(rf'\b{token}\b', text):
            asset = token
            break
    for tf in ['15m', '30m', '1h', '4h']:
        if re.search(rf'\b{re.escape(tf)}\b', text, re.I):
            timeframe = tf
            break
    return {'cycle_ref': cycle_id, 'asset': asset, 'timeframe': timeframe}


def collect_dimension(text: str, dimension: str):
    hits = []
    lowered = text.lower()
    for kw in KEYWORDS[dimension]:
        for line in text.splitlines():
            if kw in line.lower() and line.strip():
                hits.append(line.strip())
    deduped = []
    seen = set()
    for h in hits:
        key = h.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(h)
    return deduped[:8]


def build_candidates(dimensions):
    candidates = []
    if dimensions['what_failed'] and dimensions['iterate_next']:
        candidates.append({
            'bucket': 'lessons',
            'title': 'Quandalf lesson from latest journal',
            'summary': (dimensions['what_failed'][0] + ' | next: ' + dimensions['iterate_next'][0])[:280],
            'tags': ['quandalf', 'learning-loop']
        })
    if dimensions['strategy_family_notes']:
        candidates.append({
            'bucket': 'strategy_families',
            'title': 'Quandalf family memory candidate',
            'summary': dimensions['strategy_family_notes'][0][:280],
            'tags': ['quandalf', 'family-memory']
        })
    return candidates[:5]


def main():
    text = SOURCE.read_text(encoding='utf-8') if SOURCE.exists() else ''
    sections = split_sections(text)
    body = '\n\n'.join(section for _, section in sections if section)
    dimensions = {k: collect_dimension(body, k) for k in KEYWORDS}
    payload = {
        'version': 'quandalf-learning-loop-v1',
        'ts_iso': now_iso(),
        'source': str(SOURCE.relative_to(ROOT)),
        'cycle_context': extract_cycle_context(text),
        'thesis': [section for title, section in sections if 'thesis' in title][:2],
        'sections': [{'title': title, 'text': section[:1200]} for title, section in sections[:12]],
        'dimensions': dimensions,
        'promotion_candidates': build_candidates(dimensions)
    }
    STATE_OUT.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATE_OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    MEMORY_OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'ok', 'state': str(STATE_OUT), 'memory': str(MEMORY_OUT)}, indent=2))


if __name__ == '__main__':
    main()
