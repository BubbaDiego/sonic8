@echo off
setlocal enabledelayedexpansion

REM ===========================================
REM Sonic8 Launcher (Windows)
REM - Activates venv
REM - Runs Launch Pad from repo root
REM ===========================================

REM --- Paths ---
set "ROOT=%~dp0"
REM Trim trailing backslash if present
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "PY=%ROOT%\.venv\Scripts\python.exe"
set "LOGS=%ROOT%\logs"
set "ENTRY="

if not exist "%LOGS%" mkdir "%LOGS%"

echo [Sonic8] Preparing Python...
if not exist "%PY%" (
  echo [ERROR] venv python not found at "%PY%"
  echo         Create it:  python -m venv .venv ^& .venv\Scripts\pip install -U pip
  exit /b 1
)
echo [Sonic8] Using venv: "%PY%"

REM --- Allow manual override via env var or .env ---
if defined LAUNCHPAD_ENTRY set "ENTRY=%LAUNCHPAD_ENTRY%"

if not defined ENTRY if exist "%ROOT%\.env" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%\.env") do (
    if /I "%%~A"=="LAUNCHPAD_ENTRY" set "ENTRY=%%~B"
  )
)

REM --- Default to launch_pad.py at repo root ---
if not defined ENTRY set "ENTRY=launch_pad.py"

REM Normalize to full path if it's relative
if not exist "%ENTRY%" (
  if exist "%ROOT%\%ENTRY%" set "ENTRY=%ROOT%\%ENTRY%"
)

echo [Sonic8] Launch Pad entrypoint:
echo         %ENTRY%

if not exist "%ENTRY%" (
  echo [ERROR] Could not find Launch Pad at "%ENTRY%"
  exit /b 1
)

REM --- Ensure Python can import backend packages ---
set "PYTHONPATH=%ROOT%;%ROOT%\backend"

REM --- Run LaunchPad from repo root ---
pushd "%ROOT%"
echo [Sonic8] Starting LaunchPad...
"%PY%" "%ENTRY%"
set "RC=%ERRORLEVEL%"
popd

echo [Sonic8] LaunchPad exited with code %RC%
exit /b %RC%
