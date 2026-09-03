@echo off
REM =============================================================================
REM Dutchkem Trading AI — Auto Startup (runs via Task Scheduler on login)
REM Starts MT5 Bridge + Cloudflare Tunnel + updates Render MT5_HOST
REM =============================================================================

REM Wait for network
timeout /t 10 /nobreak >NUL

REM Ensure logs directory exists
if not exist "C:\DUTCHKEM-TRADING-AI\logs" mkdir "C:\DUTCHKEM-TRADING-AI\logs"

REM Start MT5 Bridge
start "MT5Bridge" /MIN python "C:\DUTCHKEM-TRADING-AI\mt5-bridge\bridge_server.py" 8082

REM Wait for bridge to be ready
timeout /t 5 /nobreak >NUL

REM Clear old tunnel log
echo. > C:\DUTCHKEM-TRADING-AI\logs\tunnel.log

REM Start Cloudflare Tunnel with output captured to log
start "CloudflareTunnel" cmd /c "C:\Users\Lenovo\cloudflared.exe tunnel --url http://localhost:8082 --no-autoupdate 2>&1 | powershell -Command \"$input | Tee-Object -FilePath 'C:\DUTCHKEM-TRADING-AI\logs\tunnel.log'\""

REM Wait for tunnel URL to appear
set TUNNEL_URL=
set WAIT_COUNT=0

:wait_loop
timeout /t 3 /nobreak >NUL
set /a WAIT_COUNT+=1

for /f "delims=" %%L in ('findstr /C:"trycloudflare.com" "C:\DUTCHKEM-TRADING-AI\logs\tunnel.log" 2^>NUL') do (
    for %%W in (%%L) do (
        echo %%W | findstr /C:"https://" >NUL 2>&1
        if !ERRORLEVEL! EQU 0 (
            set TUNNEL_URL=%%W
            goto :tunnel_found
        )
    )
)

if %WAIT_COUNT% LSS 10 goto :wait_loop
goto :log_only

:tunnel_found
set TUNNEL_URL=%TUNNEL_URL:.=%
set TUNNEL_URL=%TUNNEL_URL:,=%

REM Auto-update Render
python "C:\DUTCHKEM-TRADING-AI\scripts\render_update_tunnel.py" "%TUNNEL_URL%"

:log_only
echo [%date% %time%] Auto-start completed. Tunnel: %TUNNEL_URL% >> C:\DUTCHKEM-TRADING-AI\logs\startup.log
