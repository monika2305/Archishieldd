@echo off
title ArchiShield + n8n Launcher
echo ===================================================
echo   Starting ArchiShield + n8n Platform Ecosystem
echo ===================================================
echo.

echo [1/2] Launching FastAPI Backend on Port 8001...
start "ArchiShield Backend (8001)" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload --port 8001"

echo [2/2] Launching React/Vite Frontend on Port 5174...
start "ArchiShield Frontend (5174)" cmd /k "cd /d %~dp0frontend && npm run dev -- --port 5174"

echo.
echo ===================================================
echo   ArchiShield Services Running:
echo   * Web App:         http://localhost:5174
echo   * Local Backend:   http://localhost:8001
echo   * Public Tunnel:   https://allowance-spending-surveillance-analysts.trycloudflare.com
echo   * n8n Cloud:       https://architechs.app.n8n.cloud
echo ===================================================
echo.
pause
