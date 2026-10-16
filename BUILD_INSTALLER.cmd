@echo off
setlocal
cd /d "%~dp0"
echo.
echo  VELOMUX - Windows installer build (Inno Setup 7)
echo  ---------------------------------------------------
echo  This builds a private TEST installer from source.
echo  Your installed FFmpeg will be bundled with the app.
echo  The resulting installer requires no Python on end-user PCs.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_windows.ps1" -UseSystemFFmpeg -Installer
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" (
    echo  Installer build FAILED. Read the error above.
    echo  You can also use the GitHub Windows build workflow.
) else (
    echo  Installer build completed. Check dist\installer.
)
echo.
pause
exit /b %RESULT%
