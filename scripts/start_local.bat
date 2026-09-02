@echo off
REM =============================================================================
REM Dutchkem Trading AI — Local Startup Script
REM Starts MT5 Bridge + Cloudflare Tunnel for Render connectivity
REM =============================================================================

echo.
echo ============================================
echo  Dutchkem Trading AI — Local Startup
echo ============================================
echo.

REM Check MT5
echo [1/4] Checking MT5 terminal...
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I "terminal64.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: MT5 terminal not running! Start MetaTrader 5 EXNESS first.
    pause
    exit /b 1
)
echo   MT5 terminal is running.

REM Start Bridge
echo [2/4] Starting MT5 Bridge on port 8082...
tasklist /FI "WINDOWTITLE eq MT5Bridge*" 2>NUL | find /I "python" >NUL
if %ERRORLEVEL% EQU 0 (
    echo   Bridge already running.
) else (
    start "MT5Bridge" /MIN python "%~dp0mt5-bridge\bridge_server.py" 8082
    timeout /t 3 /nobreak >NUL
    echo   Bridge started.
)

REM Health check
echo [3/4] Checking bridge health...
curl -s http://localhost:8082/health >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   WARNING: Bridge not responding yet, waiting...
    timeout /t 5 /nobreak >NUL
)
curl -s http://localhost:8082/health
echo.

REM Start Cloudflare Tunnel
echo [4/4] Starting Cloudflare Tunnel...
echo   NOTE: URL will be printed in the cloudflared window.
echo   Copy the URL and set it as MT5_HOST on Render.
echo.
start "CloudflareTunnel" cmd /c "C:\Users\Lenovo\cloudflared.exe tunnel --url http://localhost:8082 --no-autoupdate"

echo.
echo ============================================
echo  SERVICES RUNNING:
echo    MT5 Bridge:  http://localhost:8082
echo    Tunnel:      See cloudflared window for URL
echo    Health:      http://localhost:8082/health
echo.
echo  Render will connect to the tunnel URL.
echo  Keep this script running!
echo ============================================
pause
