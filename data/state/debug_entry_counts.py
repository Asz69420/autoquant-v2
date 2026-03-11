import json
import sys
from pathlib import Path
ROOT = Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn')
sys.path.insert(0, str(ROOT / 'scripts'))
import walk_forward_engine as wfe

spec = str(ROOT / 'artifacts' / 'strategy_specs' / 'DEBUG-SIMPLE-EMA-CROSS.strategy_spec.json')
strategy = wfe.parse_strategy_spec(spec, 'default')
candles = wfe.load_candles('ETH', '4h')
indicators = wfe.compute_indicators(candles, strategy.get('parameters', {}), strategy.get('declared_indicators'))
entry_rules = wfe.normalize_directional_rules(strategy.get('entry_rules', []))

warmup = min(200, max(1, len(candles)//4))
counts = {'long': 0, 'short': 0}
for i in range(warmup, len(candles)):
    for direction in ('long', 'short'):
        ok = True
        for cond in entry_rules.get(direction, []):
            if not wfe.evaluate_condition(cond, i, indicators, candles):
                ok = False
                break
        if ok:
            counts[direction] += 1
print(json.dumps({
    'strategy_name': strategy.get('strategy_name'),
    'warmup': warmup,
    'entry_rules': entry_rules,
    'counts': counts,
    'sample_close': candles[warmup]['close'],
    'sample_ema20': indicators['ema_20'][warmup]
}, indent=2, default=str))
