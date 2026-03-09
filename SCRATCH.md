Active task: Investigate why the pipeline's refinement mode runs but cooking/research does not.

ANALYSIS COMPLETE:

Root cause of 1800s timeout:
- Research pipeline cycle 220 produced ZERO strategy specs (empty manifest from capture-cycle-specs)
- When parallel_runner.py was called with empty manifest, it entered a hanging state
- The cycle-postprocess step likely called walk_forward_engine subprocess or DB operation that deadlocked
- Pipeline ran for 52+ minutes before cron timeout, stuck in backtest/leaderboard/postprocess chain
- cycle_status.json never updated past "pending" mode (stuck before reflection step)

FIX 1: COMPLETE ✅
- Removed xqs-check and tv-grabber steps from research pipeline
- Created independent cron jobs (tv-grabber, youtube-grabber)
- Fixed schedule collisions
- Reduced timeout from 2700s to 900s
- Committed and pushed

FIX 2: IN PROGRESS
- Root cause: empty manifest → parallel_runner hangs → cycle-postprocess hangs
- Solution: Add early-exit check in pipeline
  - If current_cycle_specs.json shows "status": "empty", skip backtest → leaderboard → reflection steps
  - Go directly from capture-cycle-specs to cycle-postprocess → logron-health
  - OR: Add pre-check script that validates manifest before backtest step

Next step:
- Create early-exit wrapper script OR modify pipeline structure to handle empty-spec cycles gracefully
- Re-run pipeline test
- Report final verdict to Asz