"""
ARTIFICIAL DIVERSIFICATION ENGINE
V6.5 Enhancement #8
"""

import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger("ml.enhancements.diversification")


class ArtificialDiversification:
    """
    Ensures portfolio is properly diversified.
    """

    def __init__(self):
        self.max_correlation_threshold = 0.70
        self.max_positions = 5
        self.max_asset_class_exposure = 0.40
        self.max_sector_exposure = 0.60

        self.asset_classes = {
            "EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX", "AUDUSD": "FOREX",
            "USDCAD": "FOREX", "NZDUSD": "FOREX", "USDCHF": "FOREX", "EURGBP": "FOREX",
            "EURJPY": "FOREX", "GBPJPY": "FOREX", "AUDJPY": "FOREX",
            "XAUUSD": "COMMODITY", "XAGUSD": "COMMODITY",
            "BTCUSD": "CRYPTO", "ETHUSD": "CRYPTO",
        }
        self.sectors = {
            "EURUSD": "MAJORS", "GBPUSD": "MAJORS", "USDJPY": "MAJORS", "USDCHF": "MAJORS",
            "AUDUSD": "COMMODITY_CURRENCIES", "USDCAD": "COMMODITY_CURRENCIES", "NZDUSD": "COMMODITY_CURRENCIES",
            "EURGBP": "CROSSES", "EURJPY": "CROSSES", "GBPJPY": "CROSSES", "AUDJPY": "CROSSES",
            "XAUUSD": "PRECIOUS_METALS", "XAGUSD": "PRECIOUS_METALS",
            "BTCUSD": "CRYPTO_MAJORS", "ETHUSD": "CRYPTO_MAJORS",
        }
        self.correlation_matrix = {
            ("EURUSD", "GBPUSD"): 0.85, ("EURUSD", "USDJPY"): -0.40,
            ("EURUSD", "XAUUSD"): 0.70, ("GBPUSD", "USDJPY"): -0.35,
            ("USDJPY", "XAUUSD"): -0.50, ("XAUUSD", "XAGUSD"): 0.90,
            ("BTCUSD", "ETHUSD"): 0.80,
        }

    def check_diversification(self, symbol: str, open_positions: List[Dict]) -> Dict:
        try:
            if len(open_positions) >= self.max_positions:
                return {"diversified": False, "reason": f"Max positions ({self.max_positions}) reached", "action": "REJECT"}

            for pos in open_positions:
                corr = self.get_correlation(symbol, pos["symbol"])
                if abs(corr) > self.max_correlation_threshold:
                    return {"diversified": False, "reason": f"High correlation with {pos['symbol']} ({corr:.2f})",
                            "action": "REDUCE_SIZE", "penalty": abs(corr) / self.max_correlation_threshold}

            ac = self.get_asset_class(symbol)
            exposure = self.get_asset_class_exposure(ac, open_positions)
            if exposure > self.max_asset_class_exposure:
                return {"diversified": False, "reason": f"Asset class {ac} exposure too high ({exposure:.1%})",
                        "action": "REDUCE_SIZE", "penalty": exposure / self.max_asset_class_exposure}

            sector = self.get_sector(symbol)
            s_exp = self.get_sector_exposure(sector, open_positions)
            if s_exp > self.max_sector_exposure:
                return {"diversified": False, "reason": f"Sector {sector} exposure too high ({s_exp:.1%})",
                        "action": "REDUCE_SIZE", "penalty": s_exp / self.max_sector_exposure}

            return {"diversified": True, "reason": "Diversified", "action": "ACCEPT", "penalty": 1.0}
        except Exception as e:
            logger.error("Diversification check failed: %s", e)
            return {"diversified": True, "reason": "Default accept", "action": "ACCEPT", "penalty": 1.0}

    def calculate_diversification_penalty(self, symbol: str, open_positions: List[Dict]) -> float:
        if not open_positions:
            return 1.0
        try:
            avg_corr = 0
            for pos in open_positions:
                avg_corr += abs(self.get_correlation(symbol, pos["symbol"]))
            avg_corr /= len(open_positions)
            corr_penalty = 1.0 - avg_corr * 0.5

            ac = self.get_asset_class(symbol)
            exposure = self.get_asset_class_exposure(ac, open_positions)
            conc_penalty = 1.0 - (exposure / self.max_asset_class_exposure) * 0.3

            return max(0.5, min(1.0, corr_penalty * conc_penalty))
        except Exception:
            return 1.0

    def get_correlation(self, s1: str, s2: str) -> float:
        key = (s1, s2) if s1 < s2 else (s2, s1)
        return self.correlation_matrix.get(key, 0.0)

    def get_asset_class(self, symbol: str) -> str:
        return self.asset_classes.get(symbol, "UNKNOWN")

    def get_sector(self, symbol: str) -> str:
        return self.sectors.get(symbol, "UNKNOWN")

    def get_asset_class_exposure(self, asset_class: str, positions: List[Dict]) -> float:
        if not positions:
            return 0.0
        total = sum(p.get("equity", 1) for p in positions)
        class_eq = sum(p.get("equity", 0) for p in positions if self.get_asset_class(p["symbol"]) == asset_class)
        return class_eq / total if total > 0 else 0.0

    def get_sector_exposure(self, sector: str, positions: List[Dict]) -> float:
        if not positions:
            return 0.0
        total = sum(p.get("equity", 1) for p in positions)
        sec_eq = sum(p.get("equity", 0) for p in positions if self.get_sector(p["symbol"]) == sector)
        return sec_eq / total if total > 0 else 0.0

    def get_diversification_report(self, positions: List[Dict]) -> Dict:
        acs, sectors = {}, {}
        for pos in positions:
            ac = self.get_asset_class(pos["symbol"])
            s = self.get_sector(pos["symbol"])
            acs[ac] = acs.get(ac, 0) + 1
            sectors[s] = sectors.get(s, 0) + 1
        return {
            "total_positions": len(positions), "asset_classes": acs, "sectors": sectors,
            "diversification_score": min(1.0, len(acs) / 4), "timestamp": datetime.now().isoformat(),
        }
