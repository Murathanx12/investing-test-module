@echo off
rem Evening bump: restart the M1 chain at 15 workers once the machine is free.
rem RAM guard: skips (leaves the current pool running) if <14GB free, because
rem a 15-worker pool needs ~18GB and dies SILENTLY when it can't get it.
cd /d "C:\Users\mrthn\Aegis module"
for /f %%m in ('powershell -NoProfile -Command "[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)"') do set FREEGB=%%m
if %FREEGB% LSS 14 (
  echo [%date% %time%] bump skipped: only %FREEGB%GB free >> runs\GATE-M1\chain.log
  exit /b 0
)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='cmd.exe'\" | Where-Object { $_.CommandLine -match 'launch_m1_grid|run_m1_overnight|multiprocessing.spawn' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 5 /nobreak >nul
echo [%date% %time%] bumping to 15 workers (%FREEGB%GB free) >> runs\GATE-M1\chain.log
start "" /min cmd /c "C:\Users\mrthn\Aegis module\scripts\run_m1_overnight.cmd"
