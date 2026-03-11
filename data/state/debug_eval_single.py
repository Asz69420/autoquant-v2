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
idx = 200
conds = ["Close > EMA_20", "Close < EMA_20", "Close <= EMA_20 + 0.2 * ATR_14", "High[1] >= bb_upper_20_2[1] or High[2] >= bb_upper_20_2[2]"]
out = {}
for cond in conds:
    out[cond] = wfe.evaluate_condition(cond, idx, indicators, candles)
print(json.dumps(out, indent=2))
