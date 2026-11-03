@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "CLEAN=%ROOT%..\kb-clean"
set "ZIP=%ROOT%..\kb-deploy.zip"

echo ==============================================
echo   打包纯净版本项目（排除本地生成文件）
echo ==============================================
echo.

if exist "%CLEAN%" rmdir /s /q "%CLEAN%"
if exist "%ZIP%" del /q "%ZIP%"

echo [1/2] 复制源码到干净目录...
robocopy "%ROOT%" "%CLEAN%" /E /XD venv node_modules __pycache__ .git .idea .vscode data dist /XF *.pyc .env >nul 2>&1

echo [2/2] 压缩为 zip...
powershell -NoProfile -Command "Compress-Archive -Path '%CLEAN%' -DestinationPath '%ZIP%' -Force"

echo.
echo 打包完成: %ZIP%
echo 解压到新机器后，配置 backend\.env 并运行 deploy.bat 即可。
echo.
pause
