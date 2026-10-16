@echo off
setlocal
cd /d "%~dp0"
echo Velomux Avalonia media workstation - startup diagnostics
echo -------------------------------------------------------
if not exist "%~dp0Velomux.exe" (
  echo ERROR: Velomux.exe was not found. Extract the entire ZIP or install the setup package.
  pause
  exit /b 2
)
echo Launching Velomux...
"%~dp0Velomux.exe"
set "RESULT=%ERRORLEVEL%"
echo.
echo Application exit code: %RESULT%
set "LOGFILE=%LOCALAPPDATA%\Velomux\Logs\avalonia-startup.log"
if exist "%LOGFILE%" (
  echo Startup log: "%LOGFILE%"
  echo.
  type "%LOGFILE%"
) else (
  echo No application log was produced. Check Windows Event Viewer ^> Windows Logs ^> Application.
)
echo.
echo Do not share personal file paths or media filenames from this log.
pause
exit /b %RESULT%
