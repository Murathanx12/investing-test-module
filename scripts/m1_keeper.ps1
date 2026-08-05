# M1 chain keeper — runs every 30 min via schtask M1GridKeeper.
# Policy, in order:
#   1. done (second "M1 CHAIN COMPLETE" sentinel)          -> exit
#   2. on battery                                          -> PAUSE grid, exit
#      (compute at full load kills a 30% battery in ~half an hour; rep files
#       are atomic + idempotent, pausing loses only in-flight cells)
#   3. full pool already running (>=12 workers)            -> exit
#   4. partial pool running: bump to 15 iff >=14GB free    -> else leave it
#   5. nothing running: start 15 workers if >=14GB free,
#      else 6 workers if >=7GB free, else wait             -> exit
$repo = "C:\Users\mrthn\Aegis module"
$log = Join-Path $repo "runs\GATE-M1\chain.log"
function Stamp($msg) { Add-Content $log "[$(Get-Date -Format 'ddd dd/MM/yyyy HH:mm:ss')] keeper: $msg" }

$sentinels = (Select-String -Path $log -Pattern "M1 CHAIN COMPLETE" -SimpleMatch -ErrorAction SilentlyContinue).Count
if ($sentinels -ge 2) { exit 0 }   # first sentinel was the 08-04 logoff-wrecked chain

$grid = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
          Where-Object { $_.CommandLine -match "launch_m1_grid|multiprocessing.spawn" })
$onBattery = $false
try { $b = Get-CimInstance Win32_Battery -ErrorAction Stop; $onBattery = ($b.BatteryStatus -eq 1) } catch {}

if ($onBattery) {
    if ($grid.Count -gt 0) {
        Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='cmd.exe'" |
            Where-Object { $_.CommandLine -match "launch_m1_grid|run_m1_overnight|multiprocessing.spawn" } |
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
            Where-Object { $_.CommandLine -match "launch_m1_grid|run_m1_overnight|multiprocessing.spawn" } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep 5
        Stamp "bump to 15 workers (${freeGB}GB free)"
        Start-Process -FilePath (Join-Path $repo "scripts\run_m1_overnight.cmd") -WindowStyle Hidden
    }
    exit 0
}
if ($freeGB -ge 14) {
    Stamp "start 15 workers (${freeGB}GB free)"
    Start-Process -FilePath (Join-Path $repo "scripts\run_m1_overnight.cmd") -WindowStyle Hidden
} elseif ($freeGB -ge 7) {
    Stamp "start 6 workers (${freeGB}GB free)"
    Start-Process -FilePath (Join-Path $repo "scripts\run_m1_overnight.cmd") -ArgumentList "6" -WindowStyle Hidden
} else {
    Stamp "waiting (only ${freeGB}GB free)"
}
