name: parallel-backtest
steps:
 - id: run-parallel
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\parallel_runner.py --spec %SPEC_PATH% --variant all

 - id: leaderboard-update
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\leaderboard_render.py --preview
