name: research-cycle
steps:
  - id: cycle-start
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-start.py'

  - id: briefing
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\research-cycle.py'

  - id: oragorn-review
    command: 'openclaw agent --agent oragorn --message "Research cycle briefing ready at agents/quandalf/memory/briefing_packet.json. Review it now. Before writing orders, check Quandalf''s recent journal entries and enforce a soft 70/30 exploration-to-exploitation balance across cycles: most cycles should explore, fewer should iterate on already-passing families. Count recent concentration across strategy family, asset, timeframe, and structural concept. If the last 3 journal entries are about the same family, force exploration. If the last 5 are on the same asset, force a different asset. If any one category dominates 4+ of the last 10 entries, rotate away from it this cycle. Only allow iterate_existing for strategies that already scored QScore >= 1.0 on walk-forward. Otherwise direct exploration. Then write specific orders to agents/quandalf/memory/cycle_orders.json with: target_asset, target_timeframe, research_direction (explore_new OR iterate_existing), specific_family_to_iterate (if applicable), thesis_hint, max_variants (cap at 5), stop_condition, and a one-line rotation_reason explaining why this cycle is exploration or exploitation. Frame the next step openly: explore a new concept OR iterate on a passing strategy. Do NOT lock Quandalf into micro-tuning the same family unless it is already passing and still deserves refinement. Do NOT give generic orders." --timeout 120000'

  - id: quandalf-design
    command: 'openclaw agent --agent quandalf --message "Read your cycle orders at agents/quandalf/memory/cycle_orders.json. Follow Oragorn''s direction exactly. Do the strategy thinking yourself in this session. Write a batch of strategy specs to artifacts/strategy_specs/ and your journal entry to memory/. Throughput doctrine: exploration cycles should usually produce 2-4 materially distinct specs across different concepts/branches inside the directed theme; exploitation cycles should usually produce 1-3 focused variants of the chosen passing family. Only produce fewer if the evidence strongly supports a single high-conviction test. Do not spam near-duplicates. Each spec must represent a meaningfully different hypothesis, regime angle, or implementation branch. Also write/update agents/quandalf/memory/current_cycle_status.json with: cycle_id, research_direction, spec_paths, new_families, iterated_families, abandoned_families (empty list if none yet), and a short rationale field." --timeout 300000'

  - id: capture-cycle-specs
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\capture_cycle_specs.py'

  - id: backtest
    command: 'lobster run --file C:\Users\Clamps\.openclaw\workspace-oragorn\pipelines\parallel-backtest.lobster'

  - id: reflection
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build-reflection-packet.py'

  - id: quandalf-reflect
    command: 'openclaw agent --agent quandalf --message "Review the reflection packet at agents/quandalf/memory/reflection_packet.json. Analyze results deeply yourself and extract genuine lessons. Propose specific refinements with reasoning. Update agents/quandalf/memory/current_cycle_status.json for this cycle with final current-cycle fields: cycle_id, research_direction, spec_paths, new_families, iterated_families, abandoned_families, and rationale. abandoned_families must only include families you are explicitly abandoning from this cycle''s work or reflection, not stale historical baggage." --timeout 300000'

  - id: refine-postprocess
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py'

  - id: logron-health
    command: 'openclaw agent --agent logron --message "Run health checks on the latest cycle. Query event_log for errors in the last 30 minutes. Query backtest_results for QScore trends. Check pipeline_runs for failures. Report to log channel via tg_notify.py --channel log --bot logron. If anything critical, write alert to data/state/agent_messages.json for Oragorn." --timeout 60000'

  - id: xqs-check
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\xqs_runner.py --run'

  - id: tv-grabber
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_tv_grabber.py'
