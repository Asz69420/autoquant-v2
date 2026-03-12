param()
$ErrorActionPreference = 'Stop'
$ROOT = 'C:\Users\Clamps\.openclaw\workspace-oragorn'
$LOCK = Join-Path $ROOT 'data\state\autopilot_continuous.lock'
$PAUSE = Join-Path $ROOT 'data\state\autopilot_continuous.pause'
$FAIL_SLEEP_SECONDS = 30
$mutex = $null
$hasMutex = $false
Set-Location $ROOT

try {
  git config --global --add safe.directory $ROOT 2>$null | Out-Null
} catch {}

try {
  $mutex = New-Object System.Threading.Mutex($false, 'Global\AutoQuantContinuousAutopilot')
  $hasMutex = $mutex.WaitOne(0, $false)
} catch {
  $hasMutex = $false
}

if (-not $hasMutex) {
  Write-Host 'Continuous autopilot already running (mutex held); exiting duplicate launcher'
  exit 0
}

if (Test-Path $LOCK) {
  try {
    $existing = (Get-Content $LOCK -ErrorAction Stop | Out-String).Trim()
    if ($existing -match 'PID=(\d+)') {
      $existingPid = [int]$matches[1]
      $alive = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
      if ($alive -and $existingPid -ne $PID) {
        Write-Host "Continuous autopilot already claimed by live PID $existingPid"
        exit 0
      }
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
    python scripts\run_cycle_once.py
    $researchExit = $LASTEXITCODE
    if ($researchExit -ne 0) {
      Write-Host "[autopilot] research cycle failed with exit $researchExit"
      Start-Sleep -Seconds $FAIL_SLEEP_SECONDS
      continue
    }

    Write-Host "[autopilot] research cycle finished; chaining immediately into the next research cycle"
  }
}
finally {
  Remove-Item $LOCK -Force -ErrorAction SilentlyContinue
  if ($mutex) {
    try {
      if ($hasMutex) { $mutex.ReleaseMutex() | Out-Null }
    } catch {}
    try { $mutex.Dispose() } catch {}
  }
}
