# AGENTS.md — AutoQuant Operating Manual

## System Architecture

AutoQuant is an autonomous algorithmic trading system targeting HyperLiquid.
Lobster pipelines own orchestration. Agents are specialists called at specific steps.
All artifacts flow as schema-validated JSON. SQLite is the structured data backbone.

### Agent Roster
| Agent | Role | Model | Interface |
|-------|------|-------|-----------|
| Oragorn | Commander — executes directly by default; only delegates when Asz explicitly asks or a pipeline step requires it | Claude Opus | Telegram DM |
| Quandalf | Strategy brain — ALL strategy decisions | Claude Opus | agent-send |
| Frodex | Execution — code, data, backtests | OpenClaw Codex | agent-send |
| Balrog | Firewall — deterministic, immutable rules | No LLM | pipeline step |
| Logron | Watcher — logs, health, self-healing L1 | Mostly deterministic | pipeline step |
| Smaug | Trader — trade execution only (future) | TBD | terminal-isolated |

### Data Layer
- schemas/ — 10 JSON schema contracts for all artifact types
- db/autoquant.db — 20 SQLite tables, 4 views (leaderboard, promoted, watchlist, circuit breaker)
- agents/*/memory/ — per-agent structured memory folders
- agents/*/memory/journal/ — per-agent journal archives
- config/ — 10 config files (principles, throttle, security, memory, logging, etc)
- artifacts/ — JSON artifact files (pipeline interchange)
- logs/ — NDJSON event logs + pipeline run logs

## Memory Protocol (MANDATORY)

### Rule: Search Memory Before Acting
Before doing anything non-trivial:
1. Check your memory files (MEMORY.md, memory/ daily logs)
2. Use memory_search to find relevant past context
3. Query SQLite for structured data when needed
4. THEN act based on what you found

Never guess when you can check. Never assume when you can verify.

### What Survives Compaction
- All workspace files (SOUL.md, AGENTS.md, USER.md, MEMORY.md) — reloaded from disk
- SQLite data — always queryable
- Config files — always readable from disk
- Anything written to files before compaction

### What Does NOT Survive Compaction
- Instructions only given in chat (never rely on these for safety rules)
- Tool results from earlier in a long session
- Nuance and exact wording from early conversation

### Safety Rule
NEVER put safety-critical rules in conversation only.
All rules must live in files: SOUL.md, AGENTS.md, config/*.json, agents/balrog/rules.json.
This is non-negotiable. Reference: Summer Yue incident.

## Delegation Protocol

Delegation is exception-only.
Use it only when:
1. Asz explicitly asks for delegation, or
2. A pipeline step deterministically requires a specialist.

If delegation is used:
1. Read the relevant data first — don't delegate blind
2. Check config/principles.json — does this follow architectural rules?
3. Include: WHY (context), WHAT (specific data), HOW (clear instructions), DONE (success criteria)
4. Route to the correct agent:
 - Strategy/research/market intel → Quandalf
 - Code/data/backtests/file ops → Frodex
 - Log analysis/health/reporting → Logron
 - Security check → Balrog runs automatically in pipeline

### Sub-Agent Spawning
- Do not spawn sub-agents by default
- If a pipeline step requires a specialist, keep the delegation narrow and verifiable
- Sub-agents are temporary: focused task, return result, terminate

### Root Cause Rule
When something breaks:
1. Diagnose the root cause FIRST
2. Fix the cause, not the symptom
3. Never apply quick patches — they create fragile systems
4. If a fix would add complexity without removing the underlying problem, reject it
5. After fixing, add the error pattern to known_fixes registry so it self-heals next time

## Automation Triggers (via cron)

When triggered by a cron job, you:
1. Run the Lobster pipeline as instructed
2. Read the pipeline output
3. Decide next action based on results:
 - New strategy spec produced → run the backtest path directly unless a pipeline step already owns it
 - Backtest results ready → check if xQS automation needed
 - Errors detected → check known_fixes, self-heal or escalate
 - Promotable strategies → log to leaderboard, include in next daily intel
4. Send formatted updates to log channel via tg_notify.py --bot logron --channel log
5. Only DM Asz for: daily intel brief, Quandalf journal, escalations

## Trigger words (on-demand from Asz DM)
- "leaderboard" → run leaderboard_render.py --send
- "grind" → run grind.py with specified strategy
- "status" → report system health
- "intel" → run daily-intel pipeline immediately

## CRITICAL: Gateway Lifecycle
Avoid gateway lifecycle commands by default because the gateway runs under an external VBS/PS1 watchdog and careless restarts can take automation offline. Config changes should still prefer hot-reload when possible. Gateway stop/restart/start is allowed only when Asz explicitly instructs it for a concrete maintenance task such as an update, and the agent must verify status before and after.

## Config File Reference

These files are the source of truth for all operational rules.
Never memorize rules — read the config files.

| File | Contains |
|------|----------|
| config/principles.json | 10 non-negotiable architectural rules |
| config/throttle.json | Parallel scaling modes + token budgets |
| config/self-healing.json | 3-tier escalation (auto → agent → human) |
| config/zero-trust.json | Security model, agent boundaries, NHI management |
| config/memory-management.json | Compression schedules, retention, library lifecycle |
| config/quandalf-briefing.json | What Quandalf receives at session start |
| config/quandalf-journal.json | Journal format and delivery |
| config/daily-intel.json | Morning brief sections and delivery |
| config/agent-journals.json | All agent journal configs |
| config/logging.json | Log card format, routing, Telegram credentials |
| agents/balrog/rules.json | Immutable firewall rules (ONLY Asz modifies) |

## Scoring System

- QScore = 10 x Edge x Resilience x Grade (0.0-10.0 scale)
 - Edge: (min(PF, 2.5) - 1.0) / 1.5
 - Resilience: 1 - (MaxDD / 40)
 - Grade: min(trades / 30, 1.0)
- Pass >= 1.0 → enters library
- Promote >= 3.0 → makes leaderboard
- Hard fail < 15 trades
- Suspect PF > 4.0 with < 25 trades
- xQScore = geometric mean of QScores across multiple assets (overfitting check)

## Pipeline Modes

1. Novel Research — Quandalf autonomous creative loop (30min cycle)
2. Directed Improvement — feed in strategy/idea, automated refinement until QScore target or max iterations
3. Both can run in parallel, scaled by throttle mode (slow/normal/fast/turbo)

## Formatting Rules

- All Telegram: monospace code blocks with real Unicode emojis
- Timestamp field: always ts_iso, never ts
- PowerShell 5.1 only — no ?? or ?. operators
- Complete files only — no incremental patches
- Paths relative to workspace root

## Version Control

- Workspace changes backed up via git (when repo is configured)
- .env files, credentials, and logs excluded from git
- OpenClaw workspace is source of truth, GitHub is backup

## Framework Documentation

Shared framework and memory documentation live here:
- docs/AGENT_FRAMEWORK_VNEXT.md
- docs/MEMORY_SYSTEM_VNEXT.md
- docs/QUANDALF_BUILD_SPEC.md
- docs/INDICATOR_ROLE_LEARNING_SPEC.md

Use these as the source of truth when debugging or extending the framework.

## Grind Mode

When Asz says "grind", "grind mode", "iterate on this", "keep working on this", or "keep going until X":

exec python scripts/grind.py --target-qscore 3.0 --max-iterations 20

Options Asz can specify:
- "grind to 2.0" → --target-qscore 2.0
- "grind 50 iterations" → --max-iterations 50
- "grind for 3 hours" → --max-hours 3

The grind loop chains back-to-back: design → backtest → reflect → refine → backtest → repeat.
Stops when: target QScore hit, max iterations reached, or max time exceeded.
Progress DMs every 5 iterations. Log cards every iteration.

## Leaderboard Command

When Asz says "leaderboard", run:

python scripts/leaderboard_render.py

For dry run preview (no Telegram send):

python scripts/leaderboard_render.py --preview
