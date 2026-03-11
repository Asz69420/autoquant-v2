#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEARNING = ROOT / 'data' / 'state' / 'quandalf_learning_loop.json'
FALLBACK = ROOT / 'agents' / 'quandalf' / 'memory' / 'latest_journal.md'
TG_NOTIFY = ROOT / 'scripts' / 'tg_notify.py'

BOLD = {
    'A':'𝐀','B':'𝐁','C':'𝐂','D':'𝐃','E':'𝐄','F':'𝐅','G':'𝐆','H':'𝐇','I':'𝐈','J':'𝐉','K':'𝐊','L':'𝐋','M':'𝐌','N':'𝐍','O':'𝐎','P':'𝐏','Q':'𝐐','R':'𝐑','S':'𝐒','T':'𝐓','U':'𝐔','V':'𝐕','W':'𝐖','X':'𝐗','Y':'𝐘','Z':'𝐙',
    'a':'𝐚','b':'𝐛','c':'𝐜','d':'𝐝','e':'𝐞','f':'𝐟','g':'𝐠','h':'𝐡','i':'𝐢','j':'𝐣','k':'𝐤','l':'𝐥','m':'𝐦','n':'𝐧','o':'𝐨','p':'𝐩','q':'𝐪','r':'𝐫','s':'𝐬','t':'𝐭','u':'𝐮','v':'𝐯','w':'𝐰','x':'𝐱','y':'𝐲','z':'𝐳',
    '0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗'
}


def bold(text: str) -> str:
    return ''.join(BOLD.get(ch, ch) for ch in text)


def load_learning():
    if LEARNING.exists():
        return json.loads(LEARNING.read_text(encoding='utf-8'))
    return None


def first(items, default='—'):
    if not items:
        return default
    if isinstance(items, list):
        return str(items[0]).strip() or default
    return str(items).strip() or default


def build_from_learning(data):
    ctx = data.get('cycle_context') or {}
    dims = data.get('dimensions') or {}
    thesis = first(data.get('thesis'))
    lines = [
        f"🧠 {bold('Quandalf Daily Journal')}",
        f"Cycle: {ctx.get('cycle_ref') or '—'} | Asset: {ctx.get('asset') or '—'} | TF: {ctx.get('timeframe') or '—'}",
        '',
        f"{bold('Thesis')}\n{thesis}",
        '',
        f"{bold('What worked')}\n• {first(dims.get('what_worked'))}",
        '',
        f"{bold('What failed')}\n• {first(dims.get('what_failed'))}",
        '',
        f"{bold('Why')}\n• {first(dims.get('why_it_failed'))}",
        '',
        f"{bold('Next iterate')}\n• {first(dims.get('iterate_next'))}",
        '',
        f"{bold('Bench / abandon')}\n• Bench: {first(dims.get('bench_for_later'))}\n• Abandon: {first(dims.get('abandon'))}",
        '',
        f"{bold('Regime / family notes')}\n• Regime: {first(dims.get('regime_notes'))}\n• Family: {first(dims.get('strategy_family_notes'))}",
        '',
        f"{bold('Management / indicator notes')}\n• Management: {first(dims.get('management_notes'))}\n• Indicator roles: {first(dims.get('indicator_role_notes'))}",
    ]
    return '\n'.join(lines).strip()


def build_fallback():
    text = FALLBACK.read_text(encoding='utf-8') if FALLBACK.exists() else 'No journal available.'
    text = text.strip().splitlines()
    preview = '\n'.join(text[:20]).strip()
    return f"🧠 {bold('Quandalf Daily Journal')}\n\n{preview}"


def main():
    message = build_from_learning(load_learning()) if load_learning() else build_fallback()
    subprocess.run(['python', str(TG_NOTIFY), '--bot', 'oragorn', '--channel', 'asz', '--message', message], check=False)
    print(message)


if __name__ == '__main__':
    main()
