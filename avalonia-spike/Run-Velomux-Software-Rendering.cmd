@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0Velomux.exe" (
  echo Velomux.exe is missing. Extract the entire ZIP or install the setup package.
  pause
  exit /b 2
)
echo Starting Velomux using the software-only graphics backend...
start "" "%~dp0Velomux.exe" --software-rendering
echo Diagnostic log: %LOCALAPPDATA%\Velomux\Logs\avalonia-startup.log
