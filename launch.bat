@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Sonic5 — Launch Pad

REM --- Always run from this file’s folder (so shortcuts work) ---
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

echo.
echo [Sonic5] Preparing Python...

REM --- Prefer project venv if present; otherwise fall back to system Python ---
set "PYEXE=%BASE_DIR%.venv\Scripts\python.exe"
if exist "%PYEXE%" (
  echo [Sonic5] Using venv: "%PYEXE%"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python not found and no venv present at .venv\Scripts\python.exe
    echo        Install Python 3.x or create the venv:  python -m venv .venv
    pause
    exit /b 1
  )
  for /f "usebackq delims=" %%P in (`where python`) do (
    set "PYEXE=%%P"
    goto :found_python
  )
  :found_python
  echo [Sonic5] Using system Python: "%PYEXE%"
)

REM --- Pick the first entrypoint that exists (adjust list if yours differs) ---
set "ENTRY="
call :pick_entry ENTRY ^
  "backend\apps\launch_pad\main.py" ^
  "backend\launch_pad\main.py" ^
  "backend\launch_pad.py" ^
  "backend\core\launch_pad\main.py" ^
  "backend\apps\launchpad\main.py"

if not defined ENTRY (
  echo.
  echo [ERROR] Could not find a Launch Pad entrypoint.
  echo         Looked for:
  echo           backend\apps\launch_pad\main.py
  echo           backend\launch_pad\main.py
  echo           backend\launch_pad.py
  echo           backend\core\launch_pad\main.py
  echo           backend\apps\launchpad\main.py
  echo.
  echo Tip: Edit launch.bat and replace the candidate list with your actual path.
  pause
  exit /b 2
)

echo.
echo [Sonic5] Starting Launch Pad: "%ENTRY%"
echo.

REM --- If your Launch Pad is an ASGI app (FastAPI), you can instead run uvicorn:
REM set "APP_MODULE=backend.apps.launch_pad.app:app"
REM "%PYEXE%" -m uvicorn "%APP_MODULE%" --host 127.0.0.1 --port 8000
REM goto :done

"%PYEXE%" "%ENTRY%"
set "RC=%ERRORLEVEL%"

:done
echo.
if "%RC%"=="0" (
  echo [Sonic5] Launch Pad exited normally.
) else (
  echo [Sonic5] Launch Pad exited with code %RC%.
)
echo.
pause
exit /b %RC%

REM ------------ helpers -------------
:pick_entry
REM %1=outVar, rest=candidates relative to BASE_DIR
setlocal EnableDelayedExpansion
set "OUTVAR=%~1"
set "%OUTVAR%="
shift
:pe_loop
if "%~1"=="" goto :pe_end
if exist "%BASE_DIR%%~1" (
  for %%Z in ("%~1") do (
    endlocal & set "%OUTVAR%=%%~fZ" & goto :eof
  )
)
shift
goto :pe_loop
:pe_end
endlocal & goto :eof
