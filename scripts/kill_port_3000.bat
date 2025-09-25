@echo off
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
  echo Killing PID %%a on :3000
  taskkill /F /PID %%a >nul 2>&1
)
echo Done.
