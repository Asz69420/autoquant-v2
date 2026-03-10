#!/usr/bin/env python3
import json, sqlite3
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'db' / 'autoquant.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
out = {}
out['tables'] = [dict(r) for r in cur.execute("SELECT type, name FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name").fetchall()]
out['queue_columns'] = [dict(r) for r in cur.execute("PRAGMA table_info(research_funnel_queue)").fetchall()]
out['backtest_columns'] = [dict(r) for r in cur.execute("PRAGMA table_info(backtest_results)").fetchall()]
out['recent_queue_done'] = [dict(r) for r in cur.execute("SELECT id, cycle_id, status, stage, strategy_spec_id, variant_id, notes, completed_at FROM research_funnel_queue WHERE status='done' ORDER BY id DESC LIMIT 12").fetchall()]
# inspect likely log table structure and rows
for cand in ['event_log','logs','events','pipeline_events']:
    row = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (cand,)).fetchone()
    if row:
        out['log_table'] = cand
        out['log_columns'] = [dict(r) for r in cur.execute(f"PRAGMA table_info({cand})").fetchall()]
        out['recent_log_rows'] = [dict(r) for r in cur.execute(f"SELECT * FROM {cand} ORDER BY 1 DESC LIMIT 12").fetchall()]
        break
print(json.dumps(out, indent=2))
