# MEMORY.md — System Cheat Sheet
# Keep under 100 lines. Always loaded. Expensive in tokens.
# Only critical, current, cross-session facts here.

## System State
- Framework: complete (10 schemas, 20 tables, 10 configs, 6 agents)
- Phase: identity docs deployed, pipelines not yet wired
- Lobster: installed, Windows ESM issue pending
- Telegram: not yet bound to Oragorn (still on Frodex)
- Git repo: workspace-oragorn needs private repo setup

## Scoring
- QScore: pass >= 1.0, promote >= 3.0, hard fail < 15 trades
- xQScore: cross-asset geometric mean
- Best strategy (PoC): Vortex v2c PF 1.892, ETH 4h, transitional PF 2.986

## Key Principles (read config/principles.json for full list)
- Pipeline owns orchestration
- No quick-fix patches — root cause only
- Evidence not claims
- Quandalf owns ALL strategy decisions
- Sub-agent spawning is pipeline-driven
- If it's not in a file, it doesn't exist
- Safety rules in files only, never chat-only

## Credentials (refs only)
- Gateway: TELEGRAM_BOT_TOKEN in workspace/.env
- Quandalf: CLAUDE_BRIDGE_BOT_TOKEN in scripts/claude-bridge/.env
- Logron: TELEGRAM_LOG_BOT_TOKEN in workspace/.env
- Log channel: -5038734156
- Noodle group: -1003841245720

## Next Steps
1. Git repo for workspace-oragorn (private, auto-sync)
2. Fix Lobster Windows ESM issue
3. openclaw agents add quandalf (full agent)
4. First Lobster pipeline YAML (research cycle)
5. Cron jobs for autonomous cycles
6. Telegram binding swap to Oragorn
7. LobsterBoard visual dashboard
8. TradingView webhook receiver
9. Micro-account tiers ($50 → $500 → full)
10. Smaug build + HyperLiquid API
