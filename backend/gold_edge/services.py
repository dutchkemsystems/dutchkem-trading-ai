"""
Gold Edge Service — orchestrates the full Gold Edge pipeline.

Pipeline:
  1. Fetch OHLCV data from MT5
  2. Calculate GEC composite score
  3. Build ATR border grid
  4. Apply ATR ratio filter
  5. Run Gold Edge Matrix for entry decision
  6. Store signal and trigger risk checks
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .atr_border import ATRBorderGrid
from .atr_filter import ATRRatioFilter
from .entry_logic import GoldEdgeMatrix, GoldEdgeMatrixResult
from .ge_composite import GoldEdgeComposite

logger = logging.getLogger("gold_edge.service")


class GoldEdgeService:
    """
    High-level service that runs the Gold Edge pipeline end-to-end.

    Usage::

        service = GoldEdgeService()
        result = service.run_pipeline(
            symbol_name="XAUUSD",
            timeframe_code="H1",
        )
    """

    def __init__(
        self,
        gec: Optional[GoldEdgeComposite] = None,
        atr_border: Optional[ATRBorderGrid] = None,
        atr_filter: Optional[ATRRatioFilter] = None,
        matrix: Optional[GoldEdgeMatrix] = None,
    ):
        self.gec = gec or GoldEdgeComposite()
        self.atr_border = atr_border or ATRBorderGrid()
        self.atr_filter = atr_filter or ATRRatioFilter()
        self.matrix = matrix or GoldEdgeMatrix()

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_ohlcv(
        self, symbol_name: str, timeframe_code: str, count: int = 500
    ) -> pd.DataFrame:
        """Fetch OHLCV data from MT5 via MCP integration."""
        try:
            from mcp_integration.services import mt5_service

            loop = asyncio.new_event_loop()
            try:
                candles = loop.run_until_complete(
                    mt5_service.get_candles(symbol_name, timeframe_code, count=count)
                )
            finally:
                loop.close()

            if not candles or not isinstance(candles, list):
                return pd.DataFrame()

            df = pd.DataFrame(candles)
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if "volume" in df.columns:
                df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
            if "time" in df.columns:
                df["timestamp"] = pd.to_datetime(df["time"])
                df = df.sort_values("timestamp").reset_index(drop=True)

            return df
        except Exception as exc:
            logger.error("Failed to fetch OHLCV for %s %s: %s", symbol_name, timeframe_code, exc)
            return pd.DataFrame()

    def _fetch_dxy(self, count: int = 500) -> Optional[pd.Series]:
        """Fetch DXY (US Dollar Index) data if available."""
        try:
            from mcp_integration.services import mt5_service

            loop = asyncio.new_event_loop()
            try:
                candles = loop.run_until_complete(
                    mt5_service.get_candles("DXY", "H1", count=count)
                )
            finally:
                loop.close()

            if candles and isinstance(candles, list):
                closes = [float(c.get("close", 0)) for c in candles]
                if closes:
                    return pd.Series(closes)
        except Exception:
            logger.debug("DXY data not available — using neutral DXY score")
        return None

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        symbol_name: str,
        timeframe_code: str = "H1",
        config: Optional[Dict[str, Any]] = None,
    ) -> GoldEdgeMatrixResult:
        """
        Run the full Gold Edge pipeline for a symbol/timeframe.

        Args:
            symbol_name: trading symbol (e.g., "XAUUSD").
            timeframe_code: timeframe code (e.g., "H1").
            config: optional config overrides.

        Returns:
            GoldEdgeMatrixResult with full analysis.
        """
        logger.info("Running Gold Edge pipeline for %s %s", symbol_name, timeframe_code)

        # Fetch data
        ohlcv = self._fetch_ohlcv(symbol_name, timeframe_code, count=500)
        if ohlcv.empty or len(ohlcv) < 50:
            logger.warning("Insufficient data for %s %s", symbol_name, timeframe_code)
            return GoldEdgeMatrixResult(rejection_reasons=["insufficient_data"])

        dxy = self._fetch_dxy()

        # Apply config overrides if provided
        if config:
            matrix = self._build_matrix_from_config(config)
        else:
            matrix = self.matrix

        # Run the matrix
        result = matrix.evaluate(ohlcv, dxy_series=dxy)

        logger.info(
            "Gold Edge %s %s: action=%s, direction=%s, score=%.4f",
            symbol_name, timeframe_code,
            result.action, result.direction, result.combined_score,
        )

        return result

    def _build_matrix_from_config(self, config: Dict[str, Any]) -> GoldEdgeMatrix:
        """Build a GoldEdgeMatrix from a config dict."""
        return GoldEdgeMatrix(
            momentum_weight=float(config.get("momentum_weight", 0.30)),
            trend_weight=float(config.get("trend_weight", 0.30)),
            volatility_weight=float(config.get("volatility_weight", 0.20)),
            dxy_correlation_weight=float(config.get("dxy_correlation_weight", 0.20)),
            ema_period=int(config.get("ema_period", 21)),
            atr_period=int(config.get("atr_period", 14)),
            atr_multipliers=config.get("atr_multipliers"),
            atr_sma_period=int(config.get("atr_sma_period", 50)),
            atr_ratio_min=float(config.get("atr_ratio_min", 0.15)),
            atr_ratio_max=float(config.get("atr_ratio_max", 1.0)),
            min_gec_score=float(config.get("min_gec_score", 0.50)),
            min_combined_score=float(config.get("min_combined_score", 0.60)),
            sl_atr_multiplier=float(config.get("sl_atr_multiplier", 2.0)),
            tp_atr_multiplier=float(config.get("tp_atr_multiplier", 3.0)),
        )

    # ------------------------------------------------------------------
    # Signal storage
    # ------------------------------------------------------------------

    def store_signal(
        self,
        config_id: str,
        symbol_name: str,
        timeframe_code: str,
        result: GoldEdgeMatrixResult,
    ) -> Optional[str]:
        """
        Persist a Gold Edge signal to the database.

        Returns the signal ID if stored, else None.
        """
        try:
            from indicators.models import Timeframe
            from trading.models import Symbol
            from .models import GoldEdgeConfig, GoldEdgeSignal

            config = GoldEdgeConfig.objects.get(id=config_id)
            symbol = Symbol.objects.get(name=symbol_name)
            timeframe = Timeframe.objects.get(code=timeframe_code)

            signal = GoldEdgeSignal.objects.create(
                config=config,
                symbol=symbol,
                timeframe=timeframe,
                direction=result.direction,
                gec_score=result.gec_score,
                combined_matrix_score=result.combined_score,
                momentum_score=result.gec.momentum_score if result.gec else 0,
                trend_score=result.gec.trend_score if result.gec else 0,
                volatility_score=result.gec.volatility_score if result.gec else 0,
                dxy_correlation_score=result.gec.dxy_correlation_score if result.gec else 0,
                atr_border_layer=result.atr_border.current_layer if result.atr_border else 0,
                atr_ratio=result.atr_filter.ratio if result.atr_filter else 0,
                atr_filter_pass=result.atr_filter.passes_filter if result.atr_filter else False,
                entry_price=result.entry_price,
                stop_loss=result.stop_loss,
                take_profit=result.take_profit,
                risk_reward_ratio=result.risk_reward_ratio,
                confidence=result.confidence,
            )

            logger.info("Gold Edge signal stored: %s", signal.id)
            return str(signal.id)

        except Exception as exc:
            logger.error("Failed to store Gold Edge signal: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Batch analysis
    # ------------------------------------------------------------------

    def scan_symbols(
        self,
        symbol_names: List[str],
        timeframe_code: str = "H1",
        config: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run Gold Edge on multiple symbols and return actionable signals.
        """
        results = []
        for name in symbol_names:
            try:
                result = self.run_pipeline(name, timeframe_code, config)
                if result.action in ("ENTRY", "WATCH"):
                    results.append({
                        "symbol": name,
                        "timeframe": timeframe_code,
                        **result.to_dict(),
                    })
            except Exception as exc:
                logger.error("Gold Edge scan failed for %s: %s", name, exc)

        return sorted(results, key=lambda r: r.get("combined_score", 0), reverse=True)


# Module-level singleton
gold_edge_service = GoldEdgeService()
