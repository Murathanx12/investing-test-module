# RECAL-1 chain keeper — same policy as m1_keeper.ps1, own log + sentinel.
# Register:  schtasks /Create /TN RecalGridKeeper /SC MINUTE /MO 30 /RL HIGHEST /F ^
#   /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\mrthn\Aegis module\scripts\recal_keeper.ps1\""
# Policy, in order:
#   1. done ("RECAL CHAIN COMPLETE" sentinel)      -> exit
#   2. on battery                                  -> PAUSE grid, exit
#      (full load kills a 30% battery in ~half an hour; rep files are atomic
#       + idempotent, so pausing loses only in-flight cells)
#   3. full pool already running (>=12 workers)    -> exit
#   4. partial pool: bump to 15 iff >=14GB free    -> else leave it
#   5. nothing running: 15 workers if >=14GB free, 6 if >=7GB, else wait
$repo = "C:\Users\mrthn\Aegis module"
$log = Join-Path $repo "runs\GATE-M1\recal_chain.log"
$runner = Join-Path $repo "scripts\run_recal_overnight.cmd"
function Stamp($msg) { Add-Content $log "[$(Get-Date -Format 'ddd dd/MM/yyyy HH:mm:ss')] keeper: $msg" }

if (Test-Path $log) {
    if ((Select-String -Path $log -Pattern "RECAL CHAIN COMPLETE" -SimpleMatch -ErrorAction SilentlyContinue).Count -ge 1) { exit 0 }
    # a guard ABORT means BRAIN-009 isn't wired yet — restarting can't help.
    if ((Select-String -Path $log -Pattern "ABORT:" -SimpleMatch -ErrorAction SilentlyContinue).Count -ge 1) { exit 0 }
}

$grid = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
          Where-Object { $_.CommandLine -match "launch_m1_grid|multiprocessing.spawn" })
$onBattery = $false
try { $b = Get-CimInstance Win32_Battery -ErrorAction Stop; $onBattery = ($b.BatteryStatus -eq 1) } catch {}

if ($onBattery) {
    if ($grid.Count -gt 0) {
        Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='cmd.exe'" |
            Where-Object { $_.CommandLine -match "launch_m1_grid|run_recal_overnight|multiprocessing.spawn" } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Stamp "PAUSED (on battery, $($b.EstimatedChargeRemaining)%)"
    }
    exit 0
}

$freeGB = [math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB)
if ($grid.Count -ge 12) { exit 0 }
if ($grid.Count -gt 0) {
    if ($freeGB -ge 14) {
        Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='cmd.exe'" |
            Where-Object { $_.CommandLine -match "launch_m1_grid|run_recal_overnight|multiprocessing.spawn" } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep 5
        Stamp "bump to 15 workers (${freeGB}GB free)"
        Start-Process -FilePath $runner -ArgumentList "15" -WindowStyle Hidden
    }
    exit 0
}
if ($freeGB -ge 14) {
    Stamp "start 15 workers (${freeGB}GB free)"
    Start-Process -FilePath $runner -ArgumentList "15" -WindowStyle Hidden
} elseif ($freeGB -ge 7) {
    Stamp "start 6 workers (${freeGB}GB free)"
    Start-Process -FilePath $runner -ArgumentList "6" -WindowStyle Hidden
} else {
    Stamp "waiting (only ${freeGB}GB free)"
}
