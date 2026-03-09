name: refinement-cycle
steps:
  - id: refinement-run
    # DB/state handoff: refinement_cycle scans PASS families, generates refinement jobs, runs capped backtests through parallel_runner, updates statuses, journals, and log card.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\refinement_cycle.py'
