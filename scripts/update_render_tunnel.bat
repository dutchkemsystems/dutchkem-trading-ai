@echo off
REM =============================================================================
REM Dutchkem Trading AI — Update Render MT5_HOST
REM Reads the new tunnel URL from cloudflared window and updates Render env var
REM =============================================================================

echo.
echo ============================================
echo  Update Render MT5_HOST
echo ============================================
echo.
echo  After starting the tunnel, the URL appears in the cloudflared window.
echo  Copy the full URL (e.g., https://xxxx-xx-xx-xx.trycloudflare.com)
echo  and paste it below.
echo.

set /p NEW_URL="Enter new tunnel URL: "

if "%NEW_URL%"=="" (
    echo ERROR: No URL entered.
    pause
    exit /b 1
)

echo.
echo New MT5_HOST: %NEW_URL%
echo.
echo You need to update this on Render:
echo   1. Go to https://dashboard.render.com/
echo   2. Click dutchkem-backend
echo   3. Click Environment tab
echo   4. Find MT5_HOST and change it to: %NEW_URL%
echo   5. Save — service will auto-redeploy
echo.
pause
