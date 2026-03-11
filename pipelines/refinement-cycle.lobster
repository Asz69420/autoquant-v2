name: refinement-cycle
steps:
  - id: refinement-run
    # Independent refinement worker: reads Quandalf's explicit strategy decisions/refinement jobs,
    # runs only when there is refinement work, and otherwise exits idle without blocking cooking.
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\refinement_cycle.py'
