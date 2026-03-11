import ast, json, re, sys
from pathlib import Path
ROOT = Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn')
sys.path.insert(0, str(ROOT / 'scripts'))
import walk_forward_engine as wfe

spec = str(ROOT / 'artifacts' / 'strategy_specs' / 'DEBUG-SIMPLE-EMA-CROSS.strategy_spec.json')
strategy = wfe.parse_strategy_spec(spec, 'default')
candles = wfe.load_candles('ETH', '4h')
indicators = wfe.compute_indicators(candles, strategy.get('parameters', {}), strategy.get('declared_indicators'))
idx = 200

def resolve_token(token: str):
    token = token.strip()
    try:
        return float(token)
    except ValueError:
        pass
    offset = 0
    match = re.match(r"^(.*)\[(\d+)\]$", token)
    if match:
        token = match.group(1).strip()
        offset = int(match.group(2))
    pos = idx - offset
    t = token.lower().replace('-', '_')
    alias = {
        'price': 'close',
        'upper_bollinger_20_2': 'bb_upper_20_2',
        'lower_bollinger_20_2': 'bb_lower_20_2',
        'middle_bollinger_20_2': 'bb_middle_20_2',
    }
    t = alias.get(t, t)
    if t in {'close','high','low','open'}:
        return candles[pos][t]
    if t in indicators and pos < len(indicators[t]) and indicators[t][pos] is not None:
        return indicators[t][pos]
    return None

expr = 'Close < EMA_20'
map_ = {}
def repl(match):
    token = match.group(0)
    lower = token.lower()
    if lower in {'and','or','not','true','false'}:
        return lower
    value = resolve_token(token)
    if value is None:
        return 'None'
    key = f'v{len(map_)}'
    map_[key] = value
    return key
prepared = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?\b", repl, expr)
print(json.dumps({'prepared': prepared, 'map': map_}, indent=2, default=str))
print(ast.dump(ast.parse(prepared, mode='eval'), indent=2))
