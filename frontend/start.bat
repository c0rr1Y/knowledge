@echo off
echo ========================================
echo   企业知识库 RAG 系统 - 前端启动
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Installing dependencies...
call npm install

echo.
echo [2/2] Starting dev server at http://localhost:5173
echo.

call npm run dev
