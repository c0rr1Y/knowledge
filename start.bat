@echo off
echo ======================================
echo   Enterprise RAG - Knowledge Base
echo ======================================
echo.

set "ROOT=%~dp0"

echo [Backend] Starting on port 8000...
start "RAG-Backend" cmd /c "cd /d %ROOT%backend && venv\Scripts\activate && set HF_ENDPOINT=https://hf-mirror.com && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [Frontend] Starting on port 5173...
start "RAG-Frontend" cmd /c "cd /d %ROOT%frontend && npm run dev"

echo.
echo ======================================
echo   Backend  http://localhost:8000/docs
echo   Frontend http://localhost:5173
echo ======================================
echo.
pause
