param()
$ErrorActionPreference = 'Stop'
$ROOT = 'C:\Users\Clamps\.openclaw\workspace-oragorn'
$LOCK = Join-Path $ROOT 'data\state\autopilot_continuous.lock'
$SLEEP_SECONDS = 30
Set-Location $ROOT

try {
  git config --global --add safe.directory $ROOT 2>$null | Out-Null
} catch {}

if (Test-Path $LOCK) {
  try {
    $existing = Get-Content $LOCK -ErrorAction Stop
    if ($existing) {
      Write-Host "Continuous autopilot already claimed by: $existing"
      exit 0
    }
  } catch {}
}

"PID=$PID START=$(Get-Date -Format o)" | Set-Content -Path $LOCK -Encoding UTF8

try {
  while ($true) {
    Write-Host "[autopilot] starting research cycle $(Get-Date -Format o)"
    openclaw lobster run --pipeline pipelines/research-cycle.lobster --cwd .
    $researchExit = $LASTEXITCODE
    if ($researchExit -ne 0) {
      Write-Host "[autopilot] research cycle failed with exit $researchExit"
      Start-Sleep -Seconds $SLEEP_SECONDS
      continue
    }

    Write-Host "[autopilot] starting daily maintenance $(Get-Date -Format o)"
    openclaw lobster run --pipeline pipelines/daily-maintenance.lobster --cwd .
    $maintExit = $LASTEXITCODE
    if ($maintExit -ne 0) {
      Write-Host "[autopilot] maintenance failed with exit $maintExit"
    }

    Start-Sleep -Seconds $SLEEP_SECONDS
  }
}
finally {
  Remove-Item $LOCK -Force -ErrorAction SilentlyContinue
}
