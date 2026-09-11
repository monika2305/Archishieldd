@echo off
title ArchiShield Backend Server
echo Starting ArchiShield FastAPI Backend on http://localhost:8001...
cd /d %~dp0backend
python -m uvicorn main:app --reload --port 8001
pause
