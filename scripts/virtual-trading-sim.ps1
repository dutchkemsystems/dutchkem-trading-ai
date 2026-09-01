<#
.SYNOPSIS
    DUTCHKEM-TRADING-AI Virtual Trading Simulation
    Simulates 5 trading days with realistic scenarios showing the full 15-phase pipeline.
#>

param(
    [double]$StartingEquity = 10000,
    [int]$TradingDays = 5,
    [switch]$Detailed,
    [switch]$ExportReport
)

$Config = @{
    StartingEquity     = $StartingEquity
    MaxDailyLoss       = 0.02
    DailyTargetLock    = 0.004
    MaxPositionSize    = 0.01
    MaxOpenPositions   = 5
    MaxDailyTrades     = 10
    MinSignalStrength  = 65
    MinRiskReward      = 2.0
    MaxDrawdown        = 0.15
    PartialClose1      = 0.40
    PartialClose2      = 0.50
    PartialClose3      = 1.00
}

$Symbols = @(
    @{ Name = "EURUSD"; Category = "MAJOR"; PipSize = 0.0001; ContractSize = 100000; TypicalATR = 0.0060 }
    @{ Name = "GBPUSD"; Category = "MAJOR"; PipSize = 0.0001; ContractSize = 100000; TypicalATR = 0.0080 }
    @{ Name = "USDJPY"; Category = "MAJOR"; PipSize = 0.01;   ContractSize = 100000; TypicalATR = 0.70 }
    @{ Name = "AUDUSD"; Category = "MAJOR"; PipSize = 0.0001; ContractSize = 100000; TypicalATR = 0.0065 }
    @{ Name = "USDCAD"; Category = "MAJOR"; PipSize = 0.0001; ContractSize = 100000; TypicalATR = 0.0055 }
    @{ Name = "EURGBP"; Category = "MINOR"; PipSize = 0.0001; ContractSize = 100000; TypicalATR = 0.0050 }
    @{ Name = "EURJPY"; Category = "MINOR"; PipSize = 0.01;   ContractSize = 100000; TypicalATR = 0.90 }
    @{ Name = "GBPJPY"; Category = "MINOR"; PipSize = 0.01;   ContractSize = 100000; TypicalATR = 1.10 }
    @{ Name = "XAUUSD"; Category = "COMMODITY"; PipSize = 0.01; ContractSize = 100;    TypicalATR = 25.0 }
    @{ Name = "XAGUSD"; Category = "COMMODITY"; PipSize = 0.01; ContractSize = 5000;   TypicalATR = 0.60 }
    @{ Name = "BTCUSD"; Category = "CRYPTO"; PipSize = 0.01;  ContractSize = 1;      TypicalATR = 800.0 }
    @{ Name = "ETHUSD"; Category = "CRYPTO"; PipSize = 0.01;  ContractSize = 1;      TypicalATR = 45.0 }
    @{ Name = "SOLUSD"; Category = "CRYPTO"; PipSize = 0.01;  ContractSize = 1;      TypicalATR = 5.0 }
    @{ Name = "US30";   Category = "INDEX"; PipSize = 0.01;  ContractSize = 1;   TypicalATR = 150.0 }
    @{ Name = "US500";  Category = "INDEX"; PipSize = 0.01;  ContractSize = 1;   TypicalATR = 35.0 }
    @{ Name = "NAS100"; Category = "INDEX"; PipSize = 0.01;  ContractSize = 1;   TypicalATR = 80.0 }
    @{ Name = "GER40";  Category = "INDEX"; PipSize = 0.01;  ContractSize = 1;   TypicalATR = 70.0 }
)

$IndicatorProfiles = @(
    @{ Name = "RSI_Oversold_Reversal"; WinRate = 0.58; AvgRR = 2.3 }
    @{ Name = "EMA_Cross_Golden";       WinRate = 0.52; AvgRR = 2.1 }
    @{ Name = "MACD_Histogram";         WinRate = 0.48; AvgRR = 2.5 }
    @{ Name = "BB_Squeeze_Breakout";    WinRate = 0.55; AvgRR = 2.8 }
    @{ Name = "ATR_Volatility_Entry";   WinRate = 0.50; AvgRR = 2.0 }
    @{ Name = "ADX_Trend_Following";    WinRate = 0.54; AvgRR = 2.2 }
    @{ Name = "MultiTF_Confluence";      WinRate = 0.62; AvgRR = 2.4 }
    @{ Name = "HMM_Regime_Detection";    WinRate = 0.60; AvgRR = 2.6 }
    @{ Name = "CNN_Pattern_Recognition"; WinRate = 0.57; AvgRR = 2.3 }
    @{ Name = "Sentiment_Analysis";      WinRate = 0.53; AvgRR = 2.1 }
)

function Write-Header {
    param([string]$Title, [string]$Color = "Cyan")
    $line = "=" * 70
    Write-Host ""
    Write-Host $line -ForegroundColor $Color
    Write-Host "  $Title" -ForegroundColor White
    Write-Host $line -ForegroundColor $Color
}

function Write-Phase {
    param([int]$Phase, [string]$Name, [string]$Status, [string]$Detail = "")
    $icon = switch ($Status) { "OK" { "[PASS]" } "SKIP" { "[SKIP]" } "WARN" { "[WARN]" } "FAIL" { "[FAIL]" } "INFO" { "[INFO]" } default { "[----]" } }
    $color = switch ($Status) { "OK" { "Green" } "SKIP" { "Yellow" } "WARN" { "DarkYellow" } "FAIL" { "Red" } "INFO" { "White" } default { "Gray" } }
    $phaseStr = "Phase {0:D2}" -f $Phase
    Write-Host "  $phaseStr " -NoNewline -ForegroundColor DarkGray
    Write-Host "$icon " -NoNewline -ForegroundColor $color
    Write-Host "$Name" -NoNewline -ForegroundColor White
    if ($Detail) { Write-Host " - $Detail" -ForegroundColor DarkGray } else { Write-Host "" }
}

function Get-SignalStrength {
    param([double]$BaseWinRate)
    $noise = (Get-Random -Minimum -15 -Maximum 15)
    return [math]::Min(95, [math]::Max(50, [math]::Round(($BaseWinRate * 100) + $noise, 1)))
}

function Calculate-PositionSize {
    param([double]$Equity, [double]$RiskPercent, [double]$SLPips, [double]$PipValue)
    $riskAmount = $Equity * $RiskPercent
    if ($PipValue -eq 0) { return 0.01 }
    $lots = $riskAmount / ($SLPips * $PipValue)
    return [math]::Round([math]::Max(0.01, [math]::Min($lots, $Equity * 0.1)), 2)
}

# ============================================================================
# MAIN SIMULATION
# ============================================================================

Write-Host ""
Write-Host "  ========================================================" -ForegroundColor Cyan
Write-Host "    DUTCHKEM-TRADING-AI VIRTUAL TRADING SIMULATION        " -ForegroundColor White
Write-Host "    Simulating $TradingDays Trading Days | Starting: `$$StartingEquity           " -ForegroundColor White
Write-Host "  ========================================================" -ForegroundColor Cyan

$equity = $Config.StartingEquity
$peakEquity = $equity
$allTrades = [System.Collections.ArrayList]::new()
$dailyResults = [System.Collections.ArrayList]::new()

for ($day = 1; $day -le $TradingDays; $day++) {
    $dayStartEquity = $equity
    $dailyPnL = 0
    $dayWins = 0
    $dayLosses = 0
    $dayTradesCount = 0

    Write-Header "TRADING DAY $day of $TradingDays" "Cyan"
    Write-Host "  Starting Equity: `$$([math]::Round($equity, 2))" -ForegroundColor White
    Write-Host ""
    Write-Host "  -- 15-Phase Trading Pipeline --" -ForegroundColor Yellow

    # Phase 1-7: Analysis
    $scannedCount = Get-Random -Minimum 15 -Maximum 28
    Write-Phase 1 "Market Scanner" "OK" "Scanned $scannedCount/28 symbols"
    Write-Phase 2 "Multi-Timeframe Analysis" "OK" "Analyzing M5/M15/M30/H1/H2/H4"
    Write-Phase 3 "Indicator Calculation" "OK" "RSI, EMA(9,21), MACD, BB(20,2), ATR(14), ADX(14)"
    $regimes = @("Trending", "Ranging", "Volatile", "Quiet")
    Write-Phase 4 "HMM Regime Detection" "OK" "Regime: $($regimes | Get-Random)"
    $patterns = @("Double Bottom", "Head & Shoulders", "Ascending Triangle", "Flag Pattern", "Wedge", "None")
    Write-Phase 5 "CNN Pattern Recognition" "OK" "Pattern: $($patterns | Get-Random)"
    $sentimentScore = [math]::Round((Get-Random -Minimum -0.5 -Maximum 0.5), 2)
    $sentimentLabel = if ($sentimentScore -gt 0.1) { "Bullish" } elseif ($sentimentScore -lt -0.1) { "Bearish" } else { "Neutral" }
    Write-Phase 6 "Sentiment Analysis" "OK" "Score: $sentimentScore ($sentimentLabel)"
    Write-Phase 7 "Order Flow Analysis" "OK" "Net flow: $([math]::Round((Get-Random -Minimum -0.3 -Maximum 0.3), 2))"

    # Phase 8: Signal Generation
    $candidateSignals = [System.Collections.ArrayList]::new()
    foreach ($sym in $Symbols) {
        $profile = $IndicatorProfiles | Get-Random
        $strength = Get-SignalStrength -BaseWinRate $profile.WinRate
        if ($strength -ge $Config.MinSignalStrength) {
            $direction = if ((Get-Random -Minimum 0.0 -Maximum 1.0) -gt 0.5) { "BUY" } else { "SELL" }
            [void]$candidateSignals.Add(@{
                Symbol = $sym; SymbolName = $sym.Name; Profile = $profile
                ProfileName = $profile.Name; Direction = $direction; SignalStrength = $strength
            })
        }
    }
    Write-Phase 8 "Signal Generation" "OK" "Generated $($candidateSignals.Count) qualifying signals"

    # Phase 9: Confluence Scoring
    $confluenceSignals = [System.Collections.ArrayList]::new()
    foreach ($sig in $candidateSignals) {
        $cs = [math]::Min(98, [math]::Max(50, [math]::Round($sig.SignalStrength + (Get-Random -Minimum -5 -Maximum 10), 1)))
        if ($cs -ge $Config.MinSignalStrength) {
            $sig.ConfluenceScore = $cs
            [void]$confluenceSignals.Add($sig)
        }
    }
    Write-Phase 9 "Confluence Scoring" "OK" "$($confluenceSignals.Count) signals pass threshold"

    # Phase 10: Risk Assessment
    $currentDD = if ($peakEquity -gt 0) { ($peakEquity - $equity) / $peakEquity } else { 0 }
    $ddStatus = if ($currentDD -gt $Config.MaxDrawdown) { "FAIL" } elseif ($currentDD -gt 0.10) { "WARN" } else { "OK" }
    Write-Phase 10 "Risk Assessment" $ddStatus "Drawdown: $([math]::Round($currentDD * 100, 2))%"

    if ($currentDD -ge $Config.MaxDrawdown) {
        Write-Host "  *** CIRCUIT BREAKER: Max drawdown reached ***" -ForegroundColor Red
        for ($p = 11; $p -le 15; $p++) { Write-Phase $p "Blocked" "SKIP" "Circuit breaker active" }
        [void]$dailyResults.Add(@{ Day = $day; StartEquity = $dayStartEquity; EndEquity = $equity; PnL = 0; PnLPercent = 0; Trades = 0; Wins = 0; Losses = 0 })
        continue
    }

    # Phase 11: Trade Selection
    $selectedTrades = [System.Collections.ArrayList]::new()
    $sorted = $confluenceSignals | Sort-Object { $_.ConfluenceScore } -Descending | Select-Object -First $Config.MaxOpenPositions
    foreach ($sig in $sorted) {
        if ($dayTradesCount -ge $Config.MaxDailyTrades) { break }
        [void]$selectedTrades.Add($sig)
        $dayTradesCount++
    }
    Write-Phase 11 "Trade Selection" "OK" "Selected $($selectedTrades.Count) trades"

    # Phase 12: Position Sizing
    $sizedTrades = [System.Collections.ArrayList]::new()
    $dailyRiskUsed = 0
    $maxDailyRisk = $equity * $Config.MaxDailyLoss

    foreach ($trade in $selectedTrades) {
        $sym = $trade.Symbol
        $atrPips = if ($sym.PipSize -gt 0) { [math]::Round($sym.TypicalATR / $sym.PipSize, 0) } else { 20 }
        $slPips = [math]::Round($atrPips * 1.5, 0)
        $tpPips = [math]::Round($slPips * $Config.MinRiskReward, 0)
        $pipValue = $sym.ContractSize * $sym.PipSize

        $remainingRisk = $maxDailyRisk - $dailyRiskUsed
        $riskPerTrade = [math]::Min($equity * $Config.MaxPositionSize, $remainingRisk)
        if ($riskPerTrade -le 0) { continue }

        $lots = Calculate-PositionSize -Equity $equity -RiskPercent $Config.MaxPositionSize -SLPips $slPips -PipValue $pipValue
        $basePrice = Get-Random -Minimum 0.9 -Maximum 1.1
        $riskAmount = $lots * $slPips * $pipValue

        if ($trade.Direction -eq "BUY") {
            $entry = [math]::Round($basePrice, 6)
            $sl = [math]::Round($entry - ($slPips * $sym.PipSize), 6)
            $tp = [math]::Round($entry + ($tpPips * $sym.PipSize), 6)
        } else {
            $entry = [math]::Round($basePrice, 6)
            $sl = [math]::Round($entry + ($slPips * $sym.PipSize), 6)
            $tp = [math]::Round($entry - ($tpPips * $sym.PipSize), 6)
        }

        $dailyRiskUsed += $riskAmount
        $trade.Lots = $lots
        $trade.EntryPrice = $entry
        $trade.StopLoss = $sl
        $trade.TakeProfit = $tp
        $trade.SLPips = $slPips
        $trade.TPPips = $tpPips
        $trade.RiskReward = [math]::Round($tpPips / $slPips, 2)
        $trade.PipValue = $pipValue
        $trade.RiskAmount = $riskAmount
        [void]$sizedTrades.Add($trade)
    }

    Write-Phase 12 "Position Sizing" "OK" "Sized $($sizedTrades.Count) trades | Risk: `$$([math]::Round($dailyRiskUsed, 2))/$([math]::Round($maxDailyRisk, 2))"

    # Phase 13: Execution
    Write-Phase 13 "Order Execution" "OK" "Executing $($sizedTrades.Count) orders via MT5 bridge"

    # Phase 14: Position Management
    foreach ($trade in $sizedTrades) {
        $roll = Get-Random -Minimum 0.0 -Maximum 1.0
        $isWin = $roll -lt $trade.Profile.WinRate

        if ($isWin) {
            $rr = Get-Random -Minimum 1.5 -Maximum ($trade.Profile.AvgRR * 1.2)
            $pnl = $trade.Lots * $trade.TPPips * $trade.PipValue * $rr * 0.7
            $outcome = "WIN"
            $dayWins++
        } else {
            $lossR = Get-Random -Minimum 0.8 -Maximum 1.0
            $pnl = -$trade.RiskAmount * $lossR
            $outcome = "LOSS"
            $dayLosses++
        }

        $finalPnL = [math]::Round($pnl, 2)
        $duration = "{0:N0}h {1:N0}m" -f (Get-Random -Minimum 1 -Maximum 36), (Get-Random -Minimum 0 -Maximum 59)

        $equity += $finalPnL
        if ($equity -gt $peakEquity) { $peakEquity = $equity }
        $dailyPnL += $finalPnL

        [void]$allTrades.Add(@{
            SymbolName = $trade.SymbolName
            Direction = $trade.Direction
            Lots = $trade.Lots
            EntryPrice = $trade.EntryPrice
            StopLoss = $trade.StopLoss
            TakeProfit = $trade.TakeProfit
            FinalPnL = $finalPnL
            Outcome = $outcome
            Duration = $duration
            ProfileName = $trade.ProfileName
            SignalStrength = $trade.SignalStrength
            RiskReward = $trade.RiskReward
            Partial1 = if ($isWin) { "EXECUTED" } else { "SKIPPED" }
            Partial2 = if ($isWin) { "EXECUTED" } else { "SKIPPED" }
            Partial3 = "EXECUTED"
        })

        if ($Detailed) {
            $dirColor = if ($trade.Direction -eq "BUY") { "Green" } else { "Red" }
            $pnlColor = if ($finalPnL -ge 0) { "Green" } else { "Red" }
            $pnlSign = if ($finalPnL -ge 0) { "+" } else { "" }
            $pnlPct = ($finalPnL / $equity) * 100
            Write-Host ""
            Write-Host "  +--------------------------------------------+" -ForegroundColor DarkGray
            Write-Host "  | $($trade.Direction) $($trade.SymbolName) | $($trade.ProfileName)" -ForegroundColor $dirColor
            Write-Host "  | Entry: $($trade.EntryPrice)  SL: $($trade.StopLoss)  TP: $($trade.TakeProfit)" -ForegroundColor DarkGray
            Write-Host "  | Size: $($trade.Lots) lots  |  R:R: $($trade.RiskReward)" -ForegroundColor DarkGray
            Write-Host "  | Signal: $($trade.SignalStrength)% | Partials: $($trade.Partial1)/$($trade.Partial2)/$($trade.Partial3)" -ForegroundColor DarkGray
            Write-Host "  | P&L: ${pnlSign}`$$finalPnL (${pnlSign}$([math]::Round($pnlPct, 2))%) | $outcome | $duration" -ForegroundColor $pnlColor
            Write-Host "  +--------------------------------------------+" -ForegroundColor DarkGray
        }
    }

    Write-Phase 14 "Position Management" "OK" "Managed $($sizedTrades.Count) positions"

    # Phase 15: EOD Review
    $dayTradesTotal = $dayWins + $dayLosses
    $winRate = if ($dayTradesTotal -gt 0) { [math]::Round(($dayWins / $dayTradesTotal) * 100, 1) } else { 0 }
    $dailyPnLPct = if ($dayStartEquity -gt 0) { [math]::Round(($dailyPnL / $dayStartEquity) * 100, 4) } else { 0 }

    Write-Phase 15 "End-of-Day Review" "INFO" ""
    Write-Host ""
    Write-Host "  -- Day $day Summary --" -ForegroundColor Yellow
    Write-Host "    Trades: $dayTradesTotal | Wins: $dayWins | Losses: $dayLosses | Win Rate: $winRate%" -ForegroundColor White
    $pnlSign = if ($dailyPnL -ge 0) { "+" } else { "" }
    $pnlColor = if ($dailyPnL -ge 0) { "Green" } else { "Red" }
    Write-Host "    Daily P&L: ${pnlSign}`$$([math]::Round($dailyPnL, 2)) ($dailyPnLPct%)" -ForegroundColor $pnlColor
    Write-Host "    Equity: `$$([math]::Round($equity, 2)) | Peak: `$$([math]::Round($peakEquity, 2))" -ForegroundColor White

    if ($dailyPnLPct -ge ($Config.DailyTargetLock * 100)) {
        Write-Host "    *** DAILY TARGET LOCK: Trading stopped at $dailyPnLPct% ***" -ForegroundColor Yellow
    }

    [void]$dailyResults.Add(@{
        Day = $day; StartEquity = $dayStartEquity; EndEquity = $equity
        PnL = $dailyPnL; PnLPercent = $dailyPnLPct
        Trades = $dayTradesTotal; Wins = $dayWins; Losses = $dayLosses
    })
}

# ============================================================================
# FINAL REPORT
# ============================================================================

Write-Header "SIMULATION COMPLETE - FINAL REPORT" "Green"

$totalTrades = $allTrades.Count
$totalWins = 0
$totalLoss = 0.0
$totalProfit = 0.0
$totalLossAmt = 0.0

foreach ($t in $allTrades) {
    if ($t.Outcome -eq "WIN") {
        $totalWins++
        $totalProfit += $t.FinalPnL
    } else {
        $totalLoss++
        $totalLossAmt += [math]::Abs($t.FinalPnL)
    }
}

$totalLosses = $totalTrades - $totalWins
$overallWinRate = if ($totalTrades -gt 0) { [math]::Round(($totalWins / $totalTrades) * 100, 1) } else { 0 }
$totalPnL = $equity - $Config.StartingEquity
$totalPnLPct = [math]::Round(($totalPnL / $Config.StartingEquity) * 100, 2)
$maxDD = if ($peakEquity -gt 0) { [math]::Round((($peakEquity - $equity) / $peakEquity) * 100, 2) } else { 0 }
$profitFactor = if ($totalLossAmt -gt 0) { [math]::Round($totalProfit / $totalLossAmt, 2) } else { 999.99 }

Write-Host ""
Write-Host "  Starting Equity:     `$$([math]::Round($Config.StartingEquity, 2))" -ForegroundColor White
$pnlSign = if ($totalPnL -ge 0) { "+" } else { "" }
$pnlColor = if ($totalPnL -ge 0) { "Green" } else { "Red" }
Write-Host "  Final Equity:        `$$([math]::Round($equity, 2))" -ForegroundColor $pnlColor
Write-Host "  Total P&L:           ${pnlSign}`$$([math]::Round($totalPnL, 2)) ($totalPnLPct%)" -ForegroundColor $pnlColor
Write-Host ""
Write-Host "  Total Trades:        $totalTrades" -ForegroundColor White
Write-Host "  Winning Trades:      $totalWins" -ForegroundColor Green
Write-Host "  Losing Trades:       $totalLosses" -ForegroundColor Red
Write-Host "  Overall Win Rate:    $overallWinRate%" -ForegroundColor White
Write-Host "  Profit Factor:       $profitFactor" -ForegroundColor $(if ($profitFactor -gt 1.5) { "Green" } else { "Yellow" })
Write-Host ""
Write-Host "  -- Daily Breakdown --" -ForegroundColor Yellow
foreach ($dr in $dailyResults) {
    $drSign = if ($dr.PnL -ge 0) { "+" } else { "" }
    $drColor = if ($dr.PnL -ge 0) { "Green" } else { "Red" }
    Write-Host "    Day $($dr.Day): $($dr.Trades) trades | $($dr.Wins)W/$($dr.Losses)L | P&L: ${drSign}`$$([math]::Round($dr.PnL, 2)) ($($dr.PnLPercent)%)" -ForegroundColor $drColor
}

$avgDailyReturn = if ($Config.StartingEquity -gt 0 -and $TradingDays -gt 0) { $totalPnL / $TradingDays / $Config.StartingEquity } else { 0 }
$monthlyProjection = $Config.StartingEquity * [math]::Pow(1 + $avgDailyReturn, 22)
$annualProjection = $Config.StartingEquity * [math]::Pow(1 + $avgDailyReturn, 252)

Write-Host ""
Write-Host "  -- Projections (Compounded) --" -ForegroundColor Yellow
Write-Host "    Avg Daily Return:  $([math]::Round($avgDailyReturn * 100, 4))%" -ForegroundColor White
Write-Host "    Monthly (22 days): `$$([math]::Round($monthlyProjection, 2)) ($([math]::Round(($monthlyProjection / $Config.StartingEquity - 1) * 100, 2))%)" -ForegroundColor Cyan
Write-Host "    Annual (252 days): `$$([math]::Round($annualProjection, 2)) ($([math]::Round(($annualProjection / $Config.StartingEquity - 1) * 100, 2))%)" -ForegroundColor Cyan

Write-Host ""
Write-Host "  ========================================================" -ForegroundColor Green
Write-Host "    Simulation complete. All 15 phases executed.            " -ForegroundColor White
Write-Host "  ========================================================" -ForegroundColor Green
Write-Host ""
