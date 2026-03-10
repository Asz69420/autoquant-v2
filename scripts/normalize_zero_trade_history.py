#!/usr/bin/env python3
import json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'db' / 'autoquant.db'
BOARD = ROOT / 'data' / 'state' / 'agent_messages.json'
OUT = ROOT / 'data' / 'state' / 'zero_trade_cleanup_state.json'

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
rows = cur.execute(
    """
    SELECT id, notes FROM research_funnel_queue
    WHERE status='done'
      AND lower(COALESCE(notes,'')) LIKE '%integrity_skip:zero_%'
      AND lower(COALESCE(notes,'')) LIKE '%\"status\": \"terminal_fail\"%'
    ORDER BY completed_at DESC
    """
).fetchall()
updated = 0
sample_ids = []
for row in rows:
    notes = str(row['notes'] or '')
    try:
        payload = json.loads(notes)
    except Exception:
        continue
    if payload.get('status') == 'terminal_fail' and 'integrity_skip:zero_' in str(payload.get('error','')).lower():
        payload['status'] = 'integrity_skip'
        payload['classification'] = 'zero_trade_history_normalized'
        payload['normalized_at'] = datetime.now(timezone.utc).isoformat()
        cur.execute("UPDATE research_funnel_queue SET notes=? WHERE id=?", (json.dumps(payload), row['id']))
        updated += 1
        if len(sample_ids) < 20:
            sample_ids.append(row['id'])
conn.commit()

# prune repeated gateway board noise, keep latest unique message per 6h-ish pattern
board_removed = 0
if BOARD.exists():
    try:
        board = json.loads(BOARD.read_text(encoding='utf-8'))
        msgs = board.get('messages', [])
        kept = []
        seen = set()
        for msg in reversed(msgs):
            key = (msg.get('from'), msg.get('to'), msg.get('type'), msg.get('message'))
            if key in seen and 'gateway errors' in str(msg.get('message','')).lower():
                board_removed += 1
                continue
            seen.add(key)
            kept.append(msg)
        kept.reverse()
        board['messages'] = kept[-100:]
        BOARD.write_text(json.dumps(board, indent=2), encoding='utf-8')
    except Exception:
        pass

state = {
    'version': 'zero-trade-cleanup-v1',
    'ts_iso': datetime.now(timezone.utc).isoformat(),
    'queue_rows_normalized': updated,
    'sample_queue_ids': sample_ids,
    'board_messages_removed': board_removed,
    'status': 'ok'
}
OUT.write_text(json.dumps(state, indent=2), encoding='utf-8')
print(json.dumps(state, indent=2))
