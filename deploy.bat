@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"

echo ==============================================
echo   企业知识库问答系统 - Windows 一键部署
echo ==============================================
echo.

:: 检查环境（缺失则提示）
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+ 并勾选 "Add to PATH"
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

:: 后端
echo [1/4] 安装后端依赖...
cd /d "%ROOT%backend"
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

if not exist .env (
    echo    警告: 未找到 backend\.env，请复制 .env.example 并填入 ANTHROPIC_AUTH_TOKEN
)

:: 前端
echo [2/4] 安装前端依赖...
cd /d "%ROOT%frontend"
if not exist node_modules (
    call npm install
)

:: 启动后端
echo [3/4] 启动后端...
start "KB-Backend" cmd /c "cd /d %ROOT%backend && venv\Scripts\activate.bat && set HF_ENDPOINT=https://hf-mirror.com && uvicorn app.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

:: 启动前端
echo [4/4] 启动前端...
start "KB-Frontend" cmd /c "cd /d %ROOT%frontend && npm run dev"

echo.
echo ==============================================
echo   部署完成！
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000/docs
echo ==============================================
echo.
pause
