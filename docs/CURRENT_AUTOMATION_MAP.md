# Current Automation Map

## Current repo
All canonical automation should point to:
- `C:\Users\Clamps\.openclaw\workspace-oragorn`

## Active / Ready
- `AutoQuant-autopilot`
  - chained research + maintenance
- `AutoQuant-tv-catalog`
  - TradingView indicator catalog / library builder
- `AutoQuant-youtube-watch`
  - canonical YouTube watcher (skill-based path, current repo)
- `AutoQuant-daily-intel`
  - daily intel brief at 07:00 local
- `AutoQuant-quandalf-journal`
  - daily Quandalf journal at 20:00 local

## Disabled legacy / overlap
- `AutoQuant-build-queue-worker`
- `AutoQuant-bundle-run-log-user`
- `AutoQuant-Claude-Bridge`
- `AutoQuant-Claude-DeepIterator`
- `AutoQuant-keeper-30m`
- `AutoQuant-keeper-startup`
- `AutoQuant-Oragorn-Subagent-Monitor`
- `AutoQuant-tg_reporter`
- `AutoQuant-tg_reporter-watchdog`

## Canonical ownership
- research/refinement/maintenance: autopilot + lobster pipelines
- TradingView indicators: `scripts/tv_catalog_worker.py`
- YouTube learning: `skills/autoquant-youtube-watcher/watcher.py`
- daily intel: `scripts/daily-intel-brief.py`
- Quandalf journal: `scripts/send_quandalf_journal_dm.py`

## Rule
Anything still pointing at old `workspace` must be repointed or disabled. No duplicate automation domains.
