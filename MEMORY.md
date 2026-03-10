# MEMORY.md — System Cheat Sheet
# Keep under 100 lines. Always loaded. Expensive in tokens.
# Only critical, current, cross-session facts here.

## System State (updated 2026-03-10)
- Framework: complete (10 schemas, 20 tables, 10 configs, 6 agents)
- Phase: pipelines LIVE and running autonomously
- Research pipeline: cron every 5 min (research-cycle.lobster)
- Refinement pipeline: chained at end of research cycle
- All agents: oragorn, quandalf, frodex, logron on separate Telegram bots
- Model: all agents on openai-codex/gpt-5.4, default_model is anthropic/claude-opus-4-6
- DB: SQLite with WAL mode enabled (set 2026-03-10)
- Git: local repo on main branch, no remote yet

## Pipeline Architecture
- pipelines/research-cycle.lobster — main loop (regime-refresh → briefing → orders → quandalf-design → backtest → reflection → postprocess → refinement)
- Regime tagging: refresh_regimes.py runs at pipeline start, tags all 17 candle pairs
- Regime data injected into briefing_packet.json AND cycle_orders.json
- Asset rotation: tracks last 5 cycles in data/state/rotation_history.json, avoids repeating asset for 3 cycles
- Quandalf gets regime-aware thesis hints (e.g. "CHOP → favor mean reversion")

## Key Scripts
- scripts/cycle-postprocess.py — 1638-line god-script, needs splitting (deferred)
- scripts/refresh_regimes.py — batch regime tagger for all candle data
- scripts/build_cycle_orders.py — deterministic cycle order builder with rotation
- scripts/db_utils.py — shared DB connection helper (WAL + busy_timeout)
- scripts/archive_old_specs.py — archives specs >48h old (not promoted)
- scripts/compact_strategy_status.py — trims strategy_status.json bloat

## Scoring
- QScore: pass >= 1.0, promote >= 3.0, hard fail < 15 trades
- xQScore: cross-asset geometric mean (not yet wired — deferred until more strategies)
- 2,129 backtests, 94 families, 14 promoted (0.7% hit rate), avg QS 0.38
- Top strategy: SUPE ETH/4h QS 4.47

## Optimizations Applied (2026-03-10)
- WAL mode on SQLite DB
- Briefing packet trimmed: funding top 5, backtest details 5, no nested metrics (~40% token cut)
- strategy_status.json: 925KB → 17KB
- v1-* legacy files: moved to agents/quandalf/memory/archive/
- Old specs: archiver script ready, 4 archived

## Credentials (refs only — NEVER paste tokens)
- Bot tokens: in ~/.openclaw/openclaw.json under channels.telegram.accounts.*.botToken
- Auth profiles: in ~/.openclaw/agents/oragorn/agent/auth-profiles.json
- Log channel: -5038734156
- Noodle group: -1003841245720

## Known Issues
- cycle-postprocess.py: god-script needs modular split (1638 lines, 50+ functions, 6+ DB connections)
- OpenClaw update blocked by EBUSY (gateway holds file lock, need manual watchdog stop)
- Obfuscation detector blocks inline python -c with complex strings (use .py scripts instead)
- Regime confidence low on some pairs (ETH/1h: 5%, UMA/1h: 5%) — may need longer lookback

## Next Steps
1. Split cycle-postprocess.py into modules (pause cron first)
2. Wire xQScore validation when promoted count > 20
3. Private git remote for workspace-oragorn
4. LobsterBoard visual dashboard
5. TradingView webhook receiver
6. Micro-account tiers ($50 → $500 → full)
7. Smaug build + HyperLiquid API
