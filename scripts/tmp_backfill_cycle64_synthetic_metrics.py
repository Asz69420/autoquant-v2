import json, sqlite3
from pathlib import Path
ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
DB = ROOT / 'db' / 'autoquant.db'
cycle_id = 64
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, strategy_spec_id, stage, status, notes FROM research_funnel_queue WHERE cycle_id=? ORDER BY id", (cycle_id,)).fetchall()
updated = 0
for row in rows:
    notes = {}
    try:
        notes = json.loads(row['notes']) if row['notes'] else {}
    except Exception:
        notes = {'raw': row['notes']}
    if notes.get('synthetic_result'):
        continue
    err = str(notes.get('error') or '')
    if 'zero_trades_both_samples' not in err and 'zero_oos_trades' not in err:
        continue
    stage = row['stage'] or 'screen'
    synthetic = {
        'stage': stage,
        'insample': {'total_trades': 0, 'profit_factor': 0.0, 'max_drawdown_pct': 0.0, 'total_return_pct': 0.0, 'win_rate_pct': 0.0, 'sharpe_ratio': 0.0, 'qscore': 0.0},
        'outofsample': {'total_trades': 0, 'profit_factor': 0.0, 'max_drawdown_pct': 0.0, 'total_return_pct': 0.0, 'win_rate_pct': 0.0, 'sharpe_ratio': 0.0, 'qscore': 0.0},
        'degradation_pct': 100.0,
        'walk_forward_config': {'stage': stage, 'synthetic_backfill': True},
        'fold_results': [],
        'regime_scores': {},
        'regime_concentration': 0.0,
        'primary_regime': 'UNKNOWN'
    }
    notes['synthetic_result'] = synthetic
    conn.execute("UPDATE research_funnel_queue SET notes=? WHERE id=?", (json.dumps(notes), row['id']))
    updated += 1
conn.commit()
conn.close()
print(json.dumps({'status': 'ok', 'cycle_id': cycle_id, 'updated': updated}, indent=2))
