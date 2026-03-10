# Active Task: Quick wins audit fixes (2-5) + cycle-postprocess split planning

## Fix 2: Trim briefing packet — cut funding_rates to top 5, limit backtest_details to 5
## Fix 3: Add WAL mode to all DB connections
## Fix 4: Archive old strategy specs (>48h, not in leaderboard)
## Fix 5: Remove v1-* legacy memory files (confirmed zero references)
## Fix 6: Compact strategy_status.json (keep last 50 entries only)
## Bonus: Split cycle-postprocess into modules
