name: research-cycle
steps:
  - id: cycle-start
    # File/state handoff root: allocate cycle/run state marker for the whole run.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-start.py'

  - id: regime-refresh
    # Refresh regime tags for all candle data before briefing so Quandalf gets current market context.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\refresh_regimes.py'

  - id: briefing
    # File/state handoff: writes agents/quandalf/memory/briefing_packet.json.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\research-cycle.py'

  - id: oragorn-review
    # Deterministic cycle-order builder. Avoid nested self-calls to Oragorn inside the pipeline.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build_cycle_orders.py'

  - id: quandalf-design
    # File/state handoff from oragorn-review -> quandalf-design:
    # consumer reads cycle_orders.json and writes spec files + current_cycle_status.json.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_with_timeout.py 420 C:\Users\Clamps\AppData\Roaming\npm\openclaw.cmd agent --agent quandalf --message "Read briefing_packet.json, cycle_orders.json, reflection_packet.json, and current_cycle_status.json. You own the strategy decisions for this cycle. The pipeline only executes what you choose and returns results. HARD CONSTRAINT: every spec you write must stay inside the supported backtest universe from briefing_packet.json. Do not invent unsupported assets or unsupported timeframes. Write the FULL batch of strategy specs for this cycle to artifacts/strategy_specs/. Do not write or update a per-cycle journal as part of the live research cycle. Hard contract: if mode is explore, produce 2-4 materially distinct specs inside the current lane; if mode is exploit, produce 1-3 focused variants of the named passing strategy. Do not drift into one lonely spec per cycle unless minimum_spec_count is 1 and the evidence justifies it. All spec files for the cycle must be written before you finish. Also write/update agents/quandalf/memory/current_cycle_status.json with the SAME cycle_id as cycle_orders.json for this run. Do not increment it. Write: cycle_id, mode, research_direction, minimum_spec_count, maximum_spec_count, spec_paths, specs_produced, exploration_targets, iterate_target, new_families, iterated_families, abandoned_families, next_cycle_focus, and rationale. Treat 0-trade grammar as a red flag and avoid reusing it. Your live working context is briefing packet + cycle orders + reflection packet + current cycle status." --timeout 300000'

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
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_with_timeout.py 330 C:\Users\Clamps\AppData\Roaming\npm\openclaw.cmd agent --agent quandalf --message "Review agents/quandalf/memory/reflection_packet.json. Make an explicit decision for every strategy in the packet: promote, refine, abort, or fix_only if there was a real system/data issue. If a strategy produced 0 trades on valid data, that is a red flag and it must resolve into exactly one of two paths: refine or abort. Do not leave it undecided and do not treat it as a skipped outcome. You are not allowed to write a blank decision set: every strategy in the packet must appear in your decision output with an explicit outcome. Update agents/quandalf/memory/current_cycle_status.json for this cycle with final current-cycle batch fields. Keep cycle_id exactly equal to the active run cycle_id already in current_cycle_status/briefing/cycle_orders for this run. Do not increment it. Write: cycle_id, mode, research_direction, minimum_spec_count, maximum_spec_count, spec_paths, specs_produced, exploration_targets, iterate_target, new_families, iterated_families, abandoned_families, next_cycle_focus, and rationale. Also write agents/quandalf/memory/refinement_decisions.json with fields: cycle_id, ts_iso, strategy_decisions, jobs. strategy_decisions must contain one entry for every strategy in the reflection packet, each with strategy_spec_id, decision, rationale, and when relevant source_result_id or source_strategy_spec_id. jobs must be a list of explicit refinement/backtest commands chosen by you. Each job must include decision, source_result_id or source_strategy_spec_id, strategy_spec_id, spec_path, mutation_type, priority, and rationale. Only include jobs with decision=refine. If nothing should be refined, jobs may be empty, but strategy_decisions must still be complete. The pipeline will execute only what you choose." --timeout 300000'

  - id: refine-postprocess
    # File/DB/state handoff from quandalf-reflect -> refine-postprocess:
    # cycle-postprocess reads current_cycle_status.json, manifest, run-state, DB rows, and journals.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py'


