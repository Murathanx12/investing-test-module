"""Overnight launcher for the GATE-M1 Stage-3 grid.

Holds ES_SYSTEM_REQUIRED while the grid runs so the machine cannot sleep
mid-grid (display may still sleep). Passes argv through to run_grid.

NOTE: must import run_grid and call main() under the __main__ guard —
runpy.run_module(run_name="__main__") breaks ProcessPoolExecutor's spawn
bootstrap on Windows (_check_not_importing_main).

Usage:  .venv\\Scripts\\python.exe scripts\\launch_m1_grid.py --wave 1 --reps 250 --workers 15
"""

import ctypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

if __name__ == "__main__":
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    from aegis_brain.calibration.run_grid import main
    sys.argv = ["run_grid"] + sys.argv[1:]
    main()
