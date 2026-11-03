@echo off
echo ========================================
echo   企业知识库 RAG 系统 - 后端启动
echo ========================================
echo.

cd /d "%~dp0"

:: Check if venv exists
if not exist "venv\" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/3] Installing dependencies...
pip install -r requirements.txt -q

echo.
echo Starting server at http://localhost:8000
echo API docs at http://localhost:8000/docs
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
