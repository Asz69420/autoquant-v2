PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS research_cards (id TEXT PRIMARY KEY, ts_iso TEXT NOT NULL, source_type TEXT NOT NULL, source_ref TEXT NOT NULL, source_title TEXT, concept TEXT NOT NULL, indicators TEXT NOT NULL, timeframes TEXT NOT NULL, asset_classes TEXT NOT NULL, regime_relevance TEXT, summary TEXT NOT NULL, tags TEXT, status TEXT NOT NULL DEFAULT 'new', thesis_id TEXT);

CREATE TABLE IF NOT EXISTS theses (id TEXT PRIMARY KEY, ts_iso TEXT NOT NULL, research_card_ids TEXT NOT NULL, hypothesis TEXT NOT NULL, edge_description TEXT NOT NULL, entry_logic TEXT NOT NULL, exit_logic TEXT NOT NULL, risk_parameters TEXT NOT NULL, target_regime TEXT NOT NULL, target_assets TEXT, target_timeframes TEXT, confidence TEXT, reasoning TEXT, status TEXT NOT NULL DEFAULT 'draft', strategy_spec_id TEXT);

CREATE TABLE IF NOT EXISTS strategy_specs (id TEXT PRIMARY KEY, ts_iso TEXT NOT NULL, thesis_id TEXT NOT NULL, name TEXT NOT NULL, version TEXT NOT NULL, asset TEXT NOT NULL, timeframe TEXT NOT NULL, indicators TEXT NOT NULL, entry_rules TEXT NOT NULL, exit_rules TEXT NOT NULL, position_sizing TEXT, regime_filter TEXT, variants TEXT NOT NULL, complexity_score REAL, status TEXT NOT NULL DEFAULT 'draft');

CREATE TABLE IF NOT EXISTS backtest_results (id TEXT PRIMARY KEY, ts_iso TEXT NOT NULL, strategy_spec_id TEXT NOT NULL, variant_id TEXT NOT NULL, asset TEXT NOT NULL, timeframe TEXT NOT NULL, period_start TEXT NOT NULL, period_end TEXT NOT NULL, candle_count INTEGER, profit_factor REAL NOT NULL, total_return_pct REAL NOT NULL, max_drawdown_pct REAL NOT NULL, total_trades INTEGER NOT NULL, win_rate_pct REAL NOT NULL, avg_trade_pct REAL, sharpe_ratio REAL, sortino_ratio REAL, metrics TEXT NOT NULL, regime_metrics TEXT, score_total REAL NOT NULL, score_decision TEXT NOT NULL, score_edge REAL NOT NULL, score_resilience REAL NOT NULL, score_grade REAL NOT NULL, score_flags TEXT, score_details TEXT NOT NULL, xqscore_total REAL, xqscore_details TEXT, walk_forward TEXT, equity_curve TEXT, status TEXT NOT NULL DEFAULT 'complete', strategy_family TEXT, parent_id TEXT, mutation_type TEXT, stage TEXT NOT NULL DEFAULT 'full', validation_target TEXT, family_generation INTEGER NOT NULL DEFAULT 1, killed INTEGER NOT NULL DEFAULT 0, regime_scores TEXT, regime_concentration REAL, primary_regime TEXT, portability_score REAL DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_bt_strategy ON backtest_results(strategy_spec_id);
CREATE INDEX IF NOT EXISTS idx_bt_score ON backtest_results(score_total DESC);
CREATE INDEX IF NOT EXISTS idx_bt_decision ON backtest_results(score_decision);
CREATE INDEX IF NOT EXISTS idx_bt_family_stage_killed ON backtest_results(strategy_family, stage, killed);

CREATE TABLE IF NOT EXISTS research_funnel_queue (
  id TEXT PRIMARY KEY,
  cycle_id INTEGER,
  spec_path TEXT NOT NULL,
  strategy_spec_id TEXT NOT NULL,
  variant_id TEXT NOT NULL,
  asset TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  stage TEXT NOT NULL,
  bucket TEXT NOT NULL,
  priority INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  queued_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  parent_result_id TEXT,
  mutation_type TEXT,
  family_generation INTEGER NOT NULL DEFAULT 1,
  strategy_family TEXT,
  validation_target TEXT NOT NULL DEFAULT '',
  source_queue_id TEXT,
  notes TEXT,
  result_id TEXT,
  novelty_score REAL DEFAULT 0,
  UNIQUE(spec_path, variant_id, asset, timeframe, stage, validation_target)
);
CREATE INDEX IF NOT EXISTS idx_funnel_queue_status ON research_funnel_queue(status, stage, bucket, priority, queued_at);
CREATE INDEX IF NOT EXISTS idx_funnel_queue_cycle ON research_funnel_queue(cycle_id, status, bucket, priority);

CREATE TABLE IF NOT EXISTS lessons (id TEXT PRIMARY KEY, ts_iso TEXT NOT NULL, backtest_result_id TEXT NOT NULL, strategy_spec_id TEXT NOT NULL, lesson_type TEXT NOT NULL, observation TEXT NOT NULL, implication TEXT NOT NULL, actionable INTEGER NOT NULL DEFAULT 0, suggested_action TEXT, confidence TEXT, applied_in TEXT);

CREATE TABLE IF NOT EXISTS refinements (id TEXT PRIMARY KEY, ts_iso TEXT NOT NULL, source_strategy_spec_id TEXT NOT NULL, lesson_ids TEXT NOT NULL, changes TEXT NOT NULL, new_strategy_spec_id TEXT NOT NULL, rationale TEXT NOT NULL, iteration INTEGER NOT NULL DEFAULT 1, max_iterations INTEGER NOT NULL DEFAULT 5);

CREATE TABLE IF NOT EXISTS promotions (id TEXT PRIMARY KEY, ts_iso TEXT NOT NULL, strategy_spec_id TEXT NOT NULL, backtest_result_id TEXT NOT NULL, gate_type TEXT NOT NULL, criteria TEXT NOT NULL, evaluation TEXT, passed INTEGER NOT NULL, failed_criteria TEXT, decision TEXT NOT NULL, notes TEXT);

CREATE TABLE IF NOT EXISTS trade_signals (id TEXT PRIMARY KEY, ts_iso TEXT NOT NULL, strategy_spec_id TEXT NOT NULL, asset TEXT NOT NULL, direction TEXT NOT NULL, entry_price REAL NOT NULL, stop_loss REAL NOT NULL, take_profit REAL NOT NULL, trailing_stop TEXT, position_size TEXT NOT NULL, risk_reward_ratio REAL, regime_at_signal TEXT, confidence TEXT, balrog_status TEXT NOT NULL DEFAULT 'pending', balrog_checks TEXT, approval_status TEXT NOT NULL DEFAULT 'pending', execution_status TEXT NOT NULL DEFAULT 'pending', exchange_order_id TEXT);

CREATE TABLE IF NOT EXISTS trades (id TEXT PRIMARY KEY, ts_iso_open TEXT NOT NULL, ts_iso_close TEXT, signal_id TEXT NOT NULL, strategy_spec_id TEXT NOT NULL, asset TEXT NOT NULL, direction TEXT NOT NULL, entry_price REAL NOT NULL, exit_price REAL, units REAL NOT NULL, notional_usd REAL NOT NULL, pnl_usd REAL, pnl_pct REAL, fees_usd REAL, regime_at_open TEXT, regime_at_close TEXT, exit_reason TEXT, status TEXT NOT NULL DEFAULT 'open', exchange_order_ids TEXT);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_spec_id);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);

CREATE TABLE IF NOT EXISTS outcome_notes (id TEXT PRIMARY KEY, ts_iso TEXT NOT NULL, strategy_spec_id TEXT NOT NULL, backtest_result_id TEXT, trade_ids TEXT, context TEXT NOT NULL, expected_outcome TEXT NOT NULL, actual_outcome TEXT NOT NULL, analysis TEXT NOT NULL, market_conditions TEXT, feeds_into TEXT);

CREATE TABLE IF NOT EXISTS event_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts_iso TEXT NOT NULL, event_type TEXT NOT NULL, agent TEXT NOT NULL, pipeline TEXT, step TEXT, artifact_id TEXT, severity TEXT NOT NULL DEFAULT 'info', message TEXT NOT NULL, metadata TEXT);
CREATE INDEX IF NOT EXISTS idx_events_ts ON event_log(ts_iso);
CREATE INDEX IF NOT EXISTS idx_events_type ON event_log(event_type);
CREATE INDEX IF NOT EXISTS idx_events_agent ON event_log(agent);

CREATE TABLE IF NOT EXISTS mechanism_priors (mechanism TEXT PRIMARY KEY, success_rate REAL, total_tested INTEGER, avg_best_qs REAL, priority_modifier REAL DEFAULT 1.0, updated_at TEXT);

-- QScore Leaderboard (all completed backtests)
CREATE VIEW IF NOT EXISTS leaderboard AS
SELECT
 ss.name AS strategy_name, ss.version, ss.asset, ss.timeframe,
 bt.variant_id,
 bt.score_total AS qscore, bt.score_decision AS decision,
 bt.xqscore_total AS xqscore,
 bt.profit_factor, bt.total_return_pct, bt.max_drawdown_pct,
 bt.total_trades, bt.win_rate_pct,
 bt.score_edge AS edge, bt.score_resilience AS resilience, bt.score_grade AS grade,
 bt.status AS backtest_status, ss.status AS strategy_status, bt.ts_iso AS backtest_date
FROM backtest_results bt
JOIN strategy_specs ss ON bt.strategy_spec_id = ss.id
WHERE bt.status = 'complete'
ORDER BY bt.score_total DESC;

-- Promoted only (QScore >= 3.0)
CREATE VIEW IF NOT EXISTS leaderboard_promoted AS
SELECT * FROM leaderboard WHERE decision = 'promote' ORDER BY qscore DESC;

-- Pass watchlist (1.0 <= QScore < 3.0)
CREATE VIEW IF NOT EXISTS leaderboard_watchlist AS
SELECT * FROM leaderboard WHERE decision = 'pass' ORDER BY qscore DESC;

-- Circuit breaker monitoring
CREATE VIEW IF NOT EXISTS circuit_breaker_watch AS
SELECT
 ss.name AS strategy_name, ss.id AS strategy_spec_id,
 bt.max_drawdown_pct, bt.profit_factor, bt.score_total AS qscore,
 CASE
 WHEN bt.max_drawdown_pct >= 25.0 THEN 'HALT'
 WHEN bt.profit_factor < 1.2 THEN 'WATCH'
 ELSE 'OK'
 END AS circuit_status
FROM backtest_results bt
JOIN strategy_specs ss ON bt.strategy_spec_id = ss.id
WHERE bt.status = 'complete' AND ss.status IN ('promoted', 'tested')
ORDER BY bt.ts_iso DESC;
