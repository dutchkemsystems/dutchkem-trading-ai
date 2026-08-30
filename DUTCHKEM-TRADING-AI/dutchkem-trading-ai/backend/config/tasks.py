# Dutchkem Trading AI — Celery Tasks
# Background tasks for indicator calculation, signal generation, and EA deployment

import json
import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("tasks")


@shared_task(bind=True, max_retries=3)
def calculate_indicators(self, symbol_id: str, timeframe_code: str):
    """
    Calculate indicators for a symbol and timeframe

    This task is triggered when new market data arrives.
    Fetches real OHLCV data from MT5 via MCP integration.
    """
    try:
        import asyncio
        from strategies.timeframe_strategies import calculate_signal
        from indicators.models import Indicator, IndicatorValue, Timeframe
        from trading.models import Symbol
        from mcp_integration.services import mt5_service

        symbol = Symbol.objects.get(id=symbol_id)
        timeframe = Timeframe.objects.get(code=timeframe_code)

        # Fetch real OHLCV data from MT5 via MCP
        loop = asyncio.new_event_loop()
        try:
            candles = loop.run_until_complete(
                mt5_service.get_candles(symbol.name, timeframe_code, count=200)
            )
        finally:
            loop.close()

        if not candles or not isinstance(candles, list) or len(candles) < 5:
            logger.warning("Insufficient candle data for %s %s, using minimal fallback", symbol.name, timeframe_code)
            candles = []

        # Build OHLCV arrays from fetched candles
        if candles:
            ohlcv_data = {
                "open": [float(c.get("open", 0)) for c in candles],
                "high": [float(c.get("high", 0)) for c in candles],
                "low": [float(c.get("low", 0)) for c in candles],
                "close": [float(c.get("close", 0)) for c in candles],
                "volume": [int(c.get("volume", 0)) for c in candles],
            }
        else:
            # Fallback empty — calculation will return neutral
            ohlcv_data = {
                "open": [], "high": [], "low": [],
                "close": [], "volume": [],
            }

        # Calculate signal
        result = calculate_signal(timeframe_code, ohlcv_data)

        # Store indicator values
        IndicatorValue.objects.create(
            symbol=symbol,
            indicator=Indicator.objects.get(name="COMPOSITE"),
            timeframe=timeframe,
            timestamp=timezone.now(),
            value=result.get("indicators", {}),
            signal=result.get("signal", "NEUTRAL"),
        )

        return {
            "status": "success",
            "symbol": symbol.name,
            "timeframe": timeframe_code,
            "signal": result.get("signal"),
            "strength": result.get("strength"),
        }

    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_signals(self, symbol_id: str):
    """
    Generate multi-timeframe signals for a symbol

    This task runs periodically to generate trading signals.
    Fetches real OHLCV data from MT5 via MCP integration.
    """
    try:
        import asyncio
        from decimal import Decimal

        from strategies.confluence import TimeframeSignal, confluence_engine
        from strategies.timeframe_strategies import calculate_signal

        from signals.models import ConfluenceScore, Signal
        from trading.models import Symbol
        from indicators.models import Timeframe as TFModel
        from mcp_integration.services import mt5_service

        symbol = Symbol.objects.get(id=symbol_id)

        # Get signals for all timeframes using real MT5 data
        timeframe_signals = {}
        timeframes = ["M5", "M15", "M30", "H1", "H2", "H4"]

        # Fetch data for all timeframes via MT5 in parallel-style
        loop = asyncio.new_event_loop()
        try:
            for tf in timeframes:
                try:
                    candles = loop.run_until_complete(
                        mt5_service.get_candles(symbol.name, tf, count=200)
                    )
                except Exception as tf_exc:
                    logger.warning("MT5 fetch failed for %s %s: %s", symbol.name, tf, tf_exc)
                    candles = []

                if candles and isinstance(candles, list) and len(candles) >= 3:
                    ohlcv_data = {
                        "open": [float(c.get("open", 0)) for c in candles],
                        "high": [float(c.get("high", 0)) for c in candles],
                        "low": [float(c.get("low", 0)) for c in candles],
                        "close": [float(c.get("close", 0)) for c in candles],
                        "volume": [int(c.get("volume", 0)) for c in candles],
                    }
                else:
                    ohlcv_data = {
                        "open": [], "high": [], "low": [],
                        "close": [], "volume": [],
                    }

                result = calculate_signal(tf, ohlcv_data)

                timeframe_signals[tf] = TimeframeSignal(
                    timeframe=tf,
                    signal_type=result.get("signal", "NEUTRAL"),
                    strength=Decimal(str(result.get("strength", 0))),
                    indicators=result.get("indicators", {}),
                    stop_loss_pips=result.get("stop_loss_pips", 50),
                    take_profit_pips=result.get("take_profit_pips", 100),
                )
        finally:
            loop.close()

        # Calculate confluence
        confluence_result = confluence_engine.calculate_confluence(
            symbol=symbol.name, timeframe_signals=timeframe_signals
        )

        # Store confluence score
        ConfluenceScore.objects.create(
            symbol=symbol,
            m5_score=confluence_result.timeframe_scores.get("M5", 0),
            m15_score=confluence_result.timeframe_scores.get("M15", 0),
            m30_score=confluence_result.timeframe_scores.get("M30", 0),
            h1_score=confluence_result.timeframe_scores.get("H1", 0),
            h2_score=confluence_result.timeframe_scores.get("H2", 0),
            h4_score=confluence_result.timeframe_scores.get("H4", 0),
            total_score=confluence_result.total_score,
            direction=confluence_result.direction.value,
            higher_tf_agreement=confluence_result.higher_tf_agreement,
            all_tf_aligned=confluence_result.all_tf_aligned,
        )

        # Store signal if confluence is strong enough
        if confluence_engine.should_trade(confluence_result):
            # Resolve the H1 timeframe as the primary timeframe for multi-timeframe signals
            h1_tf = TFModel.objects.filter(code="H1").first()
            Signal.objects.create(
                symbol=symbol,
                timeframe=h1_tf,
                signal_type=confluence_result.direction.value,
                strength=confluence_result.total_score,
                confluence_score=confluence_result.total_score,
                mtf_confluence_score=confluence_result.total_score,
                h4_trend=timeframe_signals.get("H4", {}).signal_type if "H4" in timeframe_signals else "",
                h1_trend=timeframe_signals.get("H1", {}).signal_type if "H1" in timeframe_signals else "",
                m15_trend=timeframe_signals.get("M15", {}).signal_type if "M15" in timeframe_signals else "",
                risk_reward_ratio=confluence_result.risk_reward_ratio,
                confidence=confluence_result.confidence,
                generated_by="confluence_engine",
            )

        return {
            "status": "success",
            "symbol": symbol.name,
            "confluence_score": str(confluence_result.total_score),
            "direction": confluence_result.direction.value,
            "should_trade": confluence_engine.should_trade(confluence_result),
        }

    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def deploy_ea(self, ea_id: str):
    """
    Deploy Expert Advisor to MT5

    This task compiles and deploys EA code to MetaTrader 5
    """
    try:
        from eas.mql5_generator import mql5_generator
        from mcp_integration.services import mt5_service as mcp_service

        from expert_advisors.models import EADeployment, ExpertAdvisor

        ea = ExpertAdvisor.objects.get(id=ea_id)

        # Generate MQL5 code if not already generated
        if not ea.mql5_code:
            code = mql5_generator.generate_ea(
                name=ea.name,
                symbol=ea.symbol.name,
                timeframe=ea.timeframe.code,
                strategy_type=ea.strategy_type,
                parameters=ea.parameters,
                risk_per_trade=float(ea.risk_per_trade),
                use_stop_loss=ea.use_stop_loss,
                use_take_profit=ea.use_take_profit,
                use_trailing_stop=ea.trailing_stop,
                trailing_stop_pips=ea.trailing_stop_pips,
            )
            ea.mql5_code = code
            ea.save()

        # Deploy to MT5
        result = mcp_service.deploy_ea(
            name=ea.name, code=ea.mql5_code, symbol=ea.symbol.name, timeframe=ea.timeframe.code
        )

        # Create deployment record
        deployment = EADeployment.objects.create(
            ea=ea,
            mt5_account=ea.user.mt5_account,
            mt5_server=ea.user.mt5_server,
            status="ACTIVE" if result.success else "ERROR",
        )

        # Update EA status
        ea.status = "LIVE"
        ea.deployed_at = deployment.deployed_at
        ea.save()

        return {
            "status": "success",
            "ea_name": ea.name,
            "deployment_id": str(deployment.id),
            "mt5_status": result.data.get("status"),
        }

    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task
def monitor_drawdown():
    """
    Monitor drawdown for all users

    This task runs every minute to check drawdown limits
    """
    from django.contrib.auth import get_user_model

    from risk_management.models import DrawdownMonitor, RiskAlert, RiskParameter

    User = get_user_model()
    risk_params = RiskParameter.objects.filter(is_active=True).first()

    if not risk_params:
        return

    for user in User.objects.filter(is_active=True):
        monitor, _ = DrawdownMonitor.objects.get_or_create(
            user=user,
            defaults={
                "peak_equity": user.equity,
                "current_equity": user.equity,
                "starting_equity_today": user.equity,
                "drawdown_percent": 0,
            },
        )

        # Update current equity
        monitor.current_equity = user.equity

        # Calculate drawdown
        if monitor.peak_equity > 0:
            monitor.drawdown_percent = ((monitor.peak_equity - user.equity) / monitor.peak_equity) * 100

        # Check circuit breakers
        alerts = monitor.check_circuit_breaker(risk_params)

        # Create alerts if needed
        for alert_type, severity, message in alerts:
            RiskAlert.objects.create(
                user=user,
                alert_type=alert_type,
                severity=severity,
                message=message,
                data={"equity": str(user.equity), "drawdown": str(monitor.drawdown_percent)},
            )

        monitor.save()


@shared_task
def reset_daily_counters():
    """
    Reset daily counters for all users

    This task runs at midnight (00:00 UTC)
    """
    from django.contrib.auth import get_user_model

    from risk_management.models import DailyPerformance, DrawdownMonitor

    User = get_user_model()

    for user in User.objects.filter(is_active=True):
        # Reset drawdown monitor
        monitor = DrawdownMonitor.objects.filter(user=user).first()
        if monitor:
            monitor.reset_daily()

        # Create daily performance record
        DailyPerformance.objects.get_or_create(
            user=user,
            date=timezone.now().date(),
            defaults={
                "starting_equity": user.equity,
                "ending_equity": user.equity,
                "daily_pnl": 0,
                "daily_pnl_percent": 0,
            },
        )


@shared_task
def sync_mt5_data():
    """
    Sync account data from MT5

    This task runs every 5 minutes to sync account data
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    for user in User.objects.filter(is_active=True, mt5_account__isnull=False):
        try:
            from mcp_integration.services import mt5_service
            import asyncio

            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(mt5_service.get_account_info())
                if result.get("success"):
                    user.balance = result.get("data", {}).get("balance", user.balance)
                    user.equity = result.get("data", {}).get("equity", user.equity)
                    user.save()
            finally:
                loop.close()
        except Exception as exc:
            logger.error("MT5 sync failed for user %s: %s", user.username, exc)


@shared_task
def ingest_market_data():
    """
    Ingest live market data from MT5

    This task runs every minute to update live prices
    """
    from market_data.models import LivePrice
    from trading.models import Symbol

    for symbol in Symbol.objects.filter(is_active=True):
        try:
            from mcp_integration.services import mt5_service
            import asyncio

            loop = asyncio.new_event_loop()
            try:
                tick = loop.run_until_complete(mt5_service.get_tick_data(symbol.name))
                if tick:
                    LivePrice.objects.update_or_create(
                        symbol=symbol,
                        defaults={
                            "bid": tick.get("bid", 0),
                            "ask": tick.get("ask", 0),
                            "spread": tick.get("spread", 0),
                        },
                    )
            finally:
                loop.close()
        except Exception as exc:
            logger.error("Market data ingestion failed for symbol %s: %s", symbol.name, exc)


@shared_task
def calculate_performance():
    """
    Calculate and cache trading performance metrics

    This task runs every 5 minutes to update analytics caches
    """
    from analytics.models import CachedDailyPerformance, CachedSymbolBreakdown, CachedTradeSummary
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from trading.models import Trade

    User = get_user_model()
    today = timezone.now().date()

    for user in User.objects.filter(is_active=True):
        all_trades = Trade.objects.filter(user=user, status="CLOSED")

        # Cache today's performance
        today_trades = all_trades.filter(closed_at__date=today)
        daily_pnl = sum(float(t.profit_loss or 0) for t in today_trades)
        wins = today_trades.filter(profit_loss__gt=0).count()
        losses = today_trades.filter(profit_loss__lt=0).count()

        CachedDailyPerformance.objects.update_or_create(
            user=user,
            date=today,
            defaults={
                "daily_pnl": daily_pnl,
                "daily_pnl_percent": (daily_pnl / float(user.equity) * 100) if user.equity else 0,
                "total_trades": today_trades.count(),
                "winning_trades": wins,
                "losing_trades": losses,
                "win_rate": (wins / today_trades.count() * 100) if today_trades.count() > 0 else 0,
            },
        )

        # Cache symbol performance
        for symbol_name in all_trades.values_list("symbol__name", flat=True).distinct():
            symbol_trades = all_trades.filter(symbol__name=symbol_name)
            symbol_wins = symbol_trades.filter(profit_loss__gt=0).count()
            symbol_total = symbol_trades.count()
            CachedSymbolBreakdown.objects.update_or_create(
                user=user,
                symbol_name=symbol_name,
                period="ALL_TIME",
                defaults={
                    "total_pnl": sum(float(t.profit_loss or 0) for t in symbol_trades),
                    "total_trades": symbol_total,
                    "winning_trades": symbol_wins,
                    "win_rate": (symbol_wins / symbol_total * 100) if symbol_total > 0 else 0,
                },
            )

        # Cache period performance
        for period, days in [("TODAY", 0), ("WEEK", 7), ("MONTH", 30), ("ALL_TIME", 36500)]:
            if days == 0:
                period_trades = today_trades
            else:
                from datetime import timedelta
                cutoff = today - timedelta(days=days)
                period_trades = all_trades.filter(closed_at__date__gte=cutoff)

            total_pnl = sum(float(t.profit_loss or 0) for t in period_trades)
            period_wins = period_trades.filter(profit_loss__gt=0).count()
            period_losses = period_trades.filter(profit_loss__lt=0).count()
            period_total = period_trades.count()

            win_pnl = sum(float(t.profit_loss or 0) for t in period_trades.filter(profit_loss__gt=0))
            loss_pnl = abs(sum(float(t.profit_loss or 0) for t in period_trades.filter(profit_loss__lt=0)))

            CachedTradeSummary.objects.update_or_create(
                user=user,
                period=period,
                defaults={
                    "total_trades": period_total,
                    "winning_trades": period_wins,
                    "losing_trades": period_losses,
                    "win_rate": round((period_wins / period_total * 100) if period_total > 0 else 0, 2),
                    "total_pnl": round(total_pnl, 2),
                    "average_pnl": round(total_pnl / period_total, 2) if period_total > 0 else 0,
                    "profit_factor": round(win_pnl / loss_pnl, 2) if loss_pnl > 0 else 0,
                    "expires_at": timezone.now() + timedelta(minutes=5),
                },
            )


@shared_task
def health_check():
    """
    System health check task

    Verifies database connectivity and core services
    """
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc)}


@shared_task(bind=True, max_retries=1)
def train_model(self, model_type: str, symbol: str = "EURUSD", timeframe: str = "H1"):
    """Train an ML model with required symbol and timeframe parameters."""
    try:
        if model_type == "lstm":
            from ml.training.train_lstm import LSTMTrainer
            import asyncio
            trainer = LSTMTrainer()
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    trainer.train_walk_forward(symbol=symbol, timeframe=timeframe)
                )
            finally:
                loop.close()
        elif model_type == "regime":
            from ml.training.train_regime import RegimeTrainer
            import asyncio
            trainer = RegimeTrainer()
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    trainer.train_walk_forward(symbol=symbol, timeframe=timeframe)
                )
            finally:
                loop.close()
        else:
            return {"status": "error", "message": f"Unknown model type: {model_type}"}

        return {"status": "success", "model_type": model_type, "symbol": symbol, "timeframe": timeframe, "result": result}
    except Exception as exc:
        logger.error("Model training failed: %s", exc)
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True)
def run_backtest(self, backtest_id: str):
    """
    Run a backtest simulation using real historical OHLCV data from MT5.

    Replays strategy logic bar-by-bar with realistic position management.
    """
    import asyncio
    import logging

    from backtesting.models import BacktestResult
    from mcp_integration.services import mt5_service
    from strategies.timeframe_strategies import calculate_signal

    bt_logger = logging.getLogger("backtesting")

    result = BacktestResult.objects.get(id=backtest_id)

    symbol = result.symbol
    timeframe = result.timeframe
    strategy = result.strategy
    initial_balance = float(result.initial_balance)
    parameters = result.parameters or {}

    # --- Fetch historical OHLCV from MT5 ---
    lookback_count = parameters.get("lookback_bars", 2000)
    loop = asyncio.new_event_loop()
    try:
        candles = loop.run_until_complete(
            mt5_service.get_candles(symbol, timeframe, count=lookback_count)
        )
    finally:
        loop.close()

    if not candles or not isinstance(candles, list) or len(candles) < 50:
        bt_logger.warning(
            "Insufficient historical data for backtest %s (%s %s) — only %d candles",
            backtest_id, symbol, timeframe, len(candles) if candles else 0,
        )
        result.trades = []
        result.equity_curve = [{"bar": 0, "equity": initial_balance}]
        result.final_balance = result.initial_balance
        result.total_pnl = 0
        result.total_pnl_percent = 0
        result.total_trades = 0
        result.winning_trades = 0
        result.losing_trades = 0
        result.win_rate = 0
        result.profit_factor = 0
        result.max_drawdown = 0
        result.sharpe_ratio = 0
        result.save()
        return {"status": "success", "backtest_id": backtest_id, "note": "insufficient_data"}

    # --- Replay engine state ---
    balance = initial_balance
    peak_equity = initial_balance
    max_drawdown_pct = 0.0
    position = None  # None | {"dir": 1/-1, "entry": float, "sl": float, "tp": float, "lots": float, "bar": int}
    trades = []
    equity_curve = [{"bar": 0, "equity": balance}]
    risk_per_trade = float(parameters.get("risk_per_trade", 1.0)) / 100.0
    sl_atr_mult = float(parameters.get("sl_atr_mult", 2.0))
    tp_atr_mult = float(parameters.get("tp_atr_mult", 3.0))
    max_bars_in_trade = int(parameters.get("max_bars_in_trade", 100))

    # Pre-compute ATR for all bars (14-period)
    closes = [float(c.get("close", 0)) for c in candles]
    highs = [float(c.get("high", 0)) for c in candles]
    lows = [float(c.get("low", 0)) for c in candles]
    opens = [float(c.get("open", 0)) for c in candles]

    trs = []
    for i in range(1, len(candles)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atrs = [0.0] * 14
    for i in range(14, len(trs)):
        atrs.append(sum(trs[i - 13: i + 1]) / 14.0)

    # --- Bar-by-bar replay ---
    for bar_idx in range(50, len(candles)):
        close = closes[bar_idx]
        atr = atrs[bar_idx] if bar_idx < len(atrs) else (atrs[-1] if atrs else 0.0001)

        # --- Manage open position ---
        if position is not None:
            bars_held = bar_idx - position["bar"]
            high = highs[bar_idx]
            low = lows[bar_idx]

            hit_sl = False
            hit_tp = False

            if position["dir"] == 1:  # Long
                hit_sl = low <= position["sl"]
                hit_tp = high >= position["tp"]
            else:  # Short
                hit_sl = high >= position["sl"]
                hit_tp = low <= position["tp"]

            if hit_sl or hit_tp or bars_held >= max_bars_in_trade:
                if hit_sl:
                    exit_price = position["sl"]
                    pnl = (exit_price - position["entry"]) * position["dir"] * position["lots"] * 100000
                elif hit_tp:
                    exit_price = position["tp"]
                    pnl = (exit_price - position["entry"]) * position["dir"] * position["lots"] * 100000
                else:
                    exit_price = close
                    pnl = (exit_price - position["entry"]) * position["dir"] * position["lots"] * 100000

                balance += pnl
                trades.append({
                    "entry_bar": position["bar"],
                    "exit_bar": bar_idx,
                    "direction": "LONG" if position["dir"] == 1 else "SHORT",
                    "entry": round(position["entry"], 6),
                    "exit": round(exit_price, 6),
                    "sl": round(position["sl"], 6),
                    "tp": round(position["tp"], 6),
                    "pnl": round(pnl, 2),
                    "outcome": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BREAKEVEN"),
                })
                position = None

        # --- Check for new entry ---
        if position is None and atr > 0:
            # Use the strategy's calculate_signal on the lookback window
            window = 60
            if bar_idx >= window:
                lookback_ohlcv = {
                    "open": opens[bar_idx - window: bar_idx + 1],
                    "high": highs[bar_idx - window: bar_idx + 1],
                    "low": lows[bar_idx - window: bar_idx + 1],
                    "close": closes[bar_idx - window: bar_idx + 1],
                    "volume": [0] * (window + 1),
                }
                signal_result = calculate_signal(timeframe, lookback_ohlcv)
                signal_dir = signal_result.get("signal", "NEUTRAL")
                strength = float(signal_result.get("strength", 0))

                if signal_dir in ("BUY", "STRONG_BUY") and strength >= 60:
                    entry_price = close
                    risk_amount = balance * risk_per_trade
                    sl_distance = atr * sl_atr_mult
                    tp_distance = atr * tp_atr_mult
                    lots = round(risk_amount / (sl_distance * 100000), 2) if sl_distance > 0 else 0.01
                    lots = max(lots, 0.01)

                    position = {
                        "dir": 1,
                        "entry": entry_price,
                        "sl": entry_price - sl_distance,
                        "tp": entry_price + tp_distance,
                        "lots": lots,
                        "bar": bar_idx,
                    }

                elif signal_dir in ("SELL", "STRONG_SELL") and strength >= 60:
                    entry_price = close
                    risk_amount = balance * risk_per_trade
                    sl_distance = atr * sl_atr_mult
                    tp_distance = atr * tp_atr_mult
                    lots = round(risk_amount / (sl_distance * 100000), 2) if sl_distance > 0 else 0.01
                    lots = max(lots, 0.01)

                    position = {
                        "dir": -1,
                        "entry": entry_price,
                        "sl": entry_price + sl_distance,
                        "tp": entry_price - tp_distance,
                        "lots": lots,
                        "bar": bar_idx,
                    }

        # --- Track equity ---
        unrealized = 0.0
        if position is not None:
            unrealized = (close - position["entry"]) * position["dir"] * position["lots"] * 100000

        current_equity = balance + unrealized
        equity_curve.append({"bar": bar_idx, "equity": round(current_equity, 2)})

        if current_equity > peak_equity:
            peak_equity = current_equity
        if peak_equity > 0:
            dd = ((peak_equity - current_equity) / peak_equity) * 100
            if dd > max_drawdown_pct:
                max_drawdown_pct = dd

    # --- Close any remaining open position at last bar ---
    if position is not None:
        last_close = closes[-1]
        pnl = (last_close - position["entry"]) * position["dir"] * position["lots"] * 100000
        balance += pnl
        trades.append({
            "entry_bar": position["bar"],
            "exit_bar": len(candles) - 1,
            "direction": "LONG" if position["dir"] == 1 else "SHORT",
            "entry": round(position["entry"], 6),
            "exit": round(last_close, 6),
            "sl": round(position["sl"], 6),
            "tp": round(position["tp"], 6),
            "pnl": round(pnl, 2),
            "outcome": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BREAKEVEN"),
        })

    # --- Compute final stats ---
    wins = len([t for t in trades if t["outcome"] == "WIN"])
    losses = len([t for t in trades if t["outcome"] == "LOSS"])
    total_wins = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    total_losses = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))

    returns = []
    for i in range(1, len(equity_curve)):
        prev_eq = equity_curve[i - 1]["equity"]
        if prev_eq > 0:
            returns.append((equity_curve[i]["equity"] - prev_eq) / prev_eq)
    avg_return = sum(returns) / len(returns) if returns else 0
    std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if len(returns) > 1 else 1
    sharpe = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0

    result.final_balance = round(balance, 2)
    result.total_pnl = round(balance - initial_balance, 2)
    result.total_pnl_percent = round(
        (balance - initial_balance) / initial_balance * 100, 2
    ) if initial_balance > 0 else 0
    result.total_trades = len(trades)
    result.winning_trades = wins
    result.losing_trades = losses
    result.win_rate = round(wins / len(trades) * 100, 2) if trades else 0
    result.profit_factor = round(total_wins / total_losses, 2) if total_losses > 0 else 0
    result.max_drawdown = round(max_drawdown_pct, 2)
    result.sharpe_ratio = round(sharpe, 4)
    result.trades = trades
    result.equity_curve = equity_curve
    result.save()

    bt_logger.info(
        "Backtest %s complete: %d trades, %.1f%% win rate, %.2f%% return, DD=%.2f%%",
        backtest_id, len(trades), result.win_rate, result.total_pnl_percent, max_drawdown_pct,
    )

    return {"status": "success", "backtest_id": backtest_id}


@shared_task(bind=True)
def run_gold_edge_backtest(self, backtest_id: str):
    """
    Run a Gold Edge strategy backtest using real historical OHLCV from MT5.

    Replays the Gold Edge composite + ATR border + ATR filter logic
    bar-by-bar.
    """
    import asyncio
    import logging

    from mcp_integration.services import mt5_service

    bt_logger = logging.getLogger("gold_edge.backtest")

    try:
        from gold_edge.models import GoldEdgeBacktest
        from gold_edge.entry_logic import GoldEdgeMatrix
    except ImportError:
        return {"status": "error", "message": "gold_edge module not installed"}

    result = GoldEdgeBacktest.objects.get(id=backtest_id)
    result.status = "RUNNING"
    result.save()

    # Determine symbol/timeframe from config
    symbol = result.config.symbol.name if result.config else "XAUUSD"
    timeframe = result.config.timeframe.code if result.config else "H1"
    initial_balance = float(result.initial_balance)
    parameters = result.parameters or {}

    # Build matrix from config
    cfg = result.config
    matrix_kwargs = {}
    if cfg:
        matrix_kwargs = {
            "momentum_weight": float(cfg.momentum_weight),
            "trend_weight": float(cfg.trend_weight),
            "volatility_weight": float(cfg.volatility_weight),
            "dxy_correlation_weight": float(cfg.dxy_correlation_weight),
            "ema_period": cfg.ema_period,
            "atr_period": cfg.atr_period,
            "atr_multipliers": cfg.atr_multipliers,
            "atr_ratio_min": float(cfg.atr_ratio_min),
            "atr_ratio_max": float(cfg.atr_ratio_max),
            "min_gec_score": float(cfg.min_gec_score),
            "min_combined_score": float(cfg.min_combined_score),
            "sl_atr_multiplier": float(cfg.sl_atr_multiplier),
            "tp_atr_multiplier": float(cfg.tp_atr_multiplier),
        }

    matrix = GoldEdgeMatrix(**matrix_kwargs) if matrix_kwargs else GoldEdgeMatrix()

    # --- Fetch historical OHLCV from MT5 ---
    lookback_count = parameters.get("lookback_bars", 2000)
    loop = asyncio.new_event_loop()
    try:
        candles = loop.run_until_complete(
            mt5_service.get_candles(symbol, timeframe, count=lookback_count)
        )
    finally:
        loop.close()

    if not candles or not isinstance(candles, list) or len(candles) < 60:
        bt_logger.warning("Insufficient data for Gold Edge backtest %s", backtest_id)
        result.status = "COMPLETED"
        result.trades = []
        result.equity_curve = [{"bar": 0, "equity": initial_balance}]
        result.final_balance = result.initial_balance
        result.total_trades = 0
        result.save()
        return {"status": "success", "backtest_id": backtest_id, "note": "insufficient_data"}

    # --- Replay engine ---
    balance = initial_balance
    peak_equity = initial_balance
    max_drawdown_pct = 0.0
    position = None
    trades = []
    equity_curve = [{"bar": 0, "equity": balance}]
    gec_scores = []
    risk_per_trade = float(parameters.get("risk_per_trade", 1.0)) / 100.0

    closes = [float(c.get("close", 0)) for c in candles]
    highs = [float(c.get("high", 0)) for c in candles]
    lows = [float(c.get("low", 0)) for c in candles]
    opens = [float(c.get("open", 0)) for c in candles]

    import numpy as np
    import pandas as pd

    for bar_idx in range(60, len(candles)):
        close = closes[bar_idx]

        # Build lookback OHLCV
        window = min(200, bar_idx)
        lookback_df = pd.DataFrame({
            "open": opens[bar_idx - window: bar_idx + 1],
            "high": highs[bar_idx - window: bar_idx + 1],
            "low": lows[bar_idx - window: bar_idx + 1],
            "close": closes[bar_idx - window: bar_idx + 1],
            "volume": [0] * (window + 1),
        })

        # Run Gold Edge matrix
        from gold_edge.ge_composite import GECResult
        gec_result = matrix.gec.calculate(lookback_df)
        gec_scores.append(gec_result.composite_score)

        matrix_result = matrix.evaluate(lookback_df, price_override=close)

        # Manage open position
        if position is not None:
            bars_held = bar_idx - position["bar"]
            high = highs[bar_idx]
            low = lows[bar_idx]

            hit_sl = False
            hit_tp = False
            if position["dir"] == 1:
                hit_sl = low <= position["sl"]
                hit_tp = high >= position["tp"]
            else:
                hit_sl = high >= position["sl"]
                hit_tp = low <= position["tp"]

            if hit_sl or hit_tp or bars_held >= 200:
                exit_price = position["sl"] if hit_sl else (position["tp"] if hit_tp else close)
                pnl = (exit_price - position["entry"]) * position["dir"] * position["lots"] * 100000
                balance += pnl
                trades.append({
                    "entry_bar": position["bar"],
                    "exit_bar": bar_idx,
                    "direction": "LONG" if position["dir"] == 1 else "SHORT",
                    "entry": round(position["entry"], 6),
                    "exit": round(exit_price, 6),
                    "pnl": round(pnl, 2),
                    "outcome": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BREAKEVEN"),
                })
                position = None

        # Open new position
        if position is None and matrix_result.action == "ENTRY" and matrix_result.direction in ("LONG", "SHORT"):
            entry_price = close
            risk_amount = balance * risk_per_trade
            sl_dist = abs(entry_price - matrix_result.stop_loss) if matrix_result.stop_loss else 0.001
            lots = round(risk_amount / (sl_dist * 100000), 2) if sl_dist > 0 else 0.01
            lots = max(lots, 0.01)

            position = {
                "dir": 1 if matrix_result.direction == "LONG" else -1,
                "entry": entry_price,
                "sl": matrix_result.stop_loss,
                "tp": matrix_result.take_profit,
                "lots": lots,
                "bar": bar_idx,
            }

        # Track equity
        unrealized = 0.0
        if position is not None:
            unrealized = (close - position["entry"]) * position["dir"] * position["lots"] * 100000
        current_equity = balance + unrealized
        equity_curve.append({"bar": bar_idx, "equity": round(current_equity, 2)})

        if current_equity > peak_equity:
            peak_equity = current_equity
        if peak_equity > 0:
            dd = ((peak_equity - current_equity) / peak_equity) * 100
            if dd > max_drawdown_pct:
                max_drawdown_pct = dd

    # Close any open position
    if position is not None:
        last_close = closes[-1]
        pnl = (last_close - position["entry"]) * position["dir"] * position["lots"] * 100000
        balance += pnl
        trades.append({
            "entry_bar": position["bar"],
            "exit_bar": len(candles) - 1,
            "direction": "LONG" if position["dir"] == 1 else "SHORT",
            "entry": round(position["entry"], 6),
            "exit": round(last_close, 6),
            "pnl": round(pnl, 2),
            "outcome": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BREAKEVEN"),
        })

    # Final stats
    wins = len([t for t in trades if t["outcome"] == "WIN"])
    losses = len([t for t in trades if t["outcome"] == "LOSS"])
    total_wins = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    total_losses = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))

    result.status = "COMPLETED"
    result.final_balance = round(balance, 2)
    result.total_pnl = round(balance - initial_balance, 2)
    result.total_pnl_percent = round(
        (balance - initial_balance) / initial_balance * 100, 2
    ) if initial_balance > 0 else 0
    result.total_trades = len(trades)
    result.winning_trades = wins
    result.losing_trades = losses
    result.win_rate = round(wins / len(trades) * 100, 2) if trades else 0
    result.profit_factor = round(total_wins / total_losses, 2) if total_losses > 0 else 0
    result.max_drawdown = round(max_drawdown_pct, 2)
    result.trades = trades
    result.equity_curve = equity_curve
    result.gec_scores_over_time = gec_scores[-len(equity_curve):]
    result.save()

    bt_logger.info(
        "Gold Edge backtest %s complete: %d trades, %.1f%% win rate, %.2f%% return",
        backtest_id, len(trades), result.win_rate, result.total_pnl_percent,
    )

    return {"status": "success", "backtest_id": backtest_id}


# ── V6 Complete Trading Cycle ──────────────────────────────────────
@shared_task(bind=True, max_retries=3)
def run_v6_trading_cycle(self):
    """
    V6 Complete Trading Cycle - runs every 60 seconds.
    Scans markets, generates signals, manages risk, executes trades.

    Pipeline: Scan -> AI -> Signal -> Risk -> Execute -> Learn
    """
    try:
        import asyncio
        from ml.v6_orchestrator import get_v6_orchestrator

        orchestrator = get_v6_orchestrator()
        orchestrator.initialize()

        # ── Fetch market data for all active symbols ────────────────
        from mcp_integration.services import mt5_service

        market_data = {}

        symbols = [
            "XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
            "USDCAD", "NZDUSD", "USDCHF", "EURGBP", "EURJPY",
        ]

        loop = asyncio.new_event_loop()
        try:
            for symbol in symbols:
                try:
                    candles = loop.run_until_complete(
                        mt5_service.get_candles(symbol, "M5", 100)
                    )
                    if candles and isinstance(candles, list) and len(candles) >= 10:
                        closes = [float(c.get("close", 0)) for c in candles]
                        highs = [float(c.get("high", 0)) for c in candles]
                        lows = [float(c.get("low", 0)) for c in candles]

                        # Compute ATR for volatility scaling
                        trs = []
                        for i in range(1, len(candles)):
                            h, l, pc = highs[i], lows[i], closes[i - 1]
                            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
                        current_atr = sum(trs[-14:]) / 14.0 if len(trs) >= 14 else 0
                        historical_atr = sum(trs) / len(trs) if trs else 1

                        # Get tick data for spread
                        try:
                            tick = loop.run_until_complete(
                                mt5_service.get_tick_data(symbol)
                            )
                            spread = tick.get("spread", 0.1) if tick else 0.1
                        except Exception:
                            spread = 0.1

                        market_data[symbol] = {
                            "candles": candles,
                            "current_price": closes[-1] if closes else 0,
                            "spread": spread,
                            "volume": sum(
                                int(c.get("volume", 0)) for c in candles[-20:]
                            ),
                            "current_atr": current_atr,
                            "historical_atr": historical_atr,
                            "highs": highs,
                            "lows": lows,
                            "closes": closes,
                        }
                except Exception as sym_exc:
                    logger.warning(
                        "V6 market data fetch failed for %s: %s", symbol, sym_exc
                    )
                    continue
        finally:
            loop.close()

        if not market_data:
            logger.warning("V6 cycle: No market data available")
            return {"status": "NO_DATA"}

        # ── Run the V6 trading cycle ────────────────────────────────
        result = orchestrator.run_trading_cycle(market_data)

        logger.info(
            "V6 cycle complete: status=%s, trade_executed=%s, components=%d/%d",
            result.get("status"),
            result.get("trade_executed"),
            result.get("phases", {}).get("scan", {}).get("filtered_count", 0),
            len(market_data),
        )
        return result

    except Exception as e:
        logger.error("V6 trading cycle failed: %s", e, exc_info=True)
        raise self.retry(exc=e, countdown=60)
