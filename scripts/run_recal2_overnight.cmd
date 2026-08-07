@echo off
rem RECAL-1 RUN 2 — finish what run 1 could not.
rem
rem Run 1 (2026-08-06/07) established the headline result on wave 1 and froze
rem BRAIN-009. Three things were left:
rem   1. wave 2 (I2/I3/I4) never ran — a file-aware skip made it a 24-second
rem      no-op that exited 0. Fixed: the skip is now CELL-aware and every wave
rem      asserts its own coverage before the chain continues.
rem   2. the alpha=0 cell has only n=250, which (a) left FDR at
rem      [0.44%, 5.65%] and (b) drove the fine posterior map's monotonicity
rem      violations off 0-vs-1 null counts. Wave 3 adds 1000 null-only reps.
rem   3. the S3 sizing ladder needs confirming on nulls it was not chosen on.
rem
rem The run-1 FREEZE IS NOT TOUCHED. brain009_frozen.json stays as it is; the
rem enlarged-null selection is written to brain009_selection_n1250.json as a
rem labelled SENSITIVITY, and swapping the ladder is Murat's attended call.
rem
rem Usage:  scripts\run_recal2_overnight.cmd [workers]
rem LOCK the screen, do not sign out. Idempotent; the keeper resumes it.
setlocal enabledelayedexpansion
cd /d "C:\Users\mrthn\Aegis module"
set OMP_NUM_THREADS=1
set WORKERS=%1
if "%WORKERS%"=="" set WORKERS=15
set TAG=r1
set PY=.venv\Scripts\python.exe
set RUNS=runs\GATE-M1
set LOG=%RUNS%\recal2_chain.log
set FROZEN=@%RUNS%/brain009_frozen.json

if not exist %RUNS%\brain009_frozen.json (
  echo [%date% %time%] ABORT: no brain009_frozen.json — run 1 must be complete first >> %LOG%
  exit /b 2
)
%PY% -m aegis_brain.calibration.run_grid --help > "%TEMP%\recal2_help.txt" 2>&1
findstr /C:"--ruleset" "%TEMP%\recal2_help.txt" >nul
if errorlevel 1 (
  echo [%date% %time%] ABORT: run_grid has no --ruleset flag >> %LOG%
  exit /b 2
)

echo [%date% %time%] recal2 chain start (workers=%WORKERS%) >> %LOG%

rem -------------------------------------------- wave 2: I2 / I3 / I4 sweep
rem Each rep MERGES the 7 new cells into its existing wave-1 bank file, and
rem the wave asserts coverage afterwards — a silent no-op now exits non-zero.
%PY% -u scripts\launch_m1_grid.py --wave 2 --reps 250 --workers %WORKERS% --ruleset BRAIN-009 --tag %TAG% >> %RUNS%\recal2_wave2.log 2>&1
if errorlevel 1 goto :wave2fail
echo [%date% %time%] wave 2 done (exit %errorlevel%) >> %LOG%

rem ------------------------------------- wave 3: 1000 extra alpha=0 reps
%PY% -u scripts\launch_m1_grid.py --wave 3 --start 250 --reps 1000 --workers %WORKERS% --ruleset BRAIN-009 --tag %TAG% >> %RUNS%\recal2_wave3.log 2>&1
if errorlevel 1 goto :wave3fail
echo [%date% %time%] wave 3 done (exit %errorlevel%) >> %LOG%

rem ------------------------------------------------ tables on the FROZEN ladder
%PY% -m aegis_brain.calibration.bank --aggregate --tag %TAG% --ruleset %FROZEN% --subset all  >> %RUNS%\recal2_tables.log 2>&1
%PY% -m aegis_brain.calibration.bank --aggregate --tag %TAG% --ruleset %FROZEN% --subset even >> %RUNS%\recal2_tables.log 2>&1
%PY% -m aegis_brain.calibration.bank --aggregate --tag %TAG% --ruleset %FROZEN% --subset odd  >> %RUNS%\recal2_tables.log 2>&1
%PY% -m aegis_brain.calibration.bank --aggregate --tag %TAG% --ruleset BRAIN-008 --subset all >> %RUNS%\recal2_tables.log 2>&1
echo [%date% %time%] tables done (exit %errorlevel%) >> %LOG%

rem ------------------------- sizing ladder + posterior, per design
%PY% -m aegis_brain.calibration.posterior --tag %TAG% --ruleset %FROZEN% --design I1 >> %RUNS%\recal2_stage4.log 2>&1
%PY% -m aegis_brain.calibration.posterior --tag %TAG% --ruleset %FROZEN% --design I2 >> %RUNS%\recal2_stage4.log 2>&1
echo [%date% %time%] posterior + sizing ladder done (exit %errorlevel%) >> %LOG%

rem --------------- SENSITIVITY ONLY: what selection would pick at n=1250
%PY% -m aegis_brain.calibration.select --tag %TAG% --out brain009_selection_n1250.json >> %RUNS%\recal2_select.log 2>&1
echo [%date% %time%] n=1250 selection sensitivity done (exit %errorlevel%) — freeze NOT changed >> %LOG%

%PY% -m aegis_brain.calibration.exhibits --tag %TAG% --ruleset BRAIN-009 --design I1 >> %RUNS%\recal2_stage4.log 2>&1
echo [%date% %time%] exhibits done (exit %errorlevel%) >> %LOG%
echo [%date% %time%] RECAL2 CHAIN COMPLETE >> %LOG%
exit /b 0

:wave2fail
echo [%date% %time%] wave 2 FAILED or incomplete — see recal2_wave2.log (coverage assertion) >> %LOG%
exit /b 3
:wave3fail
echo [%date% %time%] wave 3 FAILED or incomplete — see recal2_wave3.log (coverage assertion) >> %LOG%
exit /b 4
