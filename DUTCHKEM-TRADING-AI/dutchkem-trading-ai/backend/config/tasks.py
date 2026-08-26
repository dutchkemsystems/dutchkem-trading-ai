# Dutchkem Trading AI — Celery Tasks
# Background tasks for indicator calculation, signal generation, and EA deployment

import json
from datetime import datetime, timedelta

from celery import shared_task
from django.utils import timezone


@shared_task(bind=True, max_retries=3)
def calculate_indicators(self, symbol_id: str, timeframe_code: str):
    """
    Calculate indicators for a symbol and timeframe

    This task is triggered when new market data arrives
    """
    try:
        from strategies.timeframe_strategies import calculate_signal

        from indicators.models import Indicator, IndicatorValue, Timeframe
        from trading.models import Symbol

        symbol = Symbol.objects.get(id=symbol_id)
        timeframe = Timeframe.objects.get(code=timeframe_code)

        # Get historical data (would come from MT5 via MCP)
        # For now, use placeholder
        ohlcv_data = {
            "open": [1.1200, 1.1210, 1.1220, 1.1215, 1.1225],
            "high": [1.1220, 1.1230, 1.1240, 1.1235, 1.1245],
            "low": [1.1190, 1.1200, 1.1210, 1.1205, 1.1215],
            "close": [1.1210, 1.1220, 1.1230, 1.1225, 1.1235],
            "volume": [1000, 1200, 1100, 1300, 1400],
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

    This task runs periodically to generate trading signals
    """
    try:
        from decimal import Decimal

        from strategies.confluence import TimeframeSignal, confluence_engine
        from strategies.timeframe_strategies import calculate_signal

        from signals.models import ConfluenceScore, Signal
        from trading.models import Symbol

        symbol = Symbol.objects.get(id=symbol_id)

        # Get signals for all timeframes
        timeframe_signals = {}
        timeframes = ["M5", "M15", "M30", "H1", "H2", "H4"]

        for tf in timeframes:
            # Calculate signal for each timeframe
            ohlcv_data = {
                "open": [1.1200, 1.1210, 1.1220],
                "high": [1.1220, 1.1230, 1.1240],
                "low": [1.1190, 1.1200, 1.1210],
                "close": [1.1210, 1.1220, 1.1230],
                "volume": [1000, 1200, 1100],
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
            Signal.objects.create(
                symbol=symbol,
                timeframe_id=None,  # Multi-timeframe signal
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
        from mcp_servers.mcp_service import mcp_service

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
    from mcp_servers.mcp_service import mcp_service

    User = get_user_model()

    for user in User.objects.filter(is_active=True, mt5_account__isnull=False):
        # Get account info from MT5
        result = mcp_service.get_account_info()

        if result.success:
            user.balance = result.data.get("balance", user.balance)
            user.equity = result.data.get("equity", user.equity)
            user.save()
