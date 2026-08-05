@echo off
rem GATE-M1 overnight chain — detached runner (survives the Claude session,
rem NOT a logoff: lock the screen, don't sign out). %1 = workers (default 15;
rem use 4-6 when the machine is in daytime use — each worker needs ~1.2GB).
rem Idempotent: rep files are seeded and skipped when present; safe to rerun.
cd /d "C:\Users\mrthn\Aegis module"
set OMP_NUM_THREADS=1
set WORKERS=%1
if "%WORKERS%"=="" set WORKERS=15
echo [%date% %time%] chain start (workers=%WORKERS%) >> runs\GATE-M1\chain.log
.venv\Scripts\python.exe -u scripts\launch_m1_grid.py --wave 1 --reps 250 --workers %WORKERS% >> runs\GATE-M1\grid_wave1.log 2>&1
echo [%date% %time%] wave 1 done (exit %errorlevel%) >> runs\GATE-M1\chain.log
.venv\Scripts\python.exe -u scripts\launch_m1_grid.py --wave 2 --reps 250 --workers %WORKERS% >> runs\GATE-M1\grid_wave2.log 2>&1
echo [%date% %time%] wave 2 done (exit %errorlevel%) >> runs\GATE-M1\chain.log
.venv\Scripts\python.exe -m aegis_brain.calibration.run_grid --aggregate >> runs\GATE-M1\aggregate.log 2>&1
echo [%date% %time%] aggregate done (exit %errorlevel%) >> runs\GATE-M1\chain.log
.venv\Scripts\python.exe -m aegis_brain.calibration.posterior >> runs\GATE-M1\stage4.log 2>&1
echo [%date% %time%] posterior done (exit %errorlevel%) >> runs\GATE-M1\chain.log
.venv\Scripts\python.exe -m aegis_brain.calibration.exhibits >> runs\GATE-M1\stage4.log 2>&1
echo [%date% %time%] M1 CHAIN COMPLETE >> runs\GATE-M1\chain.log
