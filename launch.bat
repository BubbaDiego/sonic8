@echo off
setlocal enabledelayedexpansion

REM ===========================================
REM Sonic5 Launcher (Windows)
REM - Activates venv
REM - Finds Launch Pad entrypoint
REM - Runs backend
REM ===========================================

REM --- Paths ---
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"
set "BACKEND=%ROOT%backend"
set "LOGS=%ROOT%logs"

if not exist "%LOGS%" mkdir "%LOGS%"

echo [Sonic5] Preparing Python...
if not exist "%PY%" (
  echo [ERROR] venv python not found at "%PY%"
  echo         Create it:  python -m venv .venv ^& .venv\Scripts\pip install -U pip
  exit /b 1
)
echo [Sonic5] Using venv: "%PY%"

REM --- Allow manual override via env var or .env file ---
REM 1) Environment variable LAUNCHPAD_ENTRY takes highest precedence
REM 2) If .env has LAUNCHPAD_ENTRY=..., we will read it
set "ENTRY="
if defined LAUNCHPAD_ENTRY set "ENTRY=%LAUNCHPAD_ENTRY%"

if not defined ENTRY (
  if exist "%ROOT%.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%.env") do (
      if /I "%%~A"=="LAUNCHPAD_ENTRY" set "ENTRY=%%~B"
    )
  )
)

REM --- Candidate list (relative to repo root) ---
set "CANDIDATES=launch_pad.py;
backend\sonic_backend_app.py;
backend\apps\launch_pad\main.py;
backend\apps\launchpad\main.py;
backend\launch_pad\main.py;
backend\core\launch_pad\main.py;
backend\launch_pad.py;
backend\apps\launch_pad\app.py;
backend\apps\launchpad\app.py"

REM If no override, probe candidates
if not defined ENTRY (
  for %%P in (%CANDIDATES%) do (
    if exist "%ROOT%%%P" (
      set "ENTRY=%ROOT%%%P"
      goto :ENTRY_FOUND
    )
  )
)

REM Fallback: dynamic search for "*launch*pad*\main.py" anywhere under backend
if not defined ENTRY (
  for /f "delims=" %%F in ('dir /b /s "%BACKEND%\*launch*pad*\main.py" 2^>nul') do (
    set "ENTRY=%%F"
    goto :ENTRY_FOUND
  )
)

REM Last-ditch: accept a single main.py that imports/defines Launch Pad
if not defined ENTRY (
  for /f "delims=" %%F in ('dir /b /s "%BACKEND%\main.py" 2^>nul') do (
    set "ENTRY=%%F"
    goto :ENTRY_FOUND
  )
)

echo.
echo [ERROR] Could not find a Launch Pad entrypoint.
echo         Looked for:
for %%P in (%CANDIDATES%) do echo           %%P
echo.
echo Tip A: Set LAUNCHPAD_ENTRY to an absolute or relative path, e.g.:
echo        set LAUNCHPAD_ENTRY=backend\apps\launch_pad\main.py
echo Tip B: Put the same line in .env at repo root.
echo.
pause
exit /b 1

:ENTRY_FOUND
echo [Sonic5] Launch Pad entrypoint:
echo         %ENTRY%

REM --- Ensure Python can import backend packages ---
set "PYTHONPATH=%BACKEND%;%ROOT%"

REM --- Run it ---
echo [Sonic5] Starting backend...
"%PY%" "%ENTRY%"
set "RC=%ERRORLEVEL%"
echo [Sonic5] Backend exited with code %RC%
exit /b %RC%
