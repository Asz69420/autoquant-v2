name: research-cycle-cron-safe-legacy-noncanonical
steps:
  - id: cycle-start
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-start.py'

  - id: briefing
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\research-cycle.py'

  - id: oragorn-review
    command: 'openclaw agent --agent oragorn --message "Briefing refreshed at agents/quandalf/memory/briefing_packet.json. Check Quandalf''s recent journal entries before writing orders. Enforce a soft 70/30 exploration-to-exploitation balance, rotate away from overused family/asset/timeframe/concept clusters, and force exploration if he has been exploiting too long. Only iterate on families that already passed walk-forward. Create or update agents/quandalf/memory/cycle_orders.json with specific next-cycle orders only, including a short rotation_reason. Keep response under 8 lines." --timeout 90000'

  - id: logron-health
    command: 'openclaw agent --agent logron --message "Run a quick health check for the last 30 minutes and report only material issues." --timeout 60000'

  - id: cron-log-marker
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py --send-card-only --since-minutes 30'
