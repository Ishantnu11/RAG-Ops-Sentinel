@echo off
:: ============================================================
::  SentinelRAG — Quick Startup Script
::  Gurugram University B.Tech Project 2026
::  Authors: Akshu Grewal · Ishantnu · Anish Singh Rawat
:: ============================================================
title SentinelRAG Launcher

echo.
echo  ============================================================
echo    SentinelRAG — Production RAG Observability Pipeline
echo    Gurugram University B.Tech CSE (AI) -- 2026
echo    Team: Akshu Grewal  Ishantnu  Anish Singh Rawat
echo  ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.10+ first.
    pause & exit /b 1
)

:: Check Ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo  [WARNING] Ollama not detected. Starting it now...
    start "Ollama" cmd /c "ollama serve"
    timeout /t 4 /nobreak >nul
)

:: Install dependencies if needed
if not exist ".deps_installed" (
    echo  [SETUP] Installing Python dependencies...
    pip install -r requirements.txt
    echo. > .deps_installed
    echo  [SETUP] Done.
)

:: Ingest documents if ChromaDB not present
if not exist "chroma_db" (
    echo  [INGEST] ChromaDB not found. Ingesting documents...
    python ingest.py
    echo  [INGEST] Done.
)

echo.
echo  Starting services...
echo.

:: Start Phoenix in background window
start "Phoenix Dashboard" cmd /c "python launch_phoenix.py"
timeout /t 2 /nobreak >nul

:: Start API server in background window
start "SentinelRAG API" cmd /c "python api_server.py"
timeout /t 3 /nobreak >nul

:: Open the Web UI in default browser
echo  [UI] Opening SentinelRAG Dashboard...
start http://localhost:3000

:: Start UI file server
echo  [UI] Serving frontend at http://localhost:3000
start "SentinelRAG UI" cmd /c "python -m http.server 3000 --directory ui"

echo.
echo  ============================================================
echo    SentinelRAG is running!
echo.
echo    Dashboard : http://localhost:3000
echo    API       : http://localhost:8000
echo    API Docs  : http://localhost:8000/docs
echo    Phoenix   : http://localhost:6006
echo  ============================================================
echo.
echo  Press any key to stop all services...
pause >nul

:: Kill all background processes on exit
taskkill /f /im python.exe >nul 2>&1
echo  [STOP] All services stopped.
