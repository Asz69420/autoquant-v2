name: tmp-lobster-smoke
steps:
  - id: echo
    command: 'powershell -NoProfile -Command "Write-Output LOBSTER_SMOKE_OK"'

  - id: dry-run-backtest
    command: 'python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\parallel_runner.py --spec LATEST_SPEC --dry-run'
