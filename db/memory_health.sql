CREATE TABLE IF NOT EXISTS memory_archive (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ts_iso TEXT NOT NULL,
 agent TEXT NOT NULL,
 source_file TEXT NOT NULL,
 content TEXT NOT NULL,
 archive_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_ma_agent ON memory_archive(agent);

CREATE TABLE IF NOT EXISTS memory_health (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ts_iso TEXT NOT NULL,
 agent TEXT NOT NULL,
 folder_size_kb REAL NOT NULL,
 files_count INTEGER NOT NULL,
 last_compressed TEXT,
 staleness_score REAL,
 status TEXT NOT NULL DEFAULT 'ok'
 CHECK(status IN ('ok','needs_compression','warning','critical'))
);
CREATE INDEX IF NOT EXISTS idx_mh_agent ON memory_health(agent);
CREATE INDEX IF NOT EXISTS idx_mh_status ON memory_health(status);

CREATE TABLE IF NOT EXISTS token_spend (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ts_iso TEXT NOT NULL,
 agent TEXT NOT NULL,
 pipeline TEXT,
 run_id TEXT,
 input_tokens INTEGER,
 output_tokens INTEGER,
 total_tokens INTEGER,
 model TEXT,
 cost_usd REAL
);
CREATE INDEX IF NOT EXISTS idx_ts_agent ON token_spend(agent);
CREATE INDEX IF NOT EXISTS idx_ts_date ON token_spend(ts_iso);