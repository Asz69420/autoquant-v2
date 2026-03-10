#!/usr/bin/env python3
import json, sqlite3
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'db' / 'autoquant.db'
OUT = ROOT / 'data' / 'state' / 'db_schema_snapshot.json'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
payload = {"version": "db-schema-snapshot-v1", "tables": {}, "views": []}
for row in cur.execute("SELECT type, name FROM sqlite_master WHERE type IN ('table','view') ORDER BY type,name").fetchall():
    kind = row['type']
    name = row['name']
    if kind == 'view':
        payload['views'].append(name)
    else:
        payload['tables'][name] = [dict(r) for r in cur.execute(f"PRAGMA table_info({name})").fetchall()]
OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
print(json.dumps({"status": "ok", "table_count": len(payload['tables']), "view_count": len(payload['views']), "out": str(OUT)}, indent=2))
