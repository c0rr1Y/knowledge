@echo off
setlocal

set "ROOT=%~dp0"

echo ==============================================
echo   Enterprise Knowledge Base - Windows Deploy
echo ==============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node.js 18+.
    pause
    exit /b 1
)

echo [1/4] Installing backend dependencies...
cd /d "%ROOT%backend"
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

if not exist .env (
    echo     WARNING: backend\.env not found. Copy .env.example to .env and set ANTHROPIC_AUTH_TOKEN.
)

echo [2/4] Installing frontend dependencies...
cd /d "%ROOT%frontend"
if not exist node_modules (
    call npm install
)

echo [3/4] Starting backend...
start "KB-Backend" cmd /c "cd /d %ROOT%backend && venv\Scripts\activate.bat && set HF_ENDPOINT=https://hf-mirror.com && uvicorn app.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [4/4] Starting frontend...
start "KB-Frontend" cmd /c "cd /d %ROOT%frontend && npm run dev"

echo.
echo ==============================================
echo   Deploy complete!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000/docs
echo ==============================================
echo.
pause
