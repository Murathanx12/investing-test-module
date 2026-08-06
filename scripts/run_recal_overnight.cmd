@echo off
rem RECAL-1 overnight chain — build the gate-agnostic evidence bank, select
rem and freeze the BRAIN-009 ladder, then report it.
rem
rem Usage:  scripts\run_recal_overnight.cmd [workers] [tag]
rem   workers  default 8.  ~1.2GB each: 15 needs ~18GB (idle machine only),
rem            4-8 when the machine is in daytime use.
rem   tag      default r1  -> bank_r1_NNNN.json
rem
rem Chain:  wave 1 (base + I1, carries every acceptance target)
rem      -> select + FREEZE the ladder on even reps, read odd as held-out
rem      -> wave 2 (I2/I3/I4 design sweep)
rem      -> tables (all / selection / held-out) -> posterior -> exhibits
rem Wave 1 alone unblocks selection; the chain stops rather than selecting
rem on a partial bank, and the keeper resumes it.
rem
rem The frozen BRAIN-008 grid (rep_*.json) is never read or written here.
rem Idempotent: bank files are atomic and skipped when present.  Detached —
rem survives the Claude session, but NOT a logoff: LOCK the screen.
setlocal enabledelayedexpansion
cd /d "C:\Users\mrthn\Aegis module"
set OMP_NUM_THREADS=1
set WORKERS=%1
if "%WORKERS%"=="" set WORKERS=8
set TAG=%2
if "%TAG%"=="" set TAG=r1
set REPS=250
set PY=.venv\Scripts\python.exe
set RUNS=runs\GATE-M1
set LOG=%RUNS%\recal_chain.log
set FROZEN=@%RUNS%/brain009_frozen.json

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

echo [%date% %time%] recal chain start (workers=%WORKERS% tag=%TAG% reps=%REPS%) >> %LOG%

rem ---------------------------------------------------------------- wave 1
%PY% -u scripts\launch_m1_grid.py --wave 1 --reps %REPS% --workers %WORKERS% --ruleset BRAIN-009 --tag %TAG% >> %RUNS%\recal_wave1.log 2>&1
echo [%date% %time%] wave 1 done (exit %errorlevel%) >> %LOG%

for /f %%c in ('dir /b %RUNS%\grid\bank_%TAG%_*.json 2^>nul ^| find /c /v ""') do set NBANK=%%c
if not defined NBANK set NBANK=0
if %NBANK% LSS %REPS% goto :incomplete

rem ------------------------------------------- select + FREEZE the ladder
%PY% -m aegis_brain.calibration.select --tag %TAG% >> %RUNS%\recal_select.log 2>&1
echo [%date% %time%] select done (exit %errorlevel%) -> brain009_frozen.json >> %LOG%
if not exist %RUNS%\brain009_frozen.json goto :nofreeze

rem ---------------------------------------------------------------- wave 2
%PY% -u scripts\launch_m1_grid.py --wave 2 --reps %REPS% --workers %WORKERS% --ruleset BRAIN-009 --tag %TAG% >> %RUNS%\recal_wave2.log 2>&1
echo [%date% %time%] wave 2 done (exit %errorlevel%) >> %LOG%

rem ------------------------------------------------ tables / posterior / exhibits
%PY% -m aegis_brain.calibration.bank --aggregate --tag %TAG% --ruleset %FROZEN% --subset all  >> %RUNS%\recal_tables.log 2>&1
%PY% -m aegis_brain.calibration.bank --aggregate --tag %TAG% --ruleset %FROZEN% --subset even >> %RUNS%\recal_tables.log 2>&1
%PY% -m aegis_brain.calibration.bank --aggregate --tag %TAG% --ruleset %FROZEN% --subset odd  >> %RUNS%\recal_tables.log 2>&1
%PY% -m aegis_brain.calibration.bank --aggregate --tag %TAG% --ruleset BRAIN-008 --subset all >> %RUNS%\recal_tables.log 2>&1
echo [%date% %time%] tables done (exit %errorlevel%) >> %LOG%
%PY% -m aegis_brain.calibration.posterior --tag %TAG% --ruleset %FROZEN% --design I2 >> %RUNS%\recal_stage4.log 2>&1
%PY% -m aegis_brain.calibration.posterior --tag %TAG% --ruleset %FROZEN% --design I1 >> %RUNS%\recal_stage4.log 2>&1
echo [%date% %time%] posterior done (exit %errorlevel%) >> %LOG%
%PY% -m aegis_brain.calibration.exhibits --tag %TAG% --ruleset BRAIN-009 --design I2 >> %RUNS%\recal_stage4.log 2>&1
echo [%date% %time%] exhibits done (exit %errorlevel%) >> %LOG%
echo [%date% %time%] RECAL CHAIN COMPLETE >> %LOG%
exit /b 0

:incomplete
echo [%date% %time%] wave 1 incomplete (%NBANK%/%REPS% bank files) — chain stops before selection; keeper will resume >> %LOG%
exit /b 1

:nofreeze
echo [%date% %time%] ABORT: select produced no brain009_frozen.json (see recal_select.log) >> %LOG%
exit /b 3
