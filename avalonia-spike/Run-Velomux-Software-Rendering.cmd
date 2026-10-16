@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0Velomux.Avalonia.Spike.exe" (
  echo Missing Velomux.Avalonia.Spike.exe. Extract the complete ZIP first.
  pause
  exit /b 2
)
echo Starting Velomux with software rendering for Windows compatibility testing...
start "" "%~dp0Velomux.Avalonia.Spike.exe" --software-rendering
echo If the window still does not appear, check:
echo %LOCALAPPDATA%\Velomux\Logs\avalonia-startup.log
pause
