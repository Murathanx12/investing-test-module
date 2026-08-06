@echo off
rem RECAL-1 overnight chain — re-grid the simulator under the CANDIDATE
rem BRAIN-009 (information-gated) ladder.  Frozen BRAIN-008 grid is never
rem touched: new rep files carry a tag (rep_r1_*.json).
rem
rem Usage:  scripts\run_recal_overnight.cmd [workers] [tag]
rem   workers  default 8.  ~1.2GB each: 15 needs ~18GB (idle machine only),
rem            4-8 when the machine is in daytime use.
rem   tag      default r1  -> rep_r1_*.json, stage3_tables_r1.json
rem
rem Idempotent: rep files are written atomically and skipped when present,
rem so a killed run resumes where it stopped.  Detached — survives the
rem Claude session, but NOT a logoff: LOCK the screen, never sign out.
setlocal
cd /d "C:\Users\mrthn\Aegis module"
set OMP_NUM_THREADS=1
set WORKERS=%1
if "%WORKERS%"=="" set WORKERS=8
set TAG=%2
if "%TAG%"=="" set TAG=r1
set PY=.venv\Scripts\python.exe
set LOG=runs\GATE-M1\recal_chain.log

rem --- guard: refuse to run until BRAIN-009 is actually wired.  Without
rem --- these flags this chain would silently re-run the frozen BRAIN-008
rem --- grid and overwrite its rep files — a green run proving nothing.
%PY% -m aegis_brain.calibration.run_grid --help > "%TEMP%\recal_help.txt" 2>&1
findstr /C:"--ruleset" "%TEMP%\recal_help.txt" >nul
if errorlevel 1 (
  echo [%date% %time%] ABORT: run_grid has no --ruleset flag ^(BRAIN-009 not implemented^) >> %LOG%
  exit /b 2
)
findstr /C:"--tag" "%TEMP%\recal_help.txt" >nul
if errorlevel 1 (
  echo [%date% %time%] ABORT: run_grid has no --tag flag ^(would clobber the BRAIN-008 grid^) >> %LOG%
  exit /b 2
)

echo [%date% %time%] recal chain start (workers=%WORKERS% tag=%TAG% ruleset=BRAIN-009) >> %LOG%
%PY% -u scripts\launch_m1_grid.py --wave 1 --reps 250 --workers %WORKERS% --ruleset BRAIN-009 --tag %TAG% >> runs\GATE-M1\recal_wave1.log 2>&1
echo [%date% %time%] wave 1 done (exit %errorlevel%) >> %LOG%
%PY% -u scripts\launch_m1_grid.py --wave 2 --reps 250 --workers %WORKERS% --ruleset BRAIN-009 --tag %TAG% >> runs\GATE-M1\recal_wave2.log 2>&1
echo [%date% %time%] wave 2 done (exit %errorlevel%) >> %LOG%
%PY% -m aegis_brain.calibration.run_grid --aggregate --tag %TAG% >> runs\GATE-M1\recal_aggregate.log 2>&1
echo [%date% %time%] aggregate done (exit %errorlevel%) >> %LOG%
%PY% -m aegis_brain.calibration.posterior --tag %TAG% >> runs\GATE-M1\recal_stage4.log 2>&1
echo [%date% %time%] posterior done (exit %errorlevel%) >> %LOG%
%PY% -m aegis_brain.calibration.exhibits --tag %TAG% >> runs\GATE-M1\recal_stage4.log 2>&1
echo [%date% %time%] exhibits done (exit %errorlevel%) >> %LOG%
echo [%date% %time%] RECAL CHAIN COMPLETE >> %LOG%
endlocal
