@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -m taskgraph.gui %*
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3 is required. Install Python from https://www.python.org/downloads/
        echo Enable Python and Tcl/Tk in the installer, then run this file again.
        pause
        exit /b 1
    )
    python -m taskgraph.gui %*
)
if errorlevel 1 pause
