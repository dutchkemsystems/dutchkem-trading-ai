@echo off
REM =============================================================================
REM Dutchkem Trading AI — Auto Startup (runs via Task Scheduler on login)
REM Starts MT5 Bridge + Cloudflare Tunnel
REM =============================================================================

REM Wait for network
timeout /t 10 /nobreak >NUL

REM Start MT5 Bridge
start "MT5Bridge" /MIN python "C:\DUTCHKEM-TRADING-AI\mt5-bridge\bridge_server.py" 8082

REM Wait for bridge to be ready
timeout /t 5 /nobreak >NUL

REM Start Cloudflare Tunnel
start "CloudflareTunnel" cmd /c "C:\Users\Lenovo\cloudflared.exe tunnel --url http://localhost:8082 --no-autoupdate 2>&1 > C:\DUTCHKEM-TRADING-AI\logs\tunnel.log"

REM Log the tunnel URL after a delay
timeout /t 10 /nobreak >NUL
echo [%date% %time%] Auto-start completed > C:\DUTCHKEM-TRADING-AI\logs\startup.log
