@echo off
setlocal
cd /d "%~dp0"
echo Velomux Avalonia startup diagnostics
echo -----------------------------------
echo Launching the Windows evaluation executable...
echo.
if not exist "%~dp0Velomux.Avalonia.Spike.exe" (
  echo ERROR: The executable was not found alongside this diagnostic script.
  echo Please extract the complete ZIP before running.
  pause
  exit /b 2
)
"%~dp0Velomux.Avalonia.Spike.exe"
set "RESULT=%ERRORLEVEL%"
echo.
echo Velomux exit code: %RESULT%
echo.
set "LOGFILE=%LOCALAPPDATA%\Velomux\Logs\avalonia-startup.log"
if exist "%LOGFILE%" (
  echo Startup log: "%LOGFILE%"
  echo.
  type "%LOGFILE%"
) else (
  echo No managed startup log exists. A failure before managed code started
  echo may be recorded in Windows Event Viewer ^> Windows Logs ^> Application.
)
echo.
echo Copy the error text if Velomux does not appear. Do not publish personal file paths.
pause
exit /b %RESULT%
