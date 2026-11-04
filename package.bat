@echo off
setlocal

set "ROOT=%~dp0"
set "CLEAN=%ROOT%..\kb-clean"
set "ZIP=%ROOT%..\kb-deploy.zip"

echo ==============================================
echo   Package clean project (exclude local files)
echo ==============================================
echo.

if exist "%CLEAN%" rmdir /s /q "%CLEAN%"
if exist "%ZIP%" del /q "%ZIP%"

echo [1/2] Copying source files...
robocopy "%ROOT%" "%CLEAN%" /E /XD venv node_modules __pycache__ .git .idea .vscode data dist /XF *.pyc .env >nul 2>&1

echo [2/2] Compressing to zip...
powershell -NoProfile -Command "Compress-Archive -Path '%CLEAN%' -DestinationPath '%ZIP%' -Force"

echo.
echo Done: %ZIP%
echo Extract on new machine, configure backend\.env, then run deploy.bat
echo.
pause
