@echo off
setlocal
pushd C:\sonic7
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=C:\sonic7;%PYTHONPATH%
REM Prefer JSON config; if missing, fallback to Helius env
if not exist gmx_solana_console.json (
  if "%SOL_RPC%"=="" set SOL_RPC=https://mainnet.helius-rpc.com/?api-key=a8809bee-20ba-48e9-b841-0bd2bafd60b9
)
python -m backend.core.gmx_solana_core.console.menu_console
set EXITCODE=%ERRORLEVEL%
popd
exit /b %EXITCODE%
