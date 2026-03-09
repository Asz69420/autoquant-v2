name: research-cycle
steps:
  - id: cycle-start
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-start.py'

  - id: briefing
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\research-cycle.py'

  - id: oragorn-review
    command: 'openclaw agent --agent oragorn --message "Research cycle briefing ready at agents/quandalf/memory/briefing_packet.json. Review it now. Check QScore trends from the last 3 cycles. Check if quality is improving or declining. Then write specific orders to agents/quandalf/memory/cycle_orders.json with: target_asset, target_timeframe, research_direction (explore_new OR iterate_existing), specific_family_to_iterate (if applicable), thesis_hint, max_variants (cap at 5), and stop_condition. If recent QScores are declining, set research_direction to iterate_existing and pick the best-performing family. If quality is good, allow exploration. Do NOT give Quandalf generic orders." --timeout 120000'

  - id: quandalf-design
    command: 'openclaw agent --agent quandalf --message "Read your cycle orders at agents/quandalf/memory/cycle_orders.json. Follow Oragorn''s direction exactly. Do the strategy thinking yourself in this session. Write your strategy spec to artifacts/strategy_specs/ and your journal entry to memory/." --timeout 300000'

  - id: capture-cycle-specs
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\capture_cycle_specs.py'

  - id: backtest
    command: 'lobster run --file C:\Users\Clamps\.openclaw\workspace-oragorn\pipelines\parallel-backtest.lobster'

  - id: reflection
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build-reflection-packet.py'

  - id: quandalf-reflect
    command: 'openclaw agent --agent quandalf --message "Review the reflection packet at agents/quandalf/memory/reflection_packet.json. Analyze results deeply yourself and extract genuine lessons. Propose specific refinements with reasoning." --timeout 300000'

  - id: refine-postprocess
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py'

  - id: logron-health
    command: 'openclaw agent --agent logron --message "Run health checks on the latest cycle. Query event_log for errors in the last 30 minutes. Query backtest_results for QScore trends. Check pipeline_runs for failures. Report to log channel via tg_notify.py --channel log --bot logron. If anything critical, write alert to data/state/agent_messages.json for Oragorn." --timeout 60000'

  - id: xqs-check
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\xqs_runner.py --run'

  - id: tv-grabber
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_tv_grabber.py'
