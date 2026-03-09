name: research-cycle-cron-safe-legacy-noncanonical
steps:
  - id: cycle-start
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-start.py'

  - id: briefing
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\research-cycle.py'

  - id: oragorn-review
    command: 'openclaw agent --agent oragorn --message "Briefing refreshed at agents/quandalf/memory/briefing_packet.json. Check Quandalf''s recent journal entries before writing orders. Enforce a soft 70/30 exploration-to-exploitation balance, rotate away from overused family/asset/timeframe/concept clusters, and force exploration if he has been exploiting too long. Only iterate on families that already passed walk-forward. Create or update agents/quandalf/memory/cycle_orders.json with explicit next-cycle batch orders only: cycle_id, mode, minimum_spec_count, maximum_spec_count, target_asset, target_timeframe, research_direction, iterate_target (if exploit), exploration_targets {concepts, assets, timeframes} (if explore), thesis_hint, stop_condition, and a short rotation_reason. Keep response under 8 lines." --timeout 90000'

  - id: logron-health
    # Health card delivery owned by logron-monitor.py with built-in dedup.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\logron-monitor.py'

  - id: cron-log-marker
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py --send-card-only --since-minutes 30'
