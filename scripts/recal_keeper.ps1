# RECAL chain keeper — parameterized so run 1 and run 2 share one policy.
#
# Register (run 2):
#   schtasks /Create /TN RecalGridKeeper /SC MINUTE /MO 30 /F /TR "powershell
#     -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\mrthn\Aegis module\scripts\recal_keeper.ps1'
#     -Runner run_recal2_overnight.cmd -Log recal2_chain.log -Sentinel 'RECAL2 CHAIN COMPLETE'"
#
# Policy, in order:
#   1. done (sentinel present)                     -> exit
#   2. an ABORT line in the log                    -> exit (restarting cannot help)
#   3. on battery                                  -> PAUSE grid, exit
#   4. full pool already running (>=12 workers)    -> exit
#   5. partial pool: bump to 15 iff >=14GB free    -> else leave it
#   6. nothing running: 15 workers if >=14GB free, 6 if >=7GB, else wait
param(
    [string]$Runner   = "run_recal_overnight.cmd",
    [string]$Log      = "recal_chain.log",
    [string]$Sentinel = "RECAL CHAIN COMPLETE"
)
$repo = "C:\Users\mrthn\Aegis module"
$log = Join-Path $repo "runs\GATE-M1\$Log"
$runner = Join-Path $repo "scripts\$Runner"
function Stamp($msg) { Add-Content $log "[$(Get-Date -Format 'ddd dd/MM/yyyy HH:mm:ss')] keeper: $msg" }

if (-not (Test-Path $runner)) { exit 0 }
if (Test-Path $log) {
    if ((Select-String -Path $log -Pattern $Sentinel -SimpleMatch -ErrorAction SilentlyContinue).Count -ge 1) { exit 0 }
    if ((Select-String -Path $log -Pattern "ABORT:" -SimpleMatch -ErrorAction SilentlyContinue).Count -ge 1) { exit 0 }
}

$grid = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
          Where-Object { $_.CommandLine -match "launch_m1_grid|multiprocessing.spawn" })
$onBattery = $false
try { $b = Get-CimInstance Win32_Battery -ErrorAction Stop; $onBattery = ($b.BatteryStatus -eq 1) } catch {}

if ($onBattery) {
    if ($grid.Count -gt 0) {
        Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='cmd.exe'" |
            Where-Object { $_.CommandLine -match "launch_m1_grid|run_recal.*overnight|multiprocessing.spawn" } |
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
            Where-Object { $_.CommandLine -match "launch_m1_grid|run_recal.*overnight|multiprocessing.spawn" } |
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
