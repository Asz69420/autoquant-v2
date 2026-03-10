param()
$ErrorActionPreference = 'Stop'
$ROOT = 'C:\Users\Clamps\.openclaw\workspace-oragorn'
Set-Location $ROOT

# Ensure git trust in the scheduled-task user context.
try {
  git config --global --add safe.directory $ROOT 2>$null | Out-Null
} catch {}

# Research cycle first, then daily maintenance. Both are canonical Oragorn paths.
openclaw lobster run --pipeline pipelines/research-cycle.lobster --cwd .
$researchExit = $LASTEXITCODE
if ($researchExit -ne 0) {
  exit $researchExit
}

openclaw lobster run --pipeline pipelines/daily-maintenance.lobster --cwd .
exit $LASTEXITCODE
