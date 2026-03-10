# Current Automation Map

## Current repo
All canonical automation should point to:
- `C:\Users\Clamps\.openclaw\workspace-oragorn`

## Active / Ready
- `AutoQuant-V2-ContinuousLoop`
  - continuous Lobster owner
  - runs `scripts/automation/run_continuous_autopilot.ps1`
  - chains research cycle then daily maintenance without overlap
- `AutoQuant-V2-TVCatalog`
  - TradingView indicator catalog / library builder
- `AutoQuant-V2-YouTubeWatch`
  - canonical YouTube watcher (skill-based path, current repo)
- `AutoQuant-V2-DailyIntel`
  - daily intel brief at 05:30 local
- `AutoQuant-V2-QuandalfJournal`
  - daily Quandalf journal at 17:30 local

## Disabled legacy / overlap
- `AutoQuant-autopilot`
- `AutoQuant-tv-catalog`
- `AutoQuant-youtube-watch`
- `AutoQuant-daily-intel`
- `AutoQuant-quandalf-journal`
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
- research/refinement/maintenance: `AutoQuant-V2-ContinuousLoop` + Lobster pipelines
- TradingView indicators: `AutoQuant-V2-TVCatalog` + `scripts/tv_catalog_worker.py`
- YouTube learning: `AutoQuant-V2-YouTubeWatch` + `skills/autoquant-youtube-watcher/watcher.py`
- daily intel: `AutoQuant-V2-DailyIntel` + `scripts/daily-intel-brief.py`
- Quandalf journal: `AutoQuant-V2-QuandalfJournal` + `scripts/send_quandalf_journal_dm.py`

## Rule
Anything still pointing at old `workspace` must be repointed or disabled. No duplicate automation domains.
