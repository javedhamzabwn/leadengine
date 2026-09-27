@echo off
title LeadEngine — Run Both Frontend + Backend
cd /d D:\wsl-data

echo.
echo ==========================================
echo  Starting LeadEngine Services...
echo ==========================================
echo.

:: --- Start Backend in background ---
echo Starting Backend (FastAPI) in background...
cd /d D:\wsl-data
/c/Users/Javed Hamza/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > backend.log 2>&1 &
set BACKEND_PID=%echo%
timeout /t 2 /nobreak >nul

:: --- Start Frontend in separate CMD window ---
echo Starting Frontend (Next.js) in new window...
start "" cmd /k "cd /d D:\wsl-data\frontend && npm run dev"

echo.
echo Backend PID=%BACKEND_PID% running on http://127.0.0.1:8000/api/search
echo Frontend opening on http://localhost:3000
echo.
echo Press any key to continue...
pause >nul

echo.
echo LeadEngine is now running.
echo Open your browser to: http://localhost:3000
echo The SearchPage will auto-fetch from the backend.
echo.
pause