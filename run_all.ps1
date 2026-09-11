# ArchiShield + n8n One-Click PowerShell Launcher
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   Starting ArchiShield + n8n Platform Ecosystem" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$root = $PSScriptRoot

Write-Host "`n[1/2] Launching FastAPI Backend on Port 8001..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; python -m uvicorn main:app --reload --port 8001"

Write-Host "[2/2] Launching React/Vite Frontend on Port 5174..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev -- --port 5174"

Write-Host "`n===================================================" -ForegroundColor Cyan
Write-Host "   ArchiShield Services Running:" -ForegroundColor Cyan
Write-Host "   * Web App:         http://localhost:5174" -ForegroundColor White
Write-Host "   * Local Backend:   http://localhost:8001" -ForegroundColor White
Write-Host "   * Public Tunnel:   https://allowance-spending-surveillance-analysts.trycloudflare.com" -ForegroundColor White
Write-Host "   * n8n Cloud:       https://architechs.app.n8n.cloud" -ForegroundColor White
Write-Host "===================================================" -ForegroundColor Cyan
