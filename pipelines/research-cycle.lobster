name: research-cycle
steps:
  - id: cycle-start
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-start.py'

  - id: briefing
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\research-cycle.py'

  - id: oragorn-review
    command: 'openclaw agent --agent oragorn --message "Research cycle briefing ready at agents/quandalf/memory/briefing_packet.json. Review it now. Before writing orders, check Quandalf''s recent journal entries and enforce a soft 70/30 exploration-to-exploitation balance across cycles: most cycles should explore, fewer should iterate on already-passing families. Count recent concentration across strategy family, asset, timeframe, and structural concept. If the last 3 journal entries are about the same family, force exploration. If the last 5 are on the same asset, force a different asset. If any one category dominates 4+ of the last 10 entries, rotate away from it this cycle. Only allow iterate_existing for strategies that already scored QScore >= 1.0 on walk-forward. Otherwise direct exploration. Then write specific orders to agents/quandalf/memory/cycle_orders.json as explicit batch orders with: cycle_id, mode (explore OR exploit), minimum_spec_count, maximum_spec_count (cap at 5), target_asset, target_timeframe, research_direction (explore_new OR iterate_existing), specific_family_to_iterate (if applicable), iterate_target (if exploit), exploration_targets {concepts, assets, timeframes} (if explore), thesis_hint, stop_condition, and a one-line rotation_reason explaining why this cycle is exploration or exploitation. Preserve the soft 70/30 explore/exploit doctrine and make the batch size match the mode: explore should normally demand 2-4 materially different specs; exploit should normally demand 1-3 focused passing-family variants. Frame the next step openly: explore a new concept OR iterate on a passing strategy. Do NOT lock Quandalf into micro-tuning the same family unless it is already passing and still deserves refinement. Do NOT give generic orders." --timeout 120000'

  - id: quandalf-design
    command: 'openclaw agent --agent quandalf --message "Read your cycle orders at agents/quandalf/memory/cycle_orders.json. Follow Oragorn''s direction exactly. Do the strategy thinking yourself in this session. Write the FULL batch of strategy specs for this cycle to artifacts/strategy_specs/ and your journal entry to memory/ in one response. Hard contract: if mode is explore, produce 2-4 materially distinct specs spanning DIFFERENT concepts/assets/timeframes as the orders allow; if mode is exploit, produce 1-3 focused variants of the named passing family. Do not drift into one lonely spec per cycle unless Oragorn explicitly set minimum_spec_count to 1 and the evidence justifies it. All spec files for the cycle must be written before you finish. Also write/update agents/quandalf/memory/current_cycle_status.json with: cycle_id, mode, research_direction, minimum_spec_count, maximum_spec_count, spec_paths (ALL paths from this cycle batch), specs_produced, exploration_targets, iterate_target, new_families, iterated_families, abandoned_families (empty list if none yet), next_cycle_focus, and a short rationale field." --timeout 300000'

  - id: capture-cycle-specs
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\capture_cycle_specs.py'

  - id: backtest
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\parallel_runner.py --manifest C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\current_cycle_specs.json --variant all'

  - id: leaderboard-update
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\leaderboard_render.py --preview'

  - id: reflection
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build-reflection-packet.py'

  - id: quandalf-reflect
    command: 'openclaw agent --agent quandalf --message "Review the reflection packet at agents/quandalf/memory/reflection_packet.json. Analyze results deeply yourself and extract genuine lessons. Propose specific refinements with reasoning. Update agents/quandalf/memory/current_cycle_status.json for this cycle with final current-cycle batch fields: cycle_id, mode, research_direction, minimum_spec_count, maximum_spec_count, spec_paths, specs_produced, exploration_targets, iterate_target, new_families, iterated_families, abandoned_families, next_cycle_focus, and rationale. abandoned_families must only include families you are explicitly abandoning from this cycle''s work or reflection, not stale historical baggage." --timeout 300000'

  - id: refine-postprocess
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py'

  - id: logron-health
    command: 'openclaw agent --agent logron --message "Run health checks on the latest cycle. Query event_log for errors in the last 30 minutes. Query backtest_results for QScore trends. Check pipeline_runs for failures. Report to log channel via tg_notify.py --channel log --bot logron. If anything critical, write alert to data/state/agent_messages.json for Oragorn." --timeout 60000'

  - id: xqs-check
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\xqs_runner.py --run'

  - id: tv-grabber
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_tv_grabber.py'
