CREATE TABLE IF NOT EXISTS market_confidence (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ts_iso TEXT NOT NULL,
 asset TEXT NOT NULL,
 timeframe TEXT NOT NULL,
 confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
 regime TEXT NOT NULL,
 reasoning TEXT,
 factors TEXT,
 valid_until TEXT,
 UNIQUE(asset, timeframe)
);
CREATE INDEX IF NOT EXISTS idx_mc_asset ON market_confidence(asset);

CREATE TABLE IF NOT EXISTS trade_blacklist (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ts_iso TEXT NOT NULL,
 asset TEXT NOT NULL,
 direction TEXT CHECK(direction IN ('long','short','both')),
 reason TEXT NOT NULL,
 source TEXT NOT NULL DEFAULT 'quandalf',
 expires_iso TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_bl_active ON trade_blacklist(active, asset);

CREATE TABLE IF NOT EXISTS pipeline_runs (
 id TEXT PRIMARY KEY,
 ts_iso_start TEXT NOT NULL,
 ts_iso_end TEXT,
 pipeline_name TEXT NOT NULL,
 mode TEXT,
 run_id TEXT NOT NULL,
 parent_run_id TEXT,
 status TEXT NOT NULL DEFAULT 'running'
 CHECK(status IN ('running','complete','failed','paused','cancelled')),
 steps_total INTEGER,
 steps_completed INTEGER DEFAULT 0,
 input_artifact TEXT,
 output_artifact TEXT,
 token_cost REAL,
 error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_pr_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pr_pipeline ON pipeline_runs(pipeline_name);

CREATE TABLE IF NOT EXISTS known_fixes (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ts_iso_created TEXT NOT NULL,
 error_pattern TEXT NOT NULL,
 fix_action TEXT NOT NULL,
 fix_type TEXT NOT NULL
 CHECK(fix_type IN ('auto','agent_diagnosed','manual')),
 times_applied INTEGER NOT NULL DEFAULT 0,
 last_applied TEXT,
 success_rate REAL,
 active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_kf_pattern ON known_fixes(error_pattern);

CREATE TABLE IF NOT EXISTS agent_feedback (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ts_iso TEXT NOT NULL,
 agent TEXT NOT NULL,
 feedback_type TEXT NOT NULL
 CHECK(feedback_type IN ('complaint','suggestion','bug','observation')),
 message TEXT NOT NULL,
 severity TEXT DEFAULT 'info'
 CHECK(severity IN ('info','warn','error')),
 addressed INTEGER NOT NULL DEFAULT 0,
 addressed_by TEXT,
 resolution TEXT
);
CREATE INDEX IF NOT EXISTS idx_af_agent ON agent_feedback(agent);
CREATE INDEX IF NOT EXISTS idx_af_open ON agent_feedback(addressed);
