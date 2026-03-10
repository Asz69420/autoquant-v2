# Legacy Automation Retirement

## Purpose
Keep automation tidy by documenting which scheduled tasks were retired, disabled, or repointed during the workspace-oragorn consolidation.

## Repointed to current repo
- `AutoQuant-autopilot`
  - now points to `workspace-oragorn`
  - uses `scripts/automation/run_autopilot_task.ps1`
- `AutoQuant-tv-catalog`
  - now points to `workspace-oragorn`
  - uses `scripts/tv_catalog_worker.py`

## Disabled as legacy / currently unusable
- `AutoQuant-build-queue-worker`
- `AutoQuant-bundle-run-log-user`
- `AutoQuant-Claude-Bridge`
- `AutoQuant-Claude-DeepIterator`
- `AutoQuant-keeper-30m`
- `AutoQuant-keeper-startup`
- `AutoQuant-Oragorn-Subagent-Monitor`
- `AutoQuant-tg_reporter`
- `AutoQuant-tg_reporter-watchdog`
- `AutoQuant-youtube-watch`

## Why disabled
These tasks were still targeting the old `C:\Users\Clamps\.openclaw\workspace` repo, had no clear current-repo implementation, or would create overlap/fragmentation with the new Oragorn-centered automation layer.

## Notes
- Claude Code related tasks are disabled and should stay optional/non-core until usage resets and a current-repo workflow is intentionally reintroduced.
- YouTube watching may be reintroduced later via the current skill/pipeline architecture rather than the old worker path.
- If any retired task is revived later, it should point to `workspace-oragorn` and be documented before being re-enabled.
