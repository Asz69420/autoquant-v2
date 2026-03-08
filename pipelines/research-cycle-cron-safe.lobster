name: research-cycle-cron-safe-legacy-noncanonical
steps:
  - id: cycle-start
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-start.py'

  - id: briefing
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\research-cycle.py'

  - id: oragorn-review
    command: 'openclaw agent --agent oragorn --message "Briefing refreshed at agents/quandalf/memory/briefing_packet.json. Create or update agents/quandalf/memory/cycle_orders.json with specific next-cycle orders only. Keep response under 8 lines." --timeout 90000'

  - id: logron-health
    command: 'openclaw agent --agent logron --message "Run a quick health check for the last 30 minutes and report only material issues." --timeout 60000'

  - id: cron-log-marker
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py --send-card-only --since-minutes 30'
