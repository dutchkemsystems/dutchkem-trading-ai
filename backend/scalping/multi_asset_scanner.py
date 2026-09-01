"""
V2 Multi-Asset Scanner — Concurrent scanning of 28+ instruments with priority ranking.
"""
import logging
import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

logger = logging.getLogger('scalping.scanner')

FOREX_PAIRS = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'NZDUSD', 'USDCAD',
    'EURGBP', 'EURJPY', 'GBPJPY', 'CHFJPY', 'AUDJPY', 'EURAUD', 'EURCHF',
    'EURCAD', 'EURNZD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPNZD',
    'AUDCAD', 'AUDCHF', 'AUDNZD', 'CADJPY', 'CADCHF', 'NZDJPY', 'NZDCAD',
    'NZDCHF',
]

COMMODITY_PAIRS = ['XAUUSD', 'XAGUSD', 'USOIL']
INDEX_PAIRS = ['US30', 'NAS100', 'SPX500', 'UK100', 'GER40']
CRYPTO_PAIRS = ['BTCUSD', 'ETHUSD', 'SOLUSD']

ALL_INSTRUMENTS = FOREX_PAIRS + COMMODITY_PAIRS + INDEX_PAIRS + CRYPTO_PAIRS


class InstrumentScreener:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.score = 0.0
        self.signals = []
        self.volatility = 0.0
        self.trend_strength = 0.0
        self.liquidity_score = 0.0
    
    def analyze(self, data: Dict) -> Dict:
        closes = np.array(data.get('close', []))
        highs = np.array(data.get('high', []))
        lows = np.array(data.get('low', []))
        volumes = np.array(data.get('volume', []))
        
        if len(closes) < 20:
            return {'symbol': self.symbol, 'score': 0, 'skip': True}
        
        # Volatility score
        returns = np.diff(np.log(closes)) if len(closes) > 1 else np.array([0])
        self.volatility = float(np.std(returns) * np.sqrt(252))
        
        # Trend strength (ADX proxy via directional movement)
        if len(highs) >= 14 and len(lows) >= 14:
            plus_dm = np.maximum(np.diff(highs[-15:]), 0)
            minus_dm = np.maximum(-np.diff(lows[-15:]), 0)
            atr = float(np.mean(highs[-14:] - lows[-14:]))
            if atr > 0:
                plus_di = np.sum(plus_dm) / (14 * atr) * 100
                minus_di = np.sum(minus_dm) / (14 * atr) * 100
                self.trend_strength = abs(plus_di - minus_di)
        
        # Liquidity score (volume-based)
        if len(volumes) >= 20:
            avg_vol = np.mean(volumes[-20:])
            self.liquidity_score = min(1.0, avg_vol / 10000) if avg_vol > 0 else 0.5
        
        # Signal strength (momentum)
        if len(closes) >= 10:
            momentum = (closes[-1] - closes[-10]) / closes[-10] * 100
            self.score = (
                self.volatility * 30 +
                self.trend_strength * 25 +
                self.liquidity_score * 25 +
                abs(momentum) * 20
            )
        
        return {
            'symbol': self.symbol,
            'score': round(self.score, 2),
            'volatility': round(self.volatility, 4),
            'trend_strength': round(self.trend_strength, 2),
            'liquidity': round(self.liquidity_score, 2),
            'skip': False,
        }


class MultiAssetScanner:
    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self.instruments = ALL_INSTRUMENTS.copy()
        self.last_scan_time = 0.0
        self.scan_results: Dict[str, Dict] = {}
    
    def scan_all(self, market_data: Dict[str, Dict], instruments: Optional[List[str]] = None) -> List[Dict]:
        targets = instruments or self.instruments
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for symbol in targets:
                data = market_data.get(symbol, {})
                if data:
                    screener = InstrumentScreener(symbol)
                    futures[executor.submit(screener.analyze, data)] = symbol
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if not result.get('skip'):
                        results.append(result)
                        self.scan_results[result['symbol']] = result
                except Exception as e:
                    logger.warning("Scan failed for %s: %s", futures[future], e)
        
        results.sort(key=lambda x: x['score'], reverse=True)
        self.last_scan_time = time.time()
        
        logger.info("Scanned %d instruments, %d with signals", len(targets), len(results))
        return results
    
    def get_top_opportunities(self, n: int = 5) -> List[Dict]:
        sorted_results = sorted(self.scan_results.values(), key=lambda x: x['score'], reverse=True)
        return sorted_results[:n]
    
    def get_scan_stats(self) -> Dict:
        return {
            'total_instruments': len(self.instruments),
            'last_scan_time': self.last_scan_time,
            'results_count': len(self.scan_results),
            'top_5': [r['symbol'] for r in self.get_top_opportunities(5)],
        }


scanner = MultiAssetScanner()
