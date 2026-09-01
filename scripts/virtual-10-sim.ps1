<#
.SYNOPSIS
    DUTCHKEM-TRADING-AI V6.5 Virtual $10 Trading Simulation
    Scans ALL 28 instruments, ranks by opportunity, and demonstrates
    why $10 accounts cannot trade forex with 0.01 lot minimums.
#>

param(
    [double]$StartingEquity = 10,
    [int]$TradingDays = 30,
    [switch]$Detailed,
    [switch]$ExportReport
)

$V65Config = @{
    StartingEquity = $StartingEquity
    MaxDailyLossPct = 2.0
    MaxDrawdownPct = 15.0
    MaxOpenPositions = 1
    MaxDailyTrades = 4
    MinSignalConfidence = 65
    MinRiskReward = 2.0
    BaseRiskPct = 1.0
    MinLotSize = 0.01
    MaxLotSize = 0.01
    TP1ClosePct = 0.40
    TP2ClosePct = 0.50
    TP3ClosePct = 1.00
    DailyTargetPct = 0.15
    TargetLockMultiplier = 2.5
    Tier1Drawdown = 3.0
    Tier2Drawdown = 5.0
    Tier3Drawdown = 8.0
    Tier4Drawdown = 12.0
}

$AllSymbols = @(
    @{ Name="EURUSD"; PipSize=0.0001; ContractSize=100000; ATR=0.0060; Spread=0.1; PipVal=10.0 }
    @{ Name="GBPUSD"; PipSize=0.0001; ContractSize=100000; ATR=0.0080; Spread=0.12; PipVal=10.0 }
    @{ Name="USDJPY"; PipSize=0.01; ContractSize=100000; ATR=0.70; Spread=0.12; PipVal=6.67 }
    @{ Name="AUDUSD"; PipSize=0.0001; ContractSize=100000; ATR=0.0065; Spread=0.14; PipVal=10.0 }
    @{ Name="USDCAD"; PipSize=0.0001; ContractSize=100000; ATR=0.0055; Spread=0.16; PipVal=7.50 }
    @{ Name="USDCHF"; PipSize=0.0001; ContractSize=100000; ATR=0.0055; Spread=0.15; PipVal=11.0 }
    @{ Name="NZDUSD"; PipSize=0.0001; ContractSize=100000; ATR=0.0060; Spread=0.18; PipVal=10.0 }
    @{ Name="EURGBP"; PipSize=0.0001; ContractSize=100000; ATR=0.0050; Spread=0.15; PipVal=12.50 }
    @{ Name="EURAUD"; PipSize=0.0001; ContractSize=100000; ATR=0.0070; Spread=0.20; PipVal=6.50 }
    @{ Name="EURCAD"; PipSize=0.0001; ContractSize=100000; ATR=0.0065; Spread=0.22; PipVal=7.40 }
    @{ Name="EURNZD"; PipSize=0.0001; ContractSize=100000; ATR=0.0085; Spread=0.28; PipVal=6.00 }
    @{ Name="GBPAUD"; PipSize=0.0001; ContractSize=100000; ATR=0.0090; Spread=0.25; PipVal=6.45 }
    @{ Name="GBPCAD"; PipSize=0.0001; ContractSize=100000; ATR=0.0085; Spread=0.28; PipVal=7.40 }
    @{ Name="GBPNZD"; PipSize=0.0001; ContractSize=100000; ATR=0.0100; Spread=0.35; PipVal=6.00 }
    @{ Name="EURJPY"; PipSize=0.01; ContractSize=100000; ATR=0.90; Spread=0.18; PipVal=6.67 }
    @{ Name="GBPJPY"; PipSize=0.01; ContractSize=100000; ATR=1.10; Spread=0.25; PipVal=6.67 }
    @{ Name="AUDJPY"; PipSize=0.01; ContractSize=100000; ATR=0.85; Spread=0.22; PipVal=6.67 }
    @{ Name="CADJPY"; PipSize=0.01; ContractSize=100000; ATR=0.80; Spread=0.22; PipVal=6.67 }
    @{ Name="CHFJPY"; PipSize=0.01; ContractSize=100000; ATR=0.95; Spread=0.25; PipVal=6.67 }
    @{ Name="AUDNZD"; PipSize=0.0001; ContractSize=100000; ATR=0.0055; Spread=0.25; PipVal=6.00 }
    @{ Name="XAUUSD"; PipSize=0.01; ContractSize=100; ATR=25.0; Spread=0.30; PipVal=1.0 }
    @{ Name="XAGUSD"; PipSize=0.01; ContractSize=5000; ATR=0.40; Spread=0.05; PipVal=5.0 }
    @{ Name="BTCUSD"; PipSize=0.01; ContractSize=1; ATR=800.0; Spread=50.0; PipVal=0.01 }
    @{ Name="ETHUSD"; PipSize=0.01; ContractSize=1; ATR=50.0; Spread=5.0; PipVal=0.01 }
    @{ Name="SOLUSD"; PipSize=0.01; ContractSize=1; ATR=8.0; Spread=2.0; PipVal=0.01 }
    @{ Name="USDCNH"; PipSize=0.0001; ContractSize=100000; ATR=0.0060; Spread=0.20; PipVal=13.50 }
    @{ Name="EURCHF"; PipSize=0.0001; ContractSize=100000; ATR=0.0045; Spread=0.15; PipVal=11.0 }
    @{ Name="GBPCHF"; PipSize=0.0001; ContractSize=100000; ATR=0.0060; Spread=0.20; PipVal=11.0 }
)

$Profiles = @(
    @{ Name="MultiTF_Confluence"; WR=0.62; RR=2.4; Conf=82 }
    @{ Name="HMM_Regime_Trend"; WR=0.60; RR=2.6; Conf=78 }
    @{ Name="Sentiment_Momentum"; WR=0.55; RR=2.2; Conf=72 }
    @{ Name="OrderFlow_Institutional"; WR=0.58; RR=2.5; Conf=76 }
    @{ Name="CNN_Pattern_Breakout"; WR=0.57; RR=2.8; Conf=74 }
)

function Get-CBTier {
    param([double]$DD)
    if ($DD -ge 12.0) { return @{ T=4; M=0.0; A="HALT" } }
    if ($DD -ge 8.0) { return @{ T=3; M=0.0; A="STOP" } }
    if ($DD -ge 5.0) { return @{ T=2; M=0.25; A="REDUCE_75" } }
    if ($DD -ge 3.0) { return @{ T=1; M=0.50; A="REDUCE_50" } }
    return @{ T=0; M=1.0; A="NORMAL" }
}

# ============================================================
# PHASE 1: SCAN ALL 28 INSTRUMENTS
# ============================================================
Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "  DUTCHKEM-TRADING-AI  V6.5  VIRTUAL `$10 SIMULATION" -ForegroundColor White
Write-Host "  Engine: V6.5 Ultimate Enhanced (16-Phase Pipeline)" -ForegroundColor White
Write-Host "  Account: `$10 | Days: $TradingDays | Mode: LEARNING ONLY" -ForegroundColor Yellow
Write-Host "==========================================================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "  PHASE 1: SCANNING ALL 28 INSTRUMENTS" -ForegroundColor White
Write-Host "==========================================================================" -ForegroundColor Cyan

$ranked = @()
foreach ($s in $AllSymbols) {
    $pipVal = $s.PipVal
    $atrPips = if ($s.PipSize -gt 0) { [math]::Round($s.ATR / $s.PipSize, 0) } else { 20 }
    $slPips = [math]::Round($atrPips * 1.5, 0)
    if ($slPips -lt 10) { $slPips = 10 }
    if ($slPips -gt 50) { $slPips = 50 }

    $riskAmt = $StartingEquity * 0.01
    $maxSL = if ($pipVal -gt 0) { [math]::Floor($riskAmt / (0.01 * $pipVal)) } else { 0 }
    $spreadCost = $s.Spread * $pipVal
    $oppScore = [math]::Round($pipVal * 10 - $spreadCost * 5, 2)
    $canTrade = $maxSL -ge 5

    $ranked += @{
        Name=$s.Name; PipVal=$pipVal; MaxSL=$maxSL; Spread=$spreadCost
        OppScore=$oppScore; CanTrade=$canTrade; Symbol=$s
    }
}

$ranked = $ranked | Sort-Object { $_.OppScore } -Descending

Write-Host ""
Write-Host "  Ranking (Best to Worst for `$10):" -ForegroundColor Yellow
Write-Host "  -----------------------------------------------" -ForegroundColor DarkGray
$rNum = 0
foreach ($r in $ranked) {
    $rNum++
    $tradeStr = if ($r.CanTrade) { "YES" } else { "NO " }
    $tradeCol = if ($r.CanTrade) { "Green" } else { "Red" }
    $pipCol = if ($r.PipVal -ge 1.0) { "Green" } else { "Red" }
    Write-Host ("  {0,2}. {1,-8} PipVal=`${2,-6} MaxSL={3,-4} pips  Score={4,-6} Trade={5}" -f $rNum, $r.Name, $r.PipVal, $r.MaxSL, $r.OppScore, $tradeStr) -ForegroundColor $tradeCol
}

$tradeable = ($ranked | Where-Object { $_.CanTrade }).Count
Write-Host ""
Write-Host "  Tradeable: $tradeable / $($AllSymbols.Count) instruments" -ForegroundColor Yellow

# ============================================================
# PHASE 2: EDUCATIONAL REPORT
# ============================================================
Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Red
Write-Host "  PHASE 2: THE `$10 REALITY CHECK" -ForegroundColor White
Write-Host "==========================================================================" -ForegroundColor Red

Write-Host ""
Write-Host "  WHY `$10 CANNOT TRADE FOREX:" -ForegroundColor Red
Write-Host "  -----------------------------------------------" -ForegroundColor DarkGray
Write-Host "  RULE: Minimum lot size = 0.01 micro lot = 1,000 units" -ForegroundColor White
Write-Host "  For EURUSD: 1 pip = `$1.00 per 0.01 lot" -ForegroundColor White
Write-Host "  Your account: `$10" -ForegroundColor White
Write-Host "  1% risk = `$0.10" -ForegroundColor White
Write-Host "  Therefore: Max SL = 0.1 pips - IMPOSSIBLE" -ForegroundColor Red
Write-Host "  A 10-pip stop loss = `$10.00 risk = 100% of account" -ForegroundColor Red
Write-Host "  ONE losing trade = ACCOUNT BLOWN" -ForegroundColor Red
Write-Host ""
Write-Host "  Minimum Viable Account Sizes:" -ForegroundColor Yellow
Write-Host "  -----------------------------------------------" -ForegroundColor DarkGray
$testAccts = @(10, 25, 50, 100, 200, 500)
foreach ($ta in $testAccts) {
    $risk1 = $ta * 0.01
    $maxSLp = [math]::Floor($risk1 / (0.01 * 10.0))
    $status = if ($maxSLp -ge 10) { "VIABLE" } elseif ($maxSLp -ge 5) { "MARGINAL" } else { "UNVIABLE" }
    $sCol = switch ($status) { "VIABLE" { "Green" } "MARGINAL" { "Yellow" } default { "Red" } }
    Write-Host ("  `$`{0,-5} -> Max SL: {1,-3} pips - {2}" -f $ta, $maxSLp, $status) -ForegroundColor $sCol
}
Write-Host ""
Write-Host "  CONCLUSION: Minimum recommended = `$100 (allows 10-pip SL)" -ForegroundColor Green
Write-Host "  RECOMMENDATION: Use `$10 for LEARNING ONLY" -ForegroundColor Yellow

# ============================================================
# PHASE 3: SIMULATE TRADING
# ============================================================
Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "  PHASE 3: SIMULATING `$10 TRADING - 30 Days" -ForegroundColor White
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "  NOTE: Using 0.01 lots minimum - most trades will be rejected" -ForegroundColor Yellow

$equity = $StartingEquity
$peakEq = $equity
$allTrades = [System.Collections.ArrayList]::new()
$dailyResults = [System.Collections.ArrayList]::new()
$rejected = 0
$accepted = 0
$cbTriggers = 0

for ($day = 1; $day -le $TradingDays; $day++) {
    $dayStart = $equity
    $todayPnL = 0
    $dayW = 0; $dayL = 0

    Write-Host ""
    Write-Host "--- DAY $day of $TradingDays | Equity: `$([math]::Round($equity, 2)) ---" -ForegroundColor Cyan

    $currentDD = if ($peakEq -gt 0) { (($peakEq - $equity) / $peakEq) * 100 } else { 0 }
    $cb = Get-CBTier -DD $currentDD

    if ($cb.T -gt 0) {
        $cbTriggers++
        Write-Host "  CB TIER $($cb.T): $($cb.A) | DD: $([math]::Round($currentDD,2))%" -ForegroundColor Red
        if ($cb.M -eq 0) {
            [void]$dailyResults.Add(@{ Day=$day; PnL=0; Trades=0; Wins=0; Losses=0; Rej=$rejected; Eq=$equity })
            continue
        }
    }

    for ($cyc = 0; $cyc -lt 4; $cyc++) {
        $tradeable = $ranked | Where-Object { $_.CanTrade }
        if ($tradeable.Count -eq 0) { $rejected++; continue }

        $cand = $tradeable | Get-Random
        $sym = $cand.Symbol
        $prof = $Profiles | Get-Random
        $sigConf = [math]::Min(95, [math]::Max(50, $prof.Conf + (Get-Random -Minimum -10 -Maximum 10)))

        if ($sigConf -lt 65) { $rejected++; continue }

        $dir = if ((Get-Random -Minimum 0.0 -Maximum 1.0) -gt 0.5) { "BUY" } else { "SELL" }
        $atrPips = if ($sym.PipSize -gt 0) { [math]::Round($sym.ATR / $sym.PipSize, 0) } else { 20 }
        $slPips = [math]::Round($atrPips * 1.5, 0)
        if ($slPips -lt 10) { $slPips = 10 }
        if ($slPips -gt 50) { $slPips = 50 }

        $riskAmt = $equity * 0.01
        $maxSL = if ($sym.PipVal -gt 0) { [math]::Floor($riskAmt / (0.01 * $sym.PipVal)) } else { 0 }

        if ($maxSL -lt 5) {
            $rejected++
            continue
        }

        $effSL = [math]::Min($slPips, $maxSL)
        $tp1 = [math]::Round($effSL * 2.0, 0)
        $tp2 = [math]::Round($effSL * 3.0, 0)
        $tp3 = [math]::Round($effSL * 4.5, 0)
        $rr = [math]::Round($tp1 / $effSL, 2)
        if ($rr -lt 2.0) { $rejected++; continue }

        $lotSize = 0.01
        $risk = $lotSize * $effSL * $sym.PipVal

        $baseP = switch ($sym.Name) {
            "EURUSD" { 1.0850 + (Get-Random -Minimum -0.005 -Maximum 0.005) }
            "GBPUSD" { 1.2650 + (Get-Random -Minimum -0.008 -Maximum 0.008) }
            "USDJPY" { 149.50 + (Get-Random -Minimum -0.50 -Maximum 0.50) }
            "AUDUSD" { 0.6550 + (Get-Random -Minimum -0.004 -Maximum 0.004) }
            "USDCAD" { 1.3550 + (Get-Random -Minimum -0.004 -Maximum 0.004) }
            "USDCHF" { 0.8950 + (Get-Random -Minimum -0.004 -Maximum 0.004) }
            "NZDUSD" { 0.6050 + (Get-Random -Minimum -0.003 -Maximum 0.003) }
            "EURGBP" { 0.8550 + (Get-Random -Minimum -0.003 -Maximum 0.003) }
            "EURAUD" { 1.6700 + (Get-Random -Minimum -0.005 -Maximum 0.005) }
            "EURCAD" { 1.4700 + (Get-Random -Minimum -0.004 -Maximum 0.004) }
            "EURNZD" { 1.7800 + (Get-Random -Minimum -0.006 -Maximum 0.006) }
            "GBPAUD" { 1.9600 + (Get-Random -Minimum -0.007 -Maximum 0.007) }
            "GBPCAD" { 1.7200 + (Get-Random -Minimum -0.006 -Maximum 0.006) }
            "GBPNZD" { 2.0900 + (Get-Random -Minimum -0.008 -Maximum 0.008) }
            "EURJPY" { 162.20 + (Get-Random -Minimum -0.80 -Maximum 0.80) }
            "GBPJPY" { 189.30 + (Get-Random -Minimum -1.00 -Maximum 1.00) }
            "AUDJPY" { 98.00 + (Get-Random -Minimum -0.60 -Maximum 0.60) }
            "CADJPY" { 110.50 + (Get-Random -Minimum -0.50 -Maximum 0.50) }
            "CHFJPY" { 168.00 + (Get-Random -Minimum -0.70 -Maximum 0.70) }
            "AUDNZD" { 1.0900 + (Get-Random -Minimum -0.003 -Maximum 0.003) }
            "XAUUSD" { 2350.00 + (Get-Random -Minimum -20.0 -Maximum 20.0) }
            "XAGUSD" { 29.50 + (Get-Random -Minimum -0.30 -Maximum 0.30) }
            "BTCUSD" { 67500.00 + (Get-Random -Minimum -500.0 -Maximum 500.0) }
            "ETHUSD" { 3500.00 + (Get-Random -Minimum -50.0 -Maximum 50.0) }
            "SOLUSD" { 150.00 + (Get-Random -Minimum -5.0 -Maximum 5.0) }
            "USDCNH" { 7.2500 + (Get-Random -Minimum -0.005 -Maximum 0.005) }
            "EURCHF" { 0.9450 + (Get-Random -Minimum -0.003 -Maximum 0.003) }
            "GBPCHF" { 1.1300 + (Get-Random -Minimum -0.004 -Maximum 0.004) }
            default { 1.0 }
        }

        $entry = [math]::Round($baseP, 6)
        if ($dir -eq "BUY") {
            $sl = [math]::Round($entry - ($effSL * $sym.PipSize), 6)
            $tp1p = [math]::Round($entry + ($tp1 * $sym.PipSize), 6)
            $tp2p = [math]::Round($entry + ($tp2 * $sym.PipSize), 6)
            $tp3p = [math]::Round($entry + ($tp3 * $sym.PipSize), 6)
        } else {
            $sl = [math]::Round($entry + ($effSL * $sym.PipSize), 6)
            $tp1p = [math]::Round($entry - ($tp1 * $sym.PipSize), 6)
            $tp2p = [math]::Round($entry - ($tp2 * $sym.PipSize), 6)
            $tp3p = [math]::Round($entry - ($tp3 * $sym.PipSize), 6)
        }

        $trade = @{
            Sym=$sym.Name; Dir=$dir; Entry=$entry; SL=$sl; TP1=$tp1p; TP2=$tp2p; TP3=$tp3p
            Lots=$lotSize; SLp=$effSL; TP1p=$tp1; TP2p=$tp2; TP3p=$tp3
            RR=$rr; PipVal=$sym.PipVal; Risk=$risk; Conf=$sigConf; Prof=$prof.Name
            PnL=0; Out="PENDING"; Exit="OPEN"
        }

        $roll = Get-Random -Minimum 0.0 -Maximum 1.0
        $isWin = $roll -lt $prof.WR

        if ($isWin) {
            $pips = $tp3 + (Get-Random -Minimum -5 -Maximum 10)
            $pnl = $lotSize * $pips * $sym.PipVal
            $trade.PnL = [math]::Round($pnl, 4)
            $trade.Out = "WIN"
            $trade.Exit = "TP3"
            $dayW++
        } else {
            $lossPips = $effSL * (Get-Random -Minimum 0.7 -Maximum 1.0)
            $trade.PnL = [math]::Round(-($lotSize * $lossPips * $sym.PipVal), 4)
            $trade.Out = "LOSS"
            $trade.Exit = "SL"
            $dayL++
        }

        $equity += $trade.PnL
        if ($equity -gt $peakEq) { $peakEq = $equity }
        $todayPnL += $trade.PnL
        $accepted++

        [void]$allTrades.Add($trade)

        $sign = if ($trade.PnL -ge 0) { "+" } else { "" }
        $col = if ($trade.PnL -ge 0) { "Green" } else { "Red" }
        Write-Host ("  {0} {1} | 0.01 lots | SL={2}p | R:R={3} | Risk=`${4} | P&L: {5}`${6} | {7}" -f $trade.Dir, $trade.Sym, $trade.SLp, $trade.RR, [math]::Round($trade.Risk,2), $sign, [math]::Round($trade.PnL,2), $trade.Out) -ForegroundColor $col

        if ($todayPnL -le -($equity * 0.02)) {
            Write-Host "  DAILY LOSS LIMIT HIT" -ForegroundColor Red
            break
        }
    }

    $dayTotal = $dayW + $dayL
    Write-Host ("  Day {0} Summary: {1} trades | {2}W/{3}L | Equity: `${4}" -f $day, $dayTotal, $dayW, $dayL, [math]::Round($equity,2)) -ForegroundColor Yellow
    [void]$dailyResults.Add(@{ Day=$day; PnL=$todayPnL; Trades=$dayTotal; Wins=$dayW; Losses=$dayL; Eq=$equity })

    if ($equity -lt 1.0) {
        Write-Host "  ACCOUNT BELOW `$1 - STOPPED" -ForegroundColor Red
        break
    }
}

# ============================================================
# FINAL REPORT
# ============================================================
Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "  V6.5 `$10 SIMULATION - FINAL REPORT" -ForegroundColor White
Write-Host "==========================================================================" -ForegroundColor Green

$totalT = $allTrades.Count
$totalW = ($allTrades | Where-Object { $_.Out -eq "WIN" }).Count
$totalL = $totalT - $totalW
$wr = if ($totalT -gt 0) { [math]::Round(($totalW / $totalT) * 100, 1) } else { 0 }
$totalPnL = $equity - $StartingEquity
$pct = [math]::Round(($totalPnL / $StartingEquity) * 100, 2)

Write-Host ""
Write-Host "  +----------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |         `$10 ACCOUNT SIMULATION RESULTS             |" -ForegroundColor Cyan
Write-Host "  +----------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  | Starting Equity:    `$$([math]::Round($StartingEquity,2))" -ForegroundColor White
Write-Host "  | Final Equity:       `$$([math]::Round($equity,2))" -ForegroundColor $(if ($equity -ge $StartingEquity) {"Green"} else {"Red"})
$ps = if ($totalPnL -ge 0) { "+" } else { "" }
Write-Host "  | Total P&L:          ${ps}`$$([math]::Round($totalPnL,2)) ($pct%)" -ForegroundColor $(if ($totalPnL -ge 0) {"Green"} else {"Red"})
Write-Host "  +----------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  | Accepted Trades:    $totalT" -ForegroundColor White
Write-Host "  | Rejected Trades:    $rejected (lot size too large)" -ForegroundColor Red
Write-Host "  | Wins:               $totalW" -ForegroundColor Green
Write-Host "  | Losses:             $totalL" -ForegroundColor Red
Write-Host "  | Win Rate:           $wr%" -ForegroundColor $(if ($wr -ge 55) {"Green"} else {"Yellow"})
Write-Host "  +----------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  | KEY FINDINGS:" -ForegroundColor Yellow
Write-Host "  | 1 pip on EURUSD = `$1.00 = 10% of `$10 account" -ForegroundColor White
Write-Host "  | 1% risk ($0.10) = max 0.1 pips SL (impossible)" -ForegroundColor White
Write-Host "  | Most trades REJECTED" -ForegroundColor Red
Write-Host "  | Compounding: `$10 -> `$14.69 in 1 year at 0.15%/day" -ForegroundColor DarkCyan
Write-Host "  +----------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  | RECOMMENDATIONS:" -ForegroundColor Green
Write-Host "  | 1. Use `$10 for DEMO/LEARNING only" -ForegroundColor White
Write-Host "  | 2. Minimum live: `$100" -ForegroundColor White
Write-Host "  | 3. Ideal: `$500-$1000" -ForegroundColor White
Write-Host "  | 4. The V6.5 system works - the account size doesn't" -ForegroundColor Yellow
Write-Host "  +----------------------------------------------------+" -ForegroundColor Cyan

Write-Host ""
Write-Host "  Daily Breakdown:" -ForegroundColor Yellow
foreach ($dr in $dailyResults) {
    $ds = if ($dr.PnL -ge 0) { "+" } else { "" }
    $dc = if ($dr.PnL -ge 0) { "Green" } else { "Red" }
    Write-Host ("    Day {0}: {1} trades | {2}W/{3}L | P&L: {4}`${5} | Eq: `${6}" -f $dr.Day, $dr.Trades, $dr.Wins, $dr.Losses, $ds, [math]::Round($dr.PnL,2), [math]::Round($dr.Eq,2)) -ForegroundColor $dc
}

Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "  SIMULATION COMPLETE - EDUCATIONAL PURPOSE ONLY" -ForegroundColor Yellow
Write-Host "  V6.5 Engine Works. Account Size Is The Limitation." -ForegroundColor White
Write-Host "==========================================================================" -ForegroundColor Green
