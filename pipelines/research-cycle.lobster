name: research-cycle
steps:
  - id: cycle-start
    # File/state handoff root: allocate cycle/run state marker for the whole run.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-start.py'

  - id: briefing
    # File/state handoff: writes agents/quandalf/memory/briefing_packet.json.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\research-cycle.py'

  - id: oragorn-review
    # Deterministic cycle-order builder. Avoid nested self-calls to Oragorn inside the pipeline.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build_cycle_orders.py'

  - id: quandalf-design
    # File/state handoff from oragorn-review -> quandalf-design:
    # consumer reads cycle_orders.json and writes spec files + current_cycle_status.json.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_with_timeout.py 210 C:\Users\Clamps\AppData\Roaming\npm\openclaw.cmd agent --agent quandalf --message "Read your cycle orders at agents/quandalf/memory/cycle_orders.json. Follow Oragorn''s direction exactly. Do the strategy thinking yourself in this session. HARD CONSTRAINT: every spec you write must keep the ordered asset/timeframe inside the supported backtest universe from agents/quandalf/memory/briefing_packet.json. Do not invent unsupported assets or unsupported timeframes. Write the FULL batch of strategy specs for this cycle to artifacts/strategy_specs/. Do not write or update a per-cycle journal as part of the live research cycle. Hard contract: if mode is explore, produce 2-4 materially distinct specs spanning DIFFERENT concepts/assets/timeframes as the orders allow; if mode is exploit, produce 1-3 focused variants of the named passing family. Do not drift into one lonely spec per cycle unless Oragorn explicitly set minimum_spec_count to 1 and the evidence justifies it. All spec files for the cycle must be written before you finish. Also write/update agents/quandalf/memory/current_cycle_status.json with the SAME cycle_id as agents/quandalf/memory/cycle_orders.json for this run. Do not increment it. Write: cycle_id, mode, research_direction, minimum_spec_count, maximum_spec_count, spec_paths (ALL paths from this cycle batch), specs_produced, exploration_targets, iterate_target, new_families, iterated_families, abandoned_families (empty list if none yet), next_cycle_focus, and a short rationale field. Your live working context for cycle execution is briefing packet + cycle orders + reflection packet + current cycle status, not per-cycle journals." --timeout 120000'

  - id: fallback-cook-specs
    # Safety fallback: if the interactive design step writes no specs, emit a deterministic baseline cooking batch.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\fallback_cook_specs.py'

  - id: capture-cycle-specs
    # File/state handoff from quandalf-design/fallback -> capture-cycle-specs:
    # discover newly written strategy spec files and persist manifest to data/state/current_cycle_specs.json.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\capture_cycle_specs.py'

  - id: backtest
    # File/state handoff from capture-cycle-specs -> backtest:
    # runner seeds the SQLite research_funnel_queue from current_cycle_specs.json, then processes staged work
    # within the same cycle (screen -> full -> validation) subject to per-cycle limits.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\parallel_runner.py --manifest C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\current_cycle_specs.json --variant all'

  - id: leaderboard-update
    # DB/state handoff from backtest -> leaderboard-update via backtest_results rows.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\leaderboard_render.py --preview'

  - id: reflection
    # DB/state handoff from backtest/leaderboard path -> reflection:
    # build-reflection-packet reads DB state and writes agents/quandalf/memory/reflection_packet.json.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build-reflection-packet.py'

  - id: quandalf-reflect
    # File/state handoff from reflection -> quandalf-reflect:
    # consumer reads reflection_packet.json directly; it does not consume stdin.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_with_timeout.py 330 C:\Users\Clamps\AppData\Roaming\npm\openclaw.cmd agent --agent quandalf --message "Review the reflection packet at agents/quandalf/memory/reflection_packet.json. Analyze results deeply yourself and extract genuine lessons. Propose specific refinements with reasoning. Update agents/quandalf/memory/current_cycle_status.json for this cycle with final current-cycle batch fields. Keep cycle_id exactly equal to the active run cycle_id already in current_cycle_status/briefing/cycle_orders for this run. Do not increment it. Write: cycle_id, mode, research_direction, minimum_spec_count, maximum_spec_count, spec_paths, specs_produced, exploration_targets, iterate_target, new_families, iterated_families, abandoned_families, next_cycle_focus, and rationale. abandoned_families must only include families you are explicitly abandoning from this cycle''s work or reflection, not stale historical baggage." --timeout 300000'

  - id: refine-postprocess
    # File/DB/state handoff from quandalf-reflect -> refine-postprocess:
    # cycle-postprocess reads current_cycle_status.json, manifest, run-state, DB rows, and journals.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py'

  - id: refinement-run
    # Chained handoff: refinement runs only after cooking/research has completed and posted its current-cycle results.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\refinement_cycle.py'

  - id: logron-health
    # Final health/reporting pass after the chained cooking -> refinement cycle finishes.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\logron-monitor.py'

