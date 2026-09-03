@echo off
REM =============================================================================
REM Dutchkem Trading AI — Update Render MT5_HOST
REM Uses Python script to update via Render API
REM =============================================================================

echo.
echo ============================================
echo  Update Render MT5_HOST
echo ============================================
echo.
echo  This will update MT5_HOST on Render via API
echo  and trigger a deploy.
echo.

set /p NEW_URL="Enter new tunnel URL: "

if "%NEW_URL%"=="" (
    echo ERROR: No URL entered.
    pause
    exit /b 1
)

python "%~dp0render_update_tunnel.py" "%NEW_URL%"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Auto-update failed. You can also update manually:
    echo   1. Go to https://dashboard.render.com/
    echo   2. Click dutchkem-backend
    echo   3. Click Environment tab
    echo   4. Find MT5_HOST and change it to: %NEW_URL%
    echo   5. Save — service will auto-redeploy
)

pause
