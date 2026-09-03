@echo off
REM =============================================================================
REM Dutchkem Trading AI — Local Startup Script
REM Starts MT5 Bridge + Cloudflare Tunnel + auto-updates Render MT5_HOST
REM =============================================================================

echo.
echo ============================================
echo  Dutchkem Trading AI — Local Startup
echo ============================================
echo.

REM Check MT5
echo [1/5] Checking MT5 terminal...
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I "terminal64.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: MT5 terminal not running! Start MetaTrader 5 EXNESS first.
    pause
    exit /b 1
)
echo   MT5 terminal is running.

REM Start Bridge
echo [2/5] Starting MT5 Bridge on port 8082...
tasklist /FI "WINDOWTITLE eq MT5Bridge*" 2>NUL | find /I "python" >NUL
if %ERRORLEVEL% EQU 0 (
    echo   Bridge already running.
) else (
    start "MT5Bridge" /MIN python "%~dp0mt5-bridge\bridge_server.py" 8082
    timeout /t 3 /nobreak >NUL
    echo   Bridge started.
)

REM Health check
echo [3/5] Checking bridge health...
curl -s http://localhost:8082/health >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   WARNING: Bridge not responding yet, waiting...
    timeout /t 5 /nobreak >NUL
)
curl -s http://localhost:8082/health
echo.

REM Start Cloudflare Tunnel
echo [4/5] Starting Cloudflare Tunnel...
echo   URL will appear in the cloudflared window.

REM Clear old tunnel log
echo. > "%~dp0..\logs\tunnel.log"

REM Start cloudflared in separate window + capture output to log
start "CloudflareTunnel" cmd /k "C:\Users\Lenovo\cloudflared.exe tunnel --url http://localhost:8082 --no-autoupdate 2>&1 | powershell -Command \"$input | Tee-Object -FilePath '%~dp0..\logs\tunnel.log'\""

REM Wait for tunnel URL to appear in log
echo   Waiting for tunnel URL (up to 30 seconds)...
set TUNNEL_URL=
set WAIT_COUNT=0

:wait_loop
timeout /t 2 /nobreak >NUL
set /a WAIT_COUNT+=1

REM Check log for URL
for /f "delims=" %%L in ('findstr /C:"trycloudflare.com" "%~dp0..\logs\tunnel.log" 2^>NUL') do (
    for %%W in (%%L) do (
        echo %%W | findstr /C:"https://" >NUL 2>&1
        if !ERRORLEVEL! EQU 0 (
            set TUNNEL_URL=%%W
            goto :tunnel_found
        )
    )
)

if %WAIT_COUNT% LSS 15 goto :wait_loop
echo   WARNING: Could not auto-detect tunnel URL.
echo   Check the cloudflared window for the URL.
goto :manual_update

:tunnel_found
REM Clean up URL
set TUNNEL_URL=%TUNNEL_URL:.=%
set TUNNEL_URL=%TUNNEL_URL:,=%

echo.
echo   Tunnel URL: %TUNNEL_URL%
echo.

REM Auto-update Render
echo [5/5] Updating Render MT5_HOST...
python "%~dp0render_update_tunnel.py" "%TUNNEL_URL%"
if %ERRORLEVEL% EQU 0 (
    echo   Render updated and deploying!
) else (
    echo   Auto-update failed.
    goto :manual_update
)
goto :done

:manual_update
echo.
echo   To update Render manually:
echo     1. Copy tunnel URL from the cloudflared window
echo     2. Run: python scripts\render_update_tunnel.py ^<URL^>
echo     OR go to Render dashboard → Environment → MT5_HOST → paste URL
echo.

:done
echo.
echo ============================================
echo  SERVICES RUNNING:
echo    MT5 Bridge:  http://localhost:8082
echo    Tunnel:      See cloudflared window for URL
echo    Health:      http://localhost:8082/health
echo    Render:      MT5_HOST auto-updated
echo.
echo  Keep this script running!
echo ============================================
pause
