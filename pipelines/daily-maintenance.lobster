name: daily-maintenance
steps:
 - id: health-check
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\logron-monitor.py

 - id: git-sync
   command: powershell -NoProfile -Command "cd C:\Users\Clamps\.openclaw\workspace-oragorn; git add -A; if (git diff --cached --quiet) { exit 0 } else { git commit -m 'auto-sync'; git push }"
