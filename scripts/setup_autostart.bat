@echo off
REM =============================================================================
REM Dutchkem Trading AI — Setup Auto-Start (Run as Administrator!)
REM Registers Windows Task Scheduler job to start bridge + tunnel on login
REM =============================================================================

echo.
echo ============================================
echo  SETUP: Auto-Start on Login
echo ============================================
echo.
echo  This will register a Windows Task Scheduler job
echo  that starts MT5 Bridge + Cloudflare Tunnel
echo  every time you log in.
echo.

REM Check if running as admin
net session >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Must run as Administrator!
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

echo [1/2] Removing old task if exists...
schtasks /delete /tn "DutchkemAutoStart" /f >NUL 2>&1

echo [2/2] Creating new task...
schtasks /create /tn "DutchkemAutoStart" /tr "C:\DUTCHKEM-TRADING-AI\scripts\auto_start.bat" /sc onlogon /rl highest /f /delay 0000:15

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo  SUCCESS! Task Scheduler job registered.
    echo ============================================
    echo  Task name:  DutchkemAutoStart
    echo  Trigger:    On every login (15s delay)
    echo  Action:     Runs auto_start.bat
    echo.
    echo  Bridge + tunnel will start automatically
    echo  next time you log into Windows.
    echo ============================================
) else (
    echo.
    echo ERROR: Failed to create task. Try running as Administrator.
)

pause
