#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / 'agents' / 'quandalf' / 'memory' / 'current_cycle_status.json'
ORDERS = ROOT / 'agents' / 'quandalf' / 'memory' / 'cycle_orders.json'
MANIFEST = ROOT / 'data' / 'state' / 'current_cycle_specs.json'

ASSETS = {'ETH','BTC','SOL','TAO','AVAX','LINK','DOGE','ARB','OP','INJ','BABY'}

def load(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}

def save(path, data):
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')

def infer(spec_paths):
    asset = None
    timeframe = None
    for p in spec_paths or []:
        name = Path(str(p)).name.upper()
        for token in name.split('-'):
            if token in ASSETS:
                asset = token
                break
        if '-1H-' in name: timeframe = '1h'
        elif '-4H-' in name: timeframe = '4h'
        elif '-15M-' in name: timeframe = '15m'
        elif '-30M-' in name: timeframe = '30m'
    return asset, timeframe

status = load(STATUS)
orders = load(ORDERS)
manifest = load(MANIFEST)
spec_paths = manifest.get('spec_paths') or status.get('spec_paths') or []
asset, timeframe = infer(spec_paths)
changed = []
if asset:
    if status.get('target_asset') != asset:
        status['target_asset'] = asset; changed.append('status.target_asset')
    if orders.get('cycle_id') == status.get('cycle_id') and orders.get('target_asset') != asset:
        orders['target_asset'] = asset; changed.append('orders.target_asset')
    ex = orders.get('exploration_targets') or {}
    if ex.get('assets') != [asset]:
        ex['assets'] = [asset]; orders['exploration_targets'] = ex; changed.append('orders.exploration_targets.assets')
    sex = status.get('exploration_targets') or {}
    if sex.get('assets') != [asset]:
        sex['assets'] = [asset]; status['exploration_targets'] = sex; changed.append('status.exploration_targets.assets')
    ext = orders.get('external_intel') or {}
    if ext.get('target_asset') != asset:
        ext['target_asset'] = asset; orders['external_intel'] = ext; changed.append('orders.external_intel.target_asset')
if timeframe:
    if status.get('target_timeframe') != timeframe:
        status['target_timeframe'] = timeframe; changed.append('status.target_timeframe')
    if orders.get('cycle_id') == status.get('cycle_id') and orders.get('target_timeframe') != timeframe:
        orders['target_timeframe'] = timeframe; changed.append('orders.target_timeframe')
    ex = orders.get('exploration_targets') or {}
    if ex.get('timeframes') != [timeframe]:
        ex['timeframes'] = [timeframe]; orders['exploration_targets'] = ex; changed.append('orders.exploration_targets.timeframes')
    sex = status.get('exploration_targets') or {}
    if sex.get('timeframes') != [timeframe]:
        sex['timeframes'] = [timeframe]; status['exploration_targets'] = sex; changed.append('status.exploration_targets.timeframes')
    ext = orders.get('external_intel') or {}
    if ext.get('target_timeframe') != timeframe:
        ext['target_timeframe'] = timeframe; orders['external_intel'] = ext; changed.append('orders.external_intel.target_timeframe')
if spec_paths:
    status['spec_paths'] = spec_paths
    status['specs_produced'] = len(spec_paths)
    status['next_cycle_focus'] = 'pending'
    status['rationale'] = 'pending'

if asset and timeframe and isinstance(orders.get('thesis_hint'), str):
    hint = orders['thesis_hint']
    hint = hint.replace('SOL 4h', f'{asset} {timeframe}')
    hint = hint.replace('BTC 4h', f'{asset} {timeframe}')
    orders['thesis_hint'] = hint
save(STATUS, status)
save(ORDERS, orders)
print(json.dumps({'status':'ok','changed':changed,'asset':asset,'timeframe':timeframe,'cycle_id':status.get('cycle_id')}, indent=2))
