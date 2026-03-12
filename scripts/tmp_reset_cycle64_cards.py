import json
from pathlib import Path
p = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\cycle_postprocess_card_state.json")
state = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
cards = state.get('cards') or {}
for key in list(cards.keys()):
    if key.startswith('64:'):
        cards.pop(key, None)
state['cards'] = cards
p.write_text(json.dumps(state, indent=2), encoding='utf-8')
print('reset')
