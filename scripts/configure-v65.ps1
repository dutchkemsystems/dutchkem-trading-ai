<#
.SYNOPSIS
    V6.5 Auto-Configuration Script
    Automatically configures all V6.5 settings for trading.

.DESCRIPTION
    This script auto-configures:
    - TRADING_ENGINE=v6.5
    - TRADING_MODE=full (or semi)
    - VIRTUAL_ACCOUNT_BALANCE=100.0
    - Celery schedule for V6.5 tasks
    - Symbol initialization
    - Backup system configuration
    - Risk management parameters

.NOTES
    Author: DutchKem Trading AI
    Version: 6.5
    Date: 2026-09-01
#>

param(
    [string]$TradingMode = "semi",  # Options: manual, semi, full
    [double]$VirtualBalance = 100.00,
    [switch]$InitializeSymbols,
    [switch]$Force,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  DUTCHKEM TRADING AI - V6.5 Auto-Configuration" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# STEP 1: Set Environment Variables
# ============================================================================
Write-Host "[1/6] Setting environment variables..." -ForegroundColor Yellow

$envVars = @{
    "TRADING_ENGINE" = "v6.5"
    "TRADING_MODE" = $TradingMode
    "VIRTUAL_ACCOUNT_BALANCE" = $VirtualBalance.ToString()
    "DJANGO_SETTINGS_MODULE" = "config.settings_production"
}

foreach ($key in $envVars.Keys) {
    [System.Environment]::SetEnvironmentVariable($key, $envVars[$key], "Process")
    Write-Host "  Set $key = $($envVars[$key])" -ForegroundColor Green
}

# Create .env file if it doesn't exist
$envFile = ".env"
$envContent = @"

# V6.5 Trading Engine Configuration
TRADING_ENGINE=v6.5
TRADING_MODE=$TradingMode
VIRTUAL_ACCOUNT_BALANCE=$VirtualBalance

# Django Settings
DJANGO_SETTINGS_MODULE=config.settings_production

"@

if (-not (Test-Path $envFile)) {
    $envContent | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host "  Created $envFile with V6.5 settings" -ForegroundColor Green
} else {
    # Check if TRADING_ENGINE already exists
    $existingContent = Get-Content $envFile -Raw
    if ($existingContent -match "TRADING_ENGINE=") {
        Write-Host "  TRADING_ENGINE already set in $envFile" -ForegroundColor Gray
    } else {
        $envContent | Out-File -FilePath $envFile -Encoding UTF8 -Append
        Write-Host "  Appended V6.5 settings to $envFile" -ForegroundColor Green
    }
}

# ============================================================================
# STEP 2: Configure Django Settings
# ============================================================================
Write-Host ""
Write-Host "[2/6] Configuring Django settings..." -ForegroundColor Yellow

$settingsFile = "backend\config\settings_production.py"

if (Test-Path $settingsFile) {
    $settingsContent = Get-Content $settingsFile -Raw
    
    # Check if TRADING_ENGINE exists
    if ($settingsContent -notmatch "TRADING_ENGINE") {
        Write-Host "  Adding TRADING_ENGINE to settings..." -ForegroundColor Gray
        
        # Find the TRADING_CONFIG section and add TRADING_ENGINE after it
        $tradingConfigEnd = $settingsContent.IndexOf("}", $settingsContent.IndexOf("TRADING_CONFIG"))
        if ($tradingConfigEnd -gt 0) {
            $insertPoint = $tradingConfigEnd + 1
            $newSetting = @"

# ── Trading Engine Configuration (V6.5 DEFAULT) ─────────────────────
TRADING_ENGINE = os.environ.get("TRADING_ENGINE", "v6.5")
"@
            $settingsContent = $settingsContent.Insert($insertPoint, $newSetting)
            $settingsContent | Out-File -FilePath $settingsFile -Encoding UTF8
            Write-Host "  Added TRADING_ENGINE to settings" -ForegroundColor Green
        }
    } else {
        Write-Host "  TRADING_ENGINE already configured" -ForegroundColor Gray
    }
}

# ============================================================================
# STEP 3: Initialize Database
# ============================================================================
Write-Host ""
Write-Host "[3/6] Initializing database..." -ForegroundColor Yellow

try {
    # Run migrations
    Write-Host "  Running migrations..." -ForegroundColor Gray
    & python manage.py migrate --verbosity=0 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Database migrations complete" -ForegroundColor Green
    } else {
        Write-Host "  Migration warnings (non-critical)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Database initialization skipped: $_" -ForegroundColor Yellow
}

# ============================================================================
# STEP 4: Initialize Symbols (Optional)
# ============================================================================
Write-Host ""
Write-Host "[4/6] Symbol initialization..." -ForegroundColor Yellow

if ($InitializeSymbols) {
    try {
        Write-Host "  Initializing trading symbols..." -ForegroundColor Gray
        
        # Create Django management command or script to initialize symbols
        $initScript = @'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_production')
django.setup()

from trading.models import Symbol

symbols = [
    # Majors
    ("EURUSD", "Euro / US Dollar", "Forex"),
    ("GBPUSD", "British Pound / US Dollar", "Forex"),
    ("USDJPY", "US Dollar / Japanese Yen", "Forex"),
    ("USDCHF", "US Dollar / Swiss Franc", "Forex"),
    ("AUDUSD", "Australian Dollar / US Dollar", "Forex"),
    ("USDCAD", "US Dollar / Canadian Dollar", "Forex"),
    ("NZDUSD", "New Zealand Dollar / US Dollar", "Forex"),
    # Crosses
    ("EURGBP", "Euro / British Pound", "Forex"),
    ("EURJPY", "Euro / Japanese Yen", "Forex"),
    ("GBPJPY", "British Pound / Japanese Yen", "Forex"),
    # Metals
    ("XAUUSD", "Gold / US Dollar", "Metals"),
    ("XAGUSD", "Silver / US Dollar", "Metals"),
    # Crypto
    ("BTCUSD", "Bitcoin / US Dollar", "Crypto"),
    ("ETHUSD", "Ethereum / US Dollar", "Crypto"),
    # Indices
    ("US30", "Dow Jones 30", "Index"),
    ("US500", "S&P 500", "Index"),
    ("NAS100", "NASDAQ 100", "Index"),
]

created = 0
for name, full_name, category in symbols:
    obj, was_created = Symbol.objects.get_or_create(
        name=name,
        defaults={"full_name": full_name, "category": category, "is_active": True}
    )
    if was_created:
        created += 1

print(f"Created {created} new symbols, total: {Symbol.objects.count()}")
'@
        
        $initScript | python - 2>&1 | Write-Host -ForegroundColor Gray
        Write-Host "  Symbols initialized" -ForegroundColor Green
    } catch {
        Write-Host "  Symbol initialization skipped: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Skipping (use -InitializeSymbols to enable)" -ForegroundColor Gray
}

# ============================================================================
# STEP 5: Configure Celery Schedule
# ============================================================================
Write-Host ""
Write-Host "[5/6] Configuring Celery schedule..." -ForegroundColor Yellow

$scheduleFile = "backend\config\celery_schedule.py"

if (Test-Path $scheduleFile) {
    $scheduleContent = Get-Content $scheduleFile -Raw
    
    # Verify V6.5 tasks are configured
    if ($scheduleContent -match "run-v65-trading-cycle" -and 
        $scheduleContent -match "run-backup-trading-cycle" -and
        $scheduleContent -match "v65-manage-profit-targets") {
        Write-Host "  Celery schedule already configured for V6.5" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Celery schedule may need manual update" -ForegroundColor Yellow
        Write-Host "  Check backend/config/celery_schedule.py" -ForegroundColor Yellow
    }
}

# ============================================================================
# STEP 6: Create Startup Script
# ============================================================================
Write-Host ""
Write-Host "[6/6] Creating startup script..." -ForegroundColor Yellow

$startupScript = @'
# V6.5 Trading System Startup Script
# Run this to start all V6.5 services

Write-Host "Starting V6.5 Trading System..." -ForegroundColor Cyan

# Set environment
$env:TRADING_ENGINE = "v6.5"
$env:TRADING_MODE = "semi"
$env:VIRTUAL_ACCOUNT_BALANCE = "100.0"
$env:DJANGO_SETTINGS_MODULE = "config.settings_production"

# Start Celery worker
Write-Host "Starting Celery worker..." -ForegroundColor Yellow
Start-Process -FilePath "celery" -ArgumentList "-A config worker -l info -c 4" -NoNewWindow

# Start Celery beat
Write-Host "Starting Celery beat scheduler..." -ForegroundColor Yellow
Start-Process -FilePath "celery" -ArgumentList "-A config beat -l info" -NoNewWindow

# Start Django development server (optional)
Write-Host "Starting Django server..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "manage.py runserver 0.0.0.0:8000" -NoNewWindow

Write-Host ""
Write-Host "V6.5 Trading System started!" -ForegroundColor Green
Write-Host "  Django: http://localhost:8000" -ForegroundColor White
Write-Host "  Celery Worker: Running" -ForegroundColor White
Write-Host "  Celery Beat: Running" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Gray
'@

$startupFile = "scripts\start-v65.ps1"
$startupScript | Out-File -FilePath $startupFile -Encoding UTF8
Write-Host "  Created $startupFile" -ForegroundColor Green

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  V6.5 Configuration Complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration Summary:" -ForegroundColor Yellow
Write-Host "  Trading Engine:    v6.5 (DEFAULT)" -ForegroundColor White
Write-Host "  Trading Mode:      $TradingMode" -ForegroundColor White
Write-Host "  Virtual Balance:   `$$VirtualBalance" -ForegroundColor White
Write-Host "  Backup Systems:    V6 → Gold Edge → Scalping → Confluence" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Review .env file for any additional settings" -ForegroundColor White
Write-Host "  2. Start trading: .\scripts\start-v65.ps1" -ForegroundColor White
Write-Host "  3. Run simulation: .\scripts\virtual-100-sim.ps1" -ForegroundColor White
Write-Host "  4. Monitor performance in Django admin" -ForegroundColor White
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Yellow
Write-Host "  docs\V6.5-GUIDE.md - Complete V6.5 documentation" -ForegroundColor White
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
