# =============================================================================
# Dutchkem Trading AI — Quick Start (Local Production)
# =============================================================================
# Run this script to start the complete system locally with Docker.
#
# Prerequisites:
#   - Docker Desktop installed and running
#   - MetaTrader 5 terminal running with algo trading enabled
# =============================================================================

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  DutchKEM Trading AI — Quick Start" -ForegroundColor Cyan
Write-Host "  MT5 Account: 161704951" -ForegroundColor Cyan
Write-Host "  Server: Exness-MT5Real21" -ForegroundColor Cyan
Write-Host "  Trading Mode: FULL (Automatic)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker is running
Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
try {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker not running" }
    Write-Host "  Docker is running" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Docker is not running!" -ForegroundColor Red
    Write-Host "  Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "[2/6] Stopping existing containers..." -ForegroundColor Yellow
docker compose -f docker-compose.full.yml down 2>$null
Write-Host "  Cleaned up" -ForegroundColor Green

# Build and start services
Write-Host "[3/6] Building and starting services..." -ForegroundColor Yellow
docker compose -f docker-compose.full.yml up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Failed to start services" -ForegroundColor Red
    exit 1
}
Write-Host "  Services started" -ForegroundColor Green

# Wait for services to be healthy
Write-Host "[4/6] Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check PostgreSQL
$dbReady = docker compose -f docker-compose.full.yml exec -T db pg_isready -U dutchkem 2>$null
if ($dbReady -match "accepting connections") {
    Write-Host "  PostgreSQL: Ready" -ForegroundColor Green
} else {
    Write-Host "  PostgreSQL: Waiting..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

# Check Redis
$redisReady = docker compose -f docker-compose.full.yml exec -T redis redis-cli ping 2>$null
if ($redisReady -match "PONG") {
    Write-Host "  Redis: Ready" -ForegroundColor Green
} else {
    Write-Host "  Redis: Waiting..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

# Run migrations
Write-Host "[5/6] Running database migrations..." -ForegroundColor Yellow
docker compose -f docker-compose.full.yml exec -T django python manage.py migrate --no-input 2>$null
Write-Host "  Migrations complete" -ForegroundColor Green

# Collect static files
Write-Host "[6/6] Collecting static files..." -ForegroundColor Yellow
docker compose -f docker-compose.full.yml exec -T django python manage.py collectstatic --no-input 2>$null
Write-Host "  Static files collected" -ForegroundColor Green

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  System is RUNNING!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Django Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  Admin Panel:     http://localhost:8000/admin/" -ForegroundColor White
Write-Host "  API Docs:        http://localhost:8000/api/docs/" -ForegroundColor White
Write-Host "  MT5 Bridge:      http://localhost:8082" -ForegroundColor White
Write-Host ""
Write-Host "  Trading Mode:    FULL (Automatic)" -ForegroundColor Yellow
Write-Host "  Trading Cycle:   Every 60 seconds" -ForegroundColor Yellow
Write-Host "  Active Symbols:  28 (Majors, Crosses, Exotics, Metals, Crypto, Indices)" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To stop:   docker compose -f docker-compose.full.yml down" -ForegroundColor Gray
Write-Host "  To logs:   docker compose -f docker-compose.full.yml logs -f" -ForegroundColor Gray
Write-Host "=============================================" -ForegroundColor Green
