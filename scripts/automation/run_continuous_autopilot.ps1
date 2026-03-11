param()
$ErrorActionPreference = 'Stop'
$ROOT = 'C:\Users\Clamps\.openclaw\workspace-oragorn'
$LOCK = Join-Path $ROOT 'data\state\autopilot_continuous.lock'
$PAUSE = Join-Path $ROOT 'data\state\autopilot_continuous.pause'
$FAIL_SLEEP_SECONDS = 30
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
    if (Test-Path $PAUSE) {
      Write-Host "[autopilot] pause flag detected at $(Get-Date -Format o); stopping continuous cooking loop"
      break
    }

    Write-Host "[autopilot] starting research cycle $(Get-Date -Format o)"
    lobster run --mode tool pipelines/research-cycle.lobster
    $researchExit = $LASTEXITCODE
    if ($researchExit -ne 0) {
      Write-Host "[autopilot] research cycle failed with exit $researchExit"
      Start-Sleep -Seconds $FAIL_SLEEP_SECONDS
      continue
    }

    Write-Host "[autopilot] starting daily maintenance $(Get-Date -Format o)"
    lobster run --mode tool pipelines/daily-maintenance.lobster
    $maintExit = $LASTEXITCODE
    if ($maintExit -ne 0) {
      Write-Host "[autopilot] maintenance failed with exit $maintExit"
    }

    Write-Host "[autopilot] cycle finished; chaining immediately into the next research cycle"
  }
}
finally {
  Remove-Item $LOCK -Force -ErrorAction SilentlyContinue
}
