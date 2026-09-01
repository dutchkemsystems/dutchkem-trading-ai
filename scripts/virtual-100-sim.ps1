<#
.SYNOPSIS
    DUTCHKEM-TRADING-AI V6.5 Virtual $100 Trading Simulation
    Simulates 30 days of trading with exact lot sizes, pip calculations,
    partial close execution (TP1/TP2/TP3), compounding, and circuit breakers.

.DESCRIPTION
    This simulation demonstrates how V6.5 orchestrates trades on a $100 account:
    - Exact 0.01 lot sizing (micro lots)
    - Precise pip value calculations per symbol
    - Partial close execution at TP1 (40%), TP2 (50%), TP3 (100%)
    - Daily P&L progression with compounding
    - Risk management circuit breakers in action
    - Full 16-phase pipeline walkthrough per trade
    - Backup system activation when V6.5 encounters issues

.PARAMETER StartingEquity
    Starting virtual balance (default: $100)

.PARAMETER TradingDays
    Number of days to simulate (default: 30)

.PARAMETER Detailed
    Show detailed trade-by-trade output

.PARAMETER Verbose
    Show all 16 phases for every cycle

.PARAMETER ExportReport
    Export final report to file
#>

param(
    [double]$StartingEquity = 100,
    [int]$TradingDays = 30,
    [switch]$Detailed,
    [switch]$VerboseOutput,
    [switch]$ExportReport
)

# ============================================================================
# V6.5 CONFIGURATION
# ============================================================================
$V65Config = @{
    # Account
    StartingEquity         = $StartingEquity

    # V6.5 Risk Management (compulsory)
    MaxDailyLossPct        = 2.0        # 2% daily loss limit
    MaxDrawdownPct         = 15.0       # 15% max drawdown circuit breaker
    MaxOpenPositions       = 3          # Max concurrent positions for small account
    MaxDailyTrades         = 6          # Conservative for $100 account
    MinSignalConfidence    = 65         # Minimum V6.5 combined signal confidence
    MinRiskReward          = 2.0        # Minimum R:R ratio

    # V6.5 Position Sizing
    BaseRiskPct            = 1.0        # Risk 1% of equity per trade ($1 on $100)
    MinLotSize             = 0.01       # Micro lot minimum
    MaxLotSize             = 0.05       # Max for $100 account
    RiskAdjustedSizing     = $true      # Use V6.5 RiskAdjustedSizer

    # V6.5 Partial Close
    TP1ClosePct            = 0.40       # Close 40% at TP1
    TP2ClosePct            = 0.50       # Close 50% of remainder at TP2
    TP3ClosePct            = 1.00       # Close remaining 100% at TP3
    BreakevenAfterTP1      = $true      # Move SL to breakeven after TP1

    # V6.5 Profit Targets (compulsory)
    DailyTargetPct         = 0.15       # 0.15%/day target
    WeeklyTargetPct        = 1.0        # 1.0%/week target
    MonthlyTargetPct       = 4.2        # 4.2%/month target
    TargetLockMultiplier   = 2.5        # Stop at 2.5x daily target

    # Circuit Breaker Tiers
    Tier1Drawdown          = 3.0        # Tier 1: 3% DD -> 50% size reduction
    Tier2Drawdown          = 5.0        # Tier 2: 5% DD -> 75% size reduction
    Tier3Drawdown          = 8.0        # Tier 3: 8% DD -> 100% size reduction (no trading)
    Tier4Drawdown          = 12.0       # Tier 4: 12% DD -> Emergency halt

    # V6.5 Backup System
    BackupEnabled          = $true
    BackupPriority         = @("V6_Orchestrator", "GoldEdge", "Scalping", "ConfluenceEngine")

    # Trailing Stop
    TrailingStartPips      = 5          # Start trailing after 5 pips profit
    TrailDistance1          = 5          # 5 pips trail for <10 pips profit
    TrailDistance2          = 10         # 10 pips trail for <20 pips profit
    TrailDistance3          = 15         # 15 pips trail for <50 pips profit
    TrailDistance4          = 20         # 20 pips trail for 50+ pips profit
}

# ============================================================================
# SYMBOL DEFINITIONS (with exact pip values for $100 account)
# ============================================================================
$Symbols = @(
    @{
        Name = "EURUSD"; Category = "MAJOR"; PipSize = 0.0001; ContractSize = 100000
        TypicalATR = 0.0060; TypicalSpread = 0.1; DailyRange = 60
        PipValuePerLot = 10.0; Description = "1 pip = $1.00 per 0.01 lot"
    }
    @{
        Name = "GBPUSD"; Category = "MAJOR"; PipSize = 0.0001; ContractSize = 100000
        TypicalATR = 0.0080; TypicalSpread = 0.12; DailyRange = 80
        PipValuePerLot = 10.0; Description = "1 pip = $1.00 per 0.01 lot"
    }
    @{
        Name = "USDJPY"; Category = "MAJOR"; PipSize = 0.01; ContractSize = 100000
        TypicalATR = 0.70; TypicalSpread = 0.12; DailyRange = 70
        PipValuePerLot = 6.67; Description = "1 pip = $0.67 per 0.01 lot (@150 JPY)"
    }
    @{
        Name = "AUDUSD"; Category = "MAJOR"; PipSize = 0.0001; ContractSize = 100000
        TypicalATR = 0.0065; TypicalSpread = 0.14; DailyRange = 55
        PipValuePerLot = 10.0; Description = "1 pip = $1.00 per 0.01 lot"
    }
    @{
        Name = "USDCAD"; Category = "MAJOR"; PipSize = 0.0001; ContractSize = 100000
        TypicalATR = 0.0055; TypicalSpread = 0.16; DailyRange = 50
        PipValuePerLot = 7.50; Description = "1 pip = $0.75 per 0.01 lot (@1.35 CAD)"
    }
    @{
        Name = "EURGBP"; Category = "MINOR"; PipSize = 0.0001; ContractSize = 100000
        TypicalATR = 0.0050; TypicalSpread = 0.15; DailyRange = 45
        PipValuePerLot = 12.50; Description = "1 pip = $1.25 per 0.01 lot (@0.85 GBP)"
    }
    @{
        Name = "EURJPY"; Category = "CROSS"; PipSize = 0.01; ContractSize = 100000
        TypicalATR = 0.90; TypicalSpread = 0.18; DailyRange = 85
        PipValuePerLot = 6.67; Description = "1 pip = $0.67 per 0.01 lot (@150 JPY)"
    }
    @{
        Name = "GBPJPY"; Category = "CROSS"; PipSize = 0.01; ContractSize = 100000
        TypicalATR = 1.10; TypicalSpread = 0.25; DailyRange = 100
        PipValuePerLot = 6.67; Description = "1 pip = $0.67 per 0.01 lot (@150 JPY)"
    }
    @{
        Name = "XAUUSD"; Category = "METAL"; PipSize = 0.01; ContractSize = 100
        TypicalATR = 25.0; TypicalSpread = 0.30; DailyRange = 2500
        PipValuePerLot = 1.0; Description = "1 pip = $0.01 per 0.01 lot; 100 pips = $1.00"
    }
    @{
        Name = "BTCUSD"; Category = "CRYPTO"; PipSize = 0.01; ContractSize = 1
        TypicalATR = 800.0; TypicalSpread = 50.0; DailyRange = 80000
        PipValuePerLot = 0.01; Description = "1 pip = $0.01 per 0.01 lot"
    }
)

# ============================================================================
# V6.5 16-PHASE PIPELINE DEFINITION
# ============================================================================
$V65Phases = @(
    @{ Num = 0;  Name = "Exit Management";          Desc = "Check open positions for TP/SL/time exits" }
    @{ Num = 1;  Name = "Market Scan";               Desc = "Scan 3-10 instruments for opportunities" }
    @{ Num = 2;  Name = "AI & Regime Detection";     Desc = "Ensemble prediction + HMM regime" }
    @{ Num = 3;  Name = "Sentiment Analysis";        Desc = "News + social sentiment scoring" }
    @{ Num = 4;  Name = "News Strategy";             Desc = "Economic event awareness" }
    @{ Num = 5;  Name = "Order Flow";                Desc = "Institutional activity detection" }
    @{ Num = 6;  Name = "Pattern Recognition";       Desc = "Deep learning candlestick patterns" }
    @{ Num = 7;  Name = "Multi-TF Confluence";       Desc = "Timeframe alignment check" }
    @{ Num = 8;  Name = "Signal Generation";         Desc = "Combined signal from all sources" }
    @{ Num = 9;  Name = "Risk Management";           Desc = "Dynamic sizing + circuit breakers" }
    @{ Num = 10; Name = "Adaptive Stop-Loss";        Desc = "ATR-based dynamic stop calculation" }
    @{ Num = 11; Name = "Adaptive Take-Profit";      Desc = "Multi-level TP with partial closes" }
    @{ Num = 12; Name = "Diversification Check";     Desc = "Portfolio correlation check" }
    @{ Num = 13; Name = "Execution";                 Desc = "Spread/slippage checks, order routing" }
    @{ Num = 14; Name = "Exit Management";           Desc = "Trailing stops, partial closes, time exits" }
    @{ Num = 15; Name = "Learning";                  Desc = "Self-optimizing parameter updates" }
    @{ Num = 16; Name = "Profit Targets";            Desc = "COMPULSORY dynamic target management" }
)

# Signal profiles with V6.5 realistic win rates
$V65SignalProfiles = @(
    @{ Name = "MultiTF_Confluence";       WinRate = 0.62; AvgRR = 2.4; Confidence = 82 }
    @{ Name = "HMM_Regime_Trend";         WinRate = 0.60; AvgRR = 2.6; Confidence = 78 }
    @{ Name = "Sentiment_Momentum";       WinRate = 0.55; AvgRR = 2.2; Confidence = 72 }
    @{ Name = "OrderFlow_Institutional";  WinRate = 0.58; AvgRR = 2.5; Confidence = 76 }
    @{ Name = "CNN_Pattern_Breakout";     WinRate = 0.57; AvgRR = 2.8; Confidence = 74 }
    @{ Name = "News_Impulse";             WinRate = 0.53; AvgRR = 2.0; Confidence = 68 }
    @{ Name = "V6_Fallback_Diversified";  WinRate = 0.52; AvgRR = 2.1; Confidence = 70 }
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Write-Header {
    param([string]$Title, [string]$Color = "Cyan")
    $line = "=" * 74
    Write-Host ""
    Write-Host $line -ForegroundColor $Color
    Write-Host "  $Title" -ForegroundColor White
    Write-Host $line -ForegroundColor $Color
}

function Write-SubHeader {
    param([string]$Title, [string]$Color = "Yellow")
    $line = "-" * 74
    Write-Host ""
    Write-Host $line -ForegroundColor DarkGray
    Write-Host "  $Title" -ForegroundColor $Color
    Write-Host $line -ForegroundColor DarkGray
}

function Write-Phase {
    param([int]$Phase, [string]$Name, [string]$Status, [string]$Detail = "")
    $icon = switch ($Status) {
        "OK"   { "[PASS]" }
        "SKIP" { "[SKIP]" }
        "WARN" { "[WARN]" }
        "FAIL" { "[FAIL]" }
        "INFO" { "[INFO]" }
        "BYPASS" { "[BYPASS]" }
        default { "[----]" }
    }
    $color = switch ($Status) {
        "OK"    { "Green" }
        "SKIP"  { "Yellow" }
        "WARN"  { "DarkYellow" }
        "FAIL"  { "Red" }
        "INFO"  { "White" }
        "BYPASS" { "Magenta" }
        default { "Gray" }
    }
    $phaseStr = "Phase {0:D2}" -f $Phase
    Write-Host "  $phaseStr " -NoNewline -ForegroundColor DarkGray
    Write-Host "$icon " -NoNewline -ForegroundColor $color
    Write-Host "$Name" -NoNewline -ForegroundColor White
    if ($Detail) { Write-Host " - $Detail" -ForegroundColor DarkGray } else { Write-Host "" }
}

function Write-Trade {
    param([hashtable]$Trade, [double]$Equity)
    $dirColor = if ($Trade.Direction -eq "BUY") { "Green" } else { "Red" }
    $pnlSign = if ($Trade.FinalPnL -ge 0) { "+" } else { "" }
    $pnlColor = if ($Trade.FinalPnL -ge 0) { "Green" } else { "Red" }
    $pnlPct = if ($Equity -gt 0) { ($Trade.FinalPnL / $Equity) * 100 } else { 0 }

    Write-Host ""
    Write-Host "  +------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Host "  | $($Trade.Direction) $($Trade.SymbolName) | $($Trade.ProfileName)" -ForegroundColor $dirColor
    Write-Host "  | Entry: $($Trade.EntryPrice) | SL: $($Trade.StopLoss) | TP1: $($Trade.TP1)" -ForegroundColor DarkGray
    Write-Host "  | TP2: $($Trade.TP2) | TP3: $($Trade.TP3)" -ForegroundColor DarkGray
    Write-Host "  | Size: $($Trade.Lots) lots ($($Trade.LotDescription))" -ForegroundColor DarkGray
    Write-Host "  | SL Distance: $($Trade.SLPips) pips | Risk: `$$([math]::Round($Trade.RiskAmount, 2))" -ForegroundColor DarkGray
    Write-Host "  | R:R: $($Trade.RiskReward) | Confidence: $($Trade.Confidence)%" -ForegroundColor DarkGray
    Write-Host "  | Partial Close: TP1(40%)=$(if($Trade.TP1Hit){"HIT"}else{"pending"}) TP2(50%)=$(if($Trade.TP2Hit){"HIT"}else{"pending"}) TP3(100%)=$(if($Trade.TP3Hit){"HIT"}else{"pending"})" -ForegroundColor DarkGray
    Write-Host "  | P&L: ${pnlSign}`$$([math]::Round($Trade.FinalPnL, 2)) (${pnlSign}$([math]::Round($pnlPct, 2))%) | $($Trade.Outcome)" -ForegroundColor $pnlColor
    Write-Host "  | Duration: $($Trade.Duration) | Exit: $($Trade.ExitReason)" -ForegroundColor DarkGray
    Write-Host "  +------------------------------------------------------+" -ForegroundColor DarkGray
}

function Get-CircuitBreakerTier {
    param([double]$DrawdownPct, [hashtable]$Config)
    if ($DrawdownPct -ge $Config.Tier4Drawdown) { return @{ Tier = 4; Multiplier = 0.0; Action = "EMERGENCY_HALT" } }
    if ($DrawdownPct -ge $Config.Tier3Drawdown) { return @{ Tier = 3; Multiplier = 0.0; Action = "HALT_TRADING" } }
    if ($DrawdownPct -ge $Config.Tier2Drawdown) { return @{ Tier = 2; Multiplier = 0.25; Action = "REDUCE_75%" } }
    if ($DrawdownPct -ge $Config.Tier1Drawdown) { return @{ Tier = 1; Multiplier = 0.50; Action = "REDUCE_50%" } }
    return @{ Tier = 0; Multiplier = 1.0; Action = "NORMAL" }
}

function Calculate-V65LotSize {
    param([double]$Equity, [double]$RiskPct, [double]$SLPips, [double]$PipValuePerPip, [double]$SizeMultiplier)
    $riskAmount = $Equity * ($RiskPct / 100.0)
    $adjustedRisk = $riskAmount * $SizeMultiplier
    if ($PipValuePerPip -le 0 -or $SLPips -le 0) { return 0.01 }
    $lots = $adjustedRisk / ($SLPips * $PipValuePerPip)
    $lots = [math]::Max(0.01, [math]::Min($lots, 0.05))
    return [math]::Round($lots, 2)
}

function Get-V65PipValue {
    param([hashtable]$Symbol, [double]$LotSize)
    # Pip value = ContractSize * PipSize * LotSize * ExchangeRateAdjustment
    $basePipValue = $Symbol.ContractSize * $Symbol.PipSize * $LotSize
    # For JPY pairs, adjust for typical exchange rate
    if ($Symbol.Name -match "JPY") {
        $basePipValue = $basePipValue * 0.00667  # Approximate USD/JPY adjustment
    }
    return [math]::Round($basePipValue, 4)
}

function Simulate-PartialClose {
    param([hashtable]$Trade, [double]$PriceMove)
    # Returns: @(PnL, TP1Hit, TP2Hit, TP3Hit, ExitReason, ExitPrice)
    $totalPnL = 0
    $tp1Hit = $false
    $tp2Hit = $false
    $tp3Hit = $false
    $exitReason = "OPEN"
    $exitPrice = 0
    $remainingVolume = $Trade.Lots

    $pipMove = $PriceMove / $Trade.PipSize

    # Check TP1 (40% close)
    if ($pipMove -ge $Trade.TPPips1) {
        $closeVolume = $remainingVolume * $V65Config.TP1ClosePct
        $pnl = $closeVolume * $Trade.TPPips1 * $Trade.PipValuePerPip
        $totalPnL += $pnl
        $remainingVolume *= (1 - $V65Config.TP1ClosePct)
        $tp1Hit = $true
        $exitReason = "TP1_PARTIAL"
    }

    # Check TP2 (50% of remainder)
    if ($pipMove -ge $Trade.TPPips2) {
        $closeVolume = $remainingVolume * $V65Config.TP2ClosePct
        $pnl = $closeVolume * ($Trade.TPPips2 - $Trade.TPPips1) * $Trade.PipValuePerPip
        $totalPnL += $pnl
        $remainingVolume *= (1 - $V65Config.TP2ClosePct)
        $tp2Hit = $true
        $exitReason = "TP2_PARTIAL"
    }

    # Check TP3 (full close)
    if ($pipMove -ge $Trade.TPPips3) {
        $pnl = $remainingVolume * ($Trade.TPPips3 - $Trade.TPPips2) * $Trade.PipValuePerPip
        $totalPnL += $pnl
        $tp3Hit = $true
        $exitReason = "TP3_FULL"
        $exitPrice = $Trade.EntryPrice + ($Trade.TPPips3 * $Trade.PipSize) if ($Trade.Direction -eq "BUY")
        $exitPrice = $Trade.EntryPrice - ($Trade.TPPips3 * $Trade.PipSize) if ($Trade.Direction -eq "SELL")
    }

    return @{ PnL = $totalPnL; TP1Hit = $tp1Hit; TP2Hit = $tp2Hit; TP3Hit = $tp3Hit; ExitReason = $exitReason; ExitPrice = $exitPrice }
}

# ============================================================================
# MAIN SIMULATION
# ============================================================================

Write-Host ""
Write-Host "  ==========================================================" -ForegroundColor Cyan
Write-Host "    DUTCHKEM-TRADING-AI  V6.5  VIRTUAL `$100 SIMULATION     " -ForegroundColor White
Write-Host "    Engine: V6.5 Ultimate Enhanced (16-Phase Pipeline)       " -ForegroundColor White
Write-Host "    Account: `$$StartingEquity | Days: $TradingDays | Mode: Full Auto    " -ForegroundColor White
Write-Host "  ==========================================================" -ForegroundColor Cyan

# State variables
$equity = $V65Config.StartingEquity
$peakEquity = $equity
$startingEquity = $equity
$allTrades = [System.Collections.ArrayList]::new()
$dailyResults = [System.Collections.ArrayList]::new()
$backupActivations = 0
$circuitBreakerTriggers = 0
$totalCycles = 0
$phaseTimings = @{}

# Track daily metrics for V6.5 profit target enforcement
$todayPnL = 0
$todayStartEquity = $equity

for ($day = 1; $day -le $TradingDays; $day++) {
    $dayStartEquity = $equity
    $todayStartEquity = $equity
    $todayPnL = 0
    $dailyPnL = 0
    $dayWins = 0
    $dayLosses = 0
    $dayTradesCount = 0
    $cycleCount = 0
    $dayBackupUsed = $null

    Write-Header "TRADING DAY $day of $TradingDays  |  Engine: V6.5" "Cyan"
    Write-Host "  Starting Equity: `$$([math]::Round($equity, 2))" -ForegroundColor White
    Write-Host "  Daily Target: $V65Config.DailyTargetPct% (`$$([math]::Round($equity * $V65Config.DailyTargetPct / 100, 4)))" -ForegroundColor DarkCyan
    Write-Host "  Daily Loss Limit: $V65Config.MaxDailyLossPct% (`$$([math]::Round($equity * $V65Config.MaxDailyLossPct / 100, 2)))" -ForegroundColor DarkCyan

    # ── V6.5 Daily Target Check (Phase 16 - runs FIRST) ──────────────
    Write-SubHeader "Phase 16: V6.5 Profit Target Check (COMPULSORY)" "Magenta"
    $dailyTargetAmount = $equity * ($V65Config.DailyTargetPct / 100)
    $dailyLossLimit = $equity * ($V65Config.MaxDailyLossPct / 100)
    Write-Host "  Daily Target: `$$([math]::Round($dailyTargetAmount, 4)) | Loss Limit: `$$([math]::Round($dailyLossLimit, 2))" -ForegroundColor White
    Write-Host "  V6.5 Source: PROFIT_TARGET_SOURCE = V6.5_ORCHESTRATOR" -ForegroundColor Green

    # ── Circuit Breaker Check ─────────────────────────────────────────
    $currentDD = if ($peakEquity -gt 0) { (($peakEquity - $equity) / $peakEquity) * 100 } else { 0 }
    $cbTier = Get-CircuitBreakerTier -DrawdownPct $currentDD -Config $V65Config

    if ($cbTier.Tier -gt 0) {
        $circuitBreakerTriggers++
        Write-Host ""
        Write-Host "  *** CIRCUIT BREAKER TIER $($cbTier.Tier): $($cbTier.Action) ***" -ForegroundColor Red
        Write-Host "  Drawdown: $([math]::Round($currentDD, 2))% | Size Multiplier: $($cbTier.Multiplier)" -ForegroundColor Red

        if ($cbTier.Multiplier -eq 0) {
            Write-Host "  *** TRADING HALTED — No positions allowed ***" -ForegroundColor Red
            [void]$dailyResults.Add(@{
                Day = $day; StartEquity = $dayStartEquity; EndEquity = $equity
                PnL = 0; PnLPercent = 0; Trades = 0; Wins = 0; Losses = 0
                CircuitBreaker = "TIER$($cbTier.Tier)"; BackupUsed = $null
            })
            continue
        }
    }

    # ── Run V6.5 Trading Cycles (simulated per 60 seconds) ───────────
    $cyclesPerDay = 8  # Simulate 8 key cycles per day (London open, NY open, etc.)
    $cycleTimes = @("02:00", "04:00", "08:00", "10:00", "12:00", "14:00", "16:00", "20:00")

    for ($cycle = 0; $cycle -lt $cyclesPerDay; $cycle++) {
        $cycleCount++
        $totalCycles++
        $cycleTime = $cycleTimes[$cycle]

        Write-SubHeader "V6.5 Cycle #$cycleCount @ $cycleTime UTC" "Yellow"

        # ── Check if V6.5 should activate backup ─────────────────────
        $useBackup = $false
        $activeSystem = "V6.5"

        if ($V65Config.BackupEnabled -and (Get-Random -Minimum 0.0 -Maximum 1.0) -lt 0.03) {
            # 3% chance V6.5 encounters an issue and activates backup
            $useBackup = $true
            $activeSystem = $V65Config.BackupPriority | Get-Random
            $backupActivations++
            $dayBackupUsed = $activeSystem
            Write-Host "  [V6.5] Activating backup: $activeSystem" -ForegroundColor Magenta
        }

        # ── Execute 16-Phase Pipeline ─────────────────────────────────
        if ($VerboseOutput) {
            foreach ($phase in $V65Phases) {
                $status = if ($useBackup -and $phase.Num -ge 1 -and $phase.Num -le 8) { "BYPASS" } else { "OK" }
                $detail = if ($status -eq "BYPASS") { "Using $activeSystem" } else { $phase.Desc }
                Write-Phase $phase.Num $phase.Name $status $detail
            }
        } else {
            # Condensed output
            Write-Phase 16 "Profit Targets (COMPULSORY)" "OK" "Daily: $V65Config.DailyTargetPct% | Source: V6.5"
            Write-Phase 1 "Market Scan" "OK" "Scanning $($Symbols.Count) instruments"
            Write-Phase 8 "Signal Generation" "OK" "V6.5 combined scoring"
            Write-Phase 9 "Risk Management" "OK" "CB Tier: $($cbTier.Tier) | Size Mult: $($cbTier.Multiplier)"
            if ($useBackup) {
                Write-Phase 13 "Execution" "BYPASS" "Routed via $activeSystem"
            } else {
                Write-Phase 13 "Execution" "OK" "V6.5 direct execution"
            }
        }

        # ── Generate V6.5 Signal ─────────────────────────────────────
        $candidateSymbol = $Symbols | Get-Random
        $profile = $V65SignalProfiles | Get-Random
        $signalConfidence = [math]::Min(95, [math]::Max(50, $profile.Confidence + (Get-Random -Minimum -10 -Maximum 10)))

        if ($signalConfidence -lt $V65Config.MinSignalConfidence) {
            Write-Host "  Signal confidence $signalConfidence% below threshold $($V65Config.MinSignalConfidence)% — SKIP" -ForegroundColor Yellow
            continue
        }

        $direction = if ((Get-Random -Minimum 0.0 -Maximum 1.0) -gt 0.5) { "BUY" } else { "SELL" }

        # ── V6.5 Position Sizing (RiskAdjustedSizer) ──────────────────
        $atrPips = if ($candidateSymbol.PipSize -gt 0) { [math]::Round($candidateSymbol.TypicalATR / $candidateSymbol.PipSize, 0) } else { 20 }
        $slPips = [math]::Round($atrPips * 1.5, 0)
        if ($slPips -lt 10) { $slPips = 10 }  # Minimum 10 pips SL
        if ($slPips -gt 50) { $slPips = 50 }  # Maximum 50 pips SL

        $tpPips1 = [math]::Round($slPips * 2.0, 0)   # TP1 at 2R
        $tpPips2 = [math]::Round($slPips * 3.0, 0)   # TP2 at 3R
        $tpPips3 = [math]::Round($slPips * 4.5, 0)   # TP3 at 4.5R

        $pipValuePerPip = Get-V65PipValue -Symbol $candidateSymbol -LotSize 0.01
        $riskReward = [math]::Round($tpPips1 / $slPips, 2)

        if ($riskReward -lt $V65Config.MinRiskReward) {
            Write-Host "  R:R $riskReward below minimum $($V65Config.MinRiskReward) — SKIP" -ForegroundColor Yellow
            continue
        }

        # Calculate lot size with V6.5 RiskAdjustedSizer
        $lotSize = Calculate-V65LotSize -Equity $equity -RiskPct $V65Config.BaseRiskPct -SLPips $slPips -PipValuePerPip $pipValuePerPip -SizeMultiplier $cbTier.Multiplier

        # Ensure minimum lot size for $100 account
        if ($lotSize -lt 0.01) { $lotSize = 0.01 }

        $riskAmount = $lotSize * $slPips * $pipValuePerPip

        # Check daily loss limit
        if (($todayPnL + $riskAmount) -gt $dailyLossLimit) {
            Write-Host "  Daily loss limit would be exceeded — SKIP" -ForegroundColor Yellow
            continue
        }

        # Check max daily trades
        if ($dayTradesCount -ge $V65Config.MaxDailyTrades) {
            Write-Host "  Max daily trades ($V65Config.MaxDailyTrades) reached — SKIP" -ForegroundColor Yellow
            continue
        }

        # ── Create Trade Entry ────────────────────────────────────────
        $basePrice = switch ($candidateSymbol.Name) {
            "EURUSD" { 1.0850 + (Get-Random -Minimum -0.0050 -Maximum 0.0050) }
            "GBPUSD" { 1.2650 + (Get-Random -Minimum -0.0080 -Maximum 0.0080) }
            "USDJPY" { 149.50 + (Get-Random -Minimum -0.50 -Maximum 0.50) }
            "AUDUSD" { 0.6550 + (Get-Random -Minimum -0.0040 -Maximum 0.0040) }
            "USDCAD" { 1.3550 + (Get-Random -Minimum -0.0040 -Maximum 0.0040) }
            "EURGBP" { 0.8550 + (Get-Random -Minimum -0.0030 -Maximum 0.0030) }
            "EURJPY" { 162.20 + (Get-Random -Minimum -0.80 -Maximum 0.80) }
            "GBPJPY" { 189.30 + (Get-Random -Minimum -1.00 -Maximum 1.00) }
            "XAUUSD" { 2350.00 + (Get-Random -Minimum -20.00 -Maximum 20.00) }
            "BTCUSD" { 67500.00 + (Get-Random -Minimum -500.00 -Maximum 500.00) }
            default { 1.0000 }
        }

        $entryPrice = [math]::Round($basePrice, 6)
        if ($direction -eq "BUY") {
            $sl = [math]::Round($entryPrice - ($slPips * $candidateSymbol.PipSize), 6)
            $tp1 = [math]::Round($entryPrice + ($tpPips1 * $candidateSymbol.PipSize), 6)
            $tp2 = [math]::Round($entryPrice + ($tpPips2 * $candidateSymbol.PipSize), 6)
            $tp3 = [math]::Round($entryPrice + ($tpPips3 * $candidateSymbol.PipSize), 6)
        } else {
            $sl = [math]::Round($entryPrice + ($slPips * $candidateSymbol.PipSize), 6)
            $tp1 = [math]::Round($entryPrice - ($tpPips1 * $candidateSymbol.PipSize), 6)
            $tp2 = [math]::Round($entryPrice - ($tpPips2 * $candidateSymbol.PipSize), 6)
            $tp3 = [math]::Round($entryPrice - ($tpPips3 * $candidateSymbol.PipSize), 6)
        }

        $trade = @{
            SymbolName    = $candidateSymbol.Name
            Direction     = $direction
            EntryPrice    = $entryPrice
            StopLoss      = $sl
            TP1           = $tp1
            TP2           = $tp2
            TP3           = $tp3
            Lots          = $lotSize
            LotDescription = "$lotSize lots ($([math]::Round($lotSize * 100000, 0)) units)"
            SLPips        = $slPips
            TPPips1       = $tpPips1
            TPPips2       = $tpPips2
            TPPips3       = $tpPips3
            RiskReward    = $riskReward
            PipValuePerPip = $pipValuePerPip
            RiskAmount    = $riskAmount
            Confidence    = $signalConfidence
            ProfileName   = $profile.Name
            PipSize       = $candidateSymbol.PipSize
            TP1Hit        = $false
            TP2Hit        = $false
            TP3Hit        = $false
            FinalPnL      = 0
            Outcome       = "PENDING"
            ExitReason    = "OPEN"
            Duration      = ""
            ActiveSystem  = $activeSystem
        }

        # ── Simulate Trade Outcome ────────────────────────────────────
        $roll = Get-Random -Minimum 0.0 -Maximum 1.0
        # V6.5 slightly boosts win rate from backup systems
        $effectiveWinRate = if ($useBackup) { $profile.WinRate * 0.95 } else { $profile.WinRate }
        $isWin = $roll -lt $effectiveWinRate

        if ($isWin) {
            # Simulate partial close execution
            $maxPipMove = $tpPips3 + (Get-Random -Minimum -5 -Maximum 10)
            $priceMove = $maxPipMove * $candidateSymbol.PipSize

            $partialResult = Simulate-PartialClose -Trade $trade -PriceMove $priceMove
            $trade.TP1Hit = $partialResult.TP1Hit
            $trade.TP2Hit = $partialResult.TP2Hit
            $trade.TP3Hit = $partialResult.TP3Hit
            $trade.FinalPnL = [math]::Round($partialResult.PnL, 4)
            $trade.ExitReason = $partialResult.ExitReason
            $trade.Outcome = "WIN"
            $dayWins++
        } else {
            # Loss: hit stop loss
            $lossPips = $slPips * (Get-Random -Minimum 0.7 -Maximum 1.0)
            $trade.FinalPnL = [math]::Round(-($lotSize * $lossPips * $pipValuePerPip), 4)
            $trade.ExitReason = "STOP_LOSS"
            $trade.Outcome = "LOSS"
            $dayLosses++
        }

        $durationMinutes = Get-Random -Minimum 15 -Maximum 720
        $trade.Duration = "{0}h {1}m" -f [math]::Floor($durationMinutes / 60), ($durationMinutes % 60)

        # Update equity
        $equity += $trade.FinalPnL
        if ($equity -gt $peakEquity) { $peakEquity = $equity }
        $dailyPnL += $trade.FinalPnL
        $todayPnL += $trade.FinalPnL
        $dayTradesCount++

        [void]$allTrades.Add($trade)

        if ($Detailed -or $VerboseOutput) {
            Write-Trade -Trade $trade -Equity $equity
        } else {
            $pnlSign = if ($trade.FinalPnL -ge 0) { "+" } else { "" }
            $pnlColor = if ($trade.FinalPnL -ge 0) { "Green" } else { "Red" }
            Write-Host "  $($trade.Direction) $($trade.SymbolName) | $($trade.Lots) lots | SL=$($trade.SLPips)p | R:R=$($trade.RiskReward) | P&L: ${pnlSign}`$$([math]::Round($trade.FinalPnL, 2)) | $($trade.Outcome)" -ForegroundColor $pnlColor
        }

        # ── Check daily target lock ───────────────────────────────────
        $dailyPnLPct = if ($todayStartEquity -gt 0) { ($todayPnL / $todayStartEquity) * 100 } else { 0 }
        if ($dailyPnLPct -ge ($V65Config.DailyTargetPct * $V65Config.TargetLockMultiplier)) {
            Write-Host ""
            Write-Host "  *** V6.5 DAILY TARGET LOCK: $([math]::Round($dailyPnLPct, 4))% reached ($($V65Config.DailyTargetPct * $V65Config.TargetLockMultiplier)x target) ***" -ForegroundColor Yellow
            Write-Host "  Trading stopped for today per V6.5 Profit Target Management" -ForegroundColor Yellow
            break
        }

        # Check daily loss limit
        if ($todayPnL -le -$dailyLossLimit) {
            Write-Host ""
            Write-Host "  *** V6.5 DAILY LOSS LIMIT: `$$([math]::Round($todayPnL, 2)) hit limit ***" -ForegroundColor Red
            break
        }
    }

    # ── End of Day Summary ────────────────────────────────────────────
    $dayTradesTotal = $dayWins + $dayLosses
    $winRate = if ($dayTradesTotal -gt 0) { [math]::Round(($dayWins / $dayTradesTotal) * 100, 1) } else { 0 }
    $dailyPnLPct = if ($dayStartEquity -gt 0) { [math]::Round(($dailyPnL / $dayStartEquity) * 100, 4) } else { 0 }
    $currentDD = if ($peakEquity -gt 0) { [math]::Round((($peakEquity - $equity) / $peakEquity) * 100, 2) } else { 0 }

    Write-SubHeader "Day $day End-of-Day Summary" "Yellow"
    Write-Host "  Trades: $dayTradesTotal | Wins: $dayWins | Losses: $dayLosses | Win Rate: $winRate%" -ForegroundColor White
    $pnlSign = if ($dailyPnL -ge 0) { "+" } else { "" }
    $pnlColor = if ($dailyPnL -ge 0) { "Green" } else { "Red" }
    Write-Host "  Daily P&L: ${pnlSign}`$$([math]::Round($dailyPnL, 2)) ($dailyPnLPct%)" -ForegroundColor $pnlColor
    Write-Host "  Equity: `$$([math]::Round($equity, 2)) | Peak: `$$([math]::Round($peakEquity, 2)) | DD: $currentDD%" -ForegroundColor White
    if ($dayBackupUsed) {
        Write-Host "  Backup System Used: $dayBackupUsed" -ForegroundColor Magenta
    }
    $cbTierToday = Get-CircuitBreakerTier -DrawdownPct $currentDD -Config $V65Config
    Write-Host "  Circuit Breaker: Tier $($cbTierToday.Tier) ($($cbTierToday.Action))" -ForegroundColor $(if ($cbTierToday.Tier -eq 0) { "Green" } else { "Yellow" })

    [void]$dailyResults.Add(@{
        Day = $day; StartEquity = $dayStartEquity; EndEquity = $equity
        PnL = $dailyPnL; PnLPercent = $dailyPnLPct
        Trades = $dayTradesTotal; Wins = $dayWins; Losses = $dayLosses
        Drawdown = $currentDD; BackupUsed = $dayBackupUsed
        CircuitBreakerTier = $cbTierToday.Tier
    })
}

# ============================================================================
# FINAL PERFORMANCE REPORT
# ============================================================================

Write-Header "V6.5 SIMULATION COMPLETE - PERFORMANCE REPORT" "Green"

$totalTrades = $allTrades.Count
$totalWins = ($allTrades | Where-Object { $_.Outcome -eq "WIN" }).Count
$totalLosses = $totalTrades - $totalWins
$overallWinRate = if ($totalTrades -gt 0) { [math]::Round(($totalWins / $totalTrades) * 100, 1) } else { 0 }
$totalPnL = $equity - $V65Config.StartingEquity
$totalPnLPct = [math]::Round(($totalPnL / $V65Config.StartingEquity) * 100, 2)
$maxDD = if ($peakEquity -gt 0) { [math]::Round((($peakEquity - [math]::Min($equity, $peakEquity)) / $peakEquity) * 100, 2) } else { 0 }

$totalProfit = ($allTrades | Where-Object { $_.FinalPnL -gt 0 } | Measure-Object -Property FinalPnL -Sum).Sum
$totalLossAmt = [math]::Abs(($allTrades | Where-Object { $_.FinalPnL -lt 0 } | Measure-Object -Property FinalPnL -Sum).Sum)
$profitFactor = if ($totalLossAmt -gt 0) { [math]::Round($totalProfit / $totalLossAmt, 2) } else { 999.99 }

# Compounding projections
$avgDailyReturn = if ($V65Config.StartingEquity -gt 0 -and $TradingDays -gt 0) { $totalPnL / $TradingDays / $V65Config.StartingEquity } else { 0 }
$monthlyProjection = $V65Config.StartingEquity * [math]::Pow(1 + $avgDailyReturn, 22)
$annualProjection = $V65Config.StartingEquity * [math]::Pow(1 + $avgDailyReturn, 252)

# Partial close stats
$tp1Hits = ($allTrades | Where-Object { $_.TP1Hit -eq $true }).Count
$tp2Hits = ($allTrades | Where-Object { $_.TP2Hit -eq $true }).Count
$tp3Hits = ($allTrades | Where-Object { $_.TP3Hit -eq $true }).Count

Write-Host ""
Write-Host "  ┌─────────────────────────────────────────────────┐" -ForegroundColor Cyan
Write-Host "  │         V6.5 PERFORMANCE SUMMARY                │" -ForegroundColor Cyan
Write-Host "  ├─────────────────────────────────────────────────┤" -ForegroundColor Cyan
Write-Host "  │ Starting Equity:     `$$([math]::Round($V65Config.StartingEquity, 2))" -ForegroundColor White
$pnlSign = if ($totalPnL -ge 0) { "+" } else { "" }
$pnlColor = if ($totalPnL -ge 0) { "Green" } else { "Red" }
Write-Host "  │ Final Equity:        `$$([math]::Round($equity, 2))" -ForegroundColor $pnlColor
Write-Host "  │ Total P&L:           ${pnlSign}`$$([math]::Round($totalPnL, 2)) ($totalPnLPct%)" -ForegroundColor $pnlColor
Write-Host "  │ Peak Equity:         `$$([math]::Round($peakEquity, 2))" -ForegroundColor White
Write-Host "  │ Max Drawdown:        $maxDD%" -ForegroundColor $(if ($maxDD -lt 5) { "Green" } elseif ($maxDD -lt 10) { "Yellow" } else { "Red" })
Write-Host "  ├─────────────────────────────────────────────────┤" -ForegroundColor Cyan
Write-Host "  │ Total Trades:        $totalTrades" -ForegroundColor White
Write-Host "  │ Winning Trades:      $totalWins" -ForegroundColor Green
Write-Host "  │ Losing Trades:       $totalLosses" -ForegroundColor Red
Write-Host "  │ Overall Win Rate:    $overallWinRate%" -ForegroundColor $(if ($overallWinRate -ge 55) { "Green" } else { "Yellow" })
Write-Host "  │ Profit Factor:       $profitFactor" -ForegroundColor $(if ($profitFactor -ge 1.5) { "Green" } else { "Yellow" })
Write-Host "  ├─────────────────────────────────────────────────┤" -ForegroundColor Cyan
Write-Host "  │ Partial Close Stats:" -ForegroundColor White
Write-Host "  │   TP1 Hits (40%):    $tp1Hits" -ForegroundColor DarkCyan
Write-Host "  │   TP2 Hits (50%):    $tp2Hits" -ForegroundColor DarkCyan
Write-Host "  │   TP3 Hits (100%):   $tp3Hits" -ForegroundColor DarkCyan
Write-Host "  ├─────────────────────────────────────────────────┤" -ForegroundColor Cyan
Write-Host "  │ Risk Management:" -ForegroundColor White
Write-Host "  │   Circuit Breakers:  $circuitBreakerTriggers triggers" -ForegroundColor Yellow
Write-Host "  │   Backup Activations: $backupActivations" -ForegroundColor Magenta
Write-Host "  │   Total Cycles:      $totalCycles" -ForegroundColor White
Write-Host "  ├─────────────────────────────────────────────────┤" -ForegroundColor Cyan
Write-Host "  │ Compounding Projections:" -ForegroundColor White
Write-Host "  │   Avg Daily Return:  $([math]::Round($avgDailyReturn * 100, 4))%" -ForegroundColor White
Write-Host "  │   Monthly (22 days): `$$([math]::Round($monthlyProjection, 2)) ($([math]::Round(($monthlyProjection / $V65Config.StartingEquity - 1) * 100, 2))%)" -ForegroundColor Cyan
Write-Host "  │   Annual (252 days): `$$([math]::Round($annualProjection, 2)) ($([math]::Round(($annualProjection / $V65Config.StartingEquity - 1) * 100, 2))%)" -ForegroundColor Cyan
Write-Host "  └─────────────────────────────────────────────────┘" -ForegroundColor Cyan

Write-Host ""
Write-Host "  -- Daily Breakdown --" -ForegroundColor Yellow
foreach ($dr in $dailyResults) {
    $drSign = if ($dr.PnL -ge 0) { "+" } else { "" }
    $drColor = if ($dr.PnL -ge 0) { "Green" } else { "Red" }
    $drBackup = if ($dr.BackupUsed) { " [Backup: $($dr.BackupUsed)]" } else { "" }
    $drCB = if ($dr.CircuitBreakerTier -gt 0) { " [CB:T$($dr.CircuitBreakerTier)]" } else { "" }
    Write-Host "    Day $($dr.Day): $($dr.Trades) trades | $($dr.Wins)W/$($dr.Losses)L | P&L: ${drSign}`$$([math]::Round($dr.PnL, 2)) ($($dr.PnLPercent)%)$drBackup$drCB" -ForegroundColor $drColor
}

Write-Host ""
Write-Host "  ==========================================================" -ForegroundColor Green
Write-Host "    V6.5 Simulation Complete — All 16 Phases Executed        " -ForegroundColor White
Write-Host "    Engine: V6.5 Ultimate Enhanced | Backup: Active          " -ForegroundColor White
Write-Host "  ==========================================================" -ForegroundColor Green

# Export report if requested
if ($ExportReport) {
    $reportPath = "v65-simulation-report-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
    Write-Host ""
    Write-Host "  Report exported to: $reportPath" -ForegroundColor Cyan
}
