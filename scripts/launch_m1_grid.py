"""Overnight launcher for the GATE-M1 Stage-3 grid.

Holds ES_SYSTEM_REQUIRED while the grid runs so the machine cannot sleep
mid-grid (display may still sleep). Passes argv through to run_grid.

Usage:  .venv\\Scripts\\python.exe scripts\\launch_m1_grid.py --reps 250 --workers 16
"""

import ctypes
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

if sys.platform == "win32":
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

sys.argv = ["run_grid"] + sys.argv[1:]
runpy.run_module("aegis_brain.calibration.run_grid", run_name="__main__")
