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

  - id: research-program-update
    # Build Quandalf's live research operating file for the next design pass.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build_quandalf_research_program.py'

  - id: quandalf-design
    # File/state handoff from oragorn-review -> quandalf-design:
    # consumer reads cycle_orders.json and writes spec files + current_cycle_status.json.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_with_timeout.py 420 C:\Users\Clamps\AppData\Roaming\npm\openclaw.cmd agent --agent quandalf --message "Read briefing_packet.json, cycle_orders.json, research_program.json, reflection_packet.json, and current_cycle_status.json. You own the strategy decisions for this cycle. The pipeline only executes what you choose and returns results. HARD CONSTRAINT: every spec you write must stay inside the supported/fetchable backtest universe from briefing_packet.json and cycle_orders.json. You are allowed to choose the best-fit asset/timeframe from the validation basket based on thesis; do not confine yourself to the primary lane if another basket lane fits better. Design strategies as market mechanism -> component roles -> testable rules -> failure modes -> refinement path, not decorative indicator stacks. For every strategy, include a mandatory pre-submit reasoning block covering: market behavior targeted, why edge should exist, asset/timeframe fit, indicator role map, expected regime, likely failure mode, first refinement path, expected trade density, expected outcome pattern, what would count as success, and what would count as failure. Each strategy may request a multi-lane test basket, not just one lane. For every chosen lane, explain why that asset/timeframe belongs in the test, what result would justify continuing, what result would justify rotating away, and what you expect to happen there if the thesis is actually right. Encode those lanes in the strategy spec using `validation_basket` or `test_lanes` so the backtester can run all requested lanes. Run the density sanity check before submission: plausible trade count, contradictory filters, event sparsity, and asset/timeframe mismatch. Treat indicators as components with roles, not standalone strategies. Write the FULL batch of strategy specs for this cycle to artifacts/strategy_specs/. Do not generate cosmetic variants like EMA 9 -> 10 unless you explicitly justify the expected effect. Do not write or update a per-cycle journal as part of the live research cycle. Hard contract: if mode is explore, produce 2-4 materially distinct specs across the best-fit lanes in the allowed basket; if mode is exploit, produce 1-3 focused variants of the named passing strategy. Do not drift into one lonely spec per cycle unless minimum_spec_count is 1 and the evidence justifies it. All spec files for the cycle must be written before you finish. Also write/update agents/quandalf/memory/current_cycle_status.json with the SAME cycle_id as cycle_orders.json for this run. Do not increment it. Write: cycle_id, mode, research_direction, minimum_spec_count, maximum_spec_count, spec_paths, specs_produced, exploration_targets, iterate_target, new_families, iterated_families, abandoned_families, next_cycle_focus, and rationale. Treat 0-trade grammar as a red flag and avoid reusing it. Your live working context is briefing packet + cycle orders + research program + reflection packet + current cycle status." --timeout 300000'

  - id: fallback-cook-specs
    # Safety fallback: if the interactive design step writes no specs, emit a deterministic baseline cooking batch.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\fallback_cook_specs.py'

  - id: capture-cycle-specs
    # File/state handoff from quandalf-design/fallback -> capture-cycle-specs:
    # discover newly written strategy spec files and persist manifest to data/state/current_cycle_specs.json.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\capture_cycle_specs.py'

  - id: prepare-cycle-lanes
    # Ensure requested asset/timeframe lanes exist locally with fresh candle data before backtesting.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\prepare_cycle_lanes.py'

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
    # ensure complete decision closure: one strategy decision per spec and one queue decision per tested row.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\ensure_quandalf_decisions_complete.py'

  - id: validate-quandalf-decisions
    # Hard law: every tested strategy must have one explicit decision, and refine decisions must carry required fields.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\validate_quandalf_decisions.py'

  - id: experiment-memory-update
    # Structured experiment objects for the current cycle.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build_quandalf_experiment_memory.py'

  - id: learning-loop-update
    # Durable learning update from reflection + decisions + status.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build_quandalf_learning_memory.py'

  - id: refine-postprocess
    # File/DB/state handoff from quandalf-reflect -> refine-postprocess:
    # cycle-postprocess reads current_cycle_status.json, manifest, run-state, DB rows, and journals.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py'



