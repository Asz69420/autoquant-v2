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
    # Uses a fresh per-cycle Quandalf session so long-lived main-session context cannot stall the live loop.
    # Non-fatal by design: if Quandalf times out or produces no specs, fallback-cook-specs still gets a chance.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_quandalf_design_cycle.py'

  - id: fallback-cook-specs
    # Safety fallback: if the interactive design step writes no specs, emit a deterministic baseline cooking batch.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\fallback_cook_specs.py'

  - id: capture-cycle-specs
    # File/state handoff from quandalf-design/fallback -> capture-cycle-specs:
    # discover newly written strategy spec files and persist manifest to data/state/current_cycle_specs.json.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\capture_cycle_specs.py'

  - id: research-card
    # Visible evidence card only after spec capture, so Generated reflects real written specs.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\emit_cycle_research_card.py'

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



