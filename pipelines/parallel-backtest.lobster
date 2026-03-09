name: parallel-backtest
steps:
  - id: run-parallel
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\parallel_runner.py --manifest C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\current_cycle_specs.json --variant all'

  - id: leaderboard-update
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\leaderboard_render.py --preview'
