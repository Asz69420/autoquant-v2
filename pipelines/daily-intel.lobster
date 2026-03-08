name: daily-intel
steps:
 - id: compile-intel
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\daily-intel-brief.py

 - id: leaderboard
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\leaderboard_render.py --send
