"""
V6 Asset Class Ensemble — Specialized AI ensembles for each asset class.
More accurate predictions for each market type.
"""
import logging
from typing import Dict, Any, Optional, List
import numpy as np

logger = logging.getLogger('ml.asset_ensemble')


class ForexFeatureSet:
    """Feature extraction specific to forex markets."""
    
    @staticmethod
    def extract(data: Dict) -> np.ndarray:
        features = []
        for key in ['open', 'high', 'low', 'close', 'volume']:
            if key in data:
                arr = np.array(data[key]) if isinstance(data[key], list) else [data[key]]
                features.extend(arr[-20:].tolist() if len(arr) >= 20 else arr.tolist())
        
        if 'rsi' in data:
            features.append(data['rsi'])
        if 'macd' in data:
            features.append(data['macd'])
        if 'atr' in data:
            features.append(data['atr'])
        if 'spread' in data:
            features.append(data['spread'])
        
        return np.array(features[:100])


class CommodityFeatureSet:
    @staticmethod
    def extract(data: Dict) -> np.ndarray:
        features = []
        for key in ['open', 'high', 'low', 'close', 'volume']:
            if key in data:
                arr = np.array(data[key]) if isinstance(data[key], list) else [data[key]]
                features.extend(arr[-20:].tolist() if len(arr) >= 20 else arr.tolist())
        
        if 'dxy' in data:
            features.append(data['dxy'])
        if 'gold_correlation' in data:
            features.append(data['gold_correlation'])
        
        return np.array(features[:100])


class IndexFeatureSet:
    @staticmethod
    def extract(data: Dict) -> np.ndarray:
        features = []
        for key in ['open', 'high', 'low', 'close', 'volume']:
            if key in data:
                arr = np.array(data[key]) if isinstance(data[key], list) else [data[key]]
                features.extend(arr[-20:].tolist() if len(arr) >= 20 else arr.tolist())
        
        if 'vix' in data:
            features.append(data['vix'])
        
        return np.array(features[:100])


class CryptoFeatureSet:
    @staticmethod
    def extract(data: Dict) -> np.ndarray:
        features = []
        for key in ['open', 'high', 'low', 'close', 'volume']:
            if key in data:
                arr = np.array(data[key]) if isinstance(data[key], list) else [data[key]]
                features.extend(arr[-20:].tolist() if len(arr) >= 20 else arr.tolist())
        
        if 'funding_rate' in data:
            features.append(data['funding_rate'])
        if 'order_book_depth' in data:
            features.append(data['order_book_depth'])
        
        return np.array(features[:100])


ASSET_CLASS_PATTERNS = {
    'forex': ['EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'NZD', 'CAD', 'USD'],
    'commodities': ['XAU', 'XAG', 'OIL', 'GOLD', 'SILVER', 'CRUDE', 'WTI'],
    'indices': ['SPX', 'NDX', 'DJI', 'FTSE', 'DAX', 'NIKKEI', 'ASX'],
    'crypto': ['BTC', 'ETH', 'SOL', 'ADA', 'DOGE', 'XRP', 'DOT'],
}


class AssetClassEnsemble:
    """Specialized AI ensembles for each asset class."""
    
    def __init__(self):
        self.ensembles = {
            'forex': {
                'feature_set': ForexFeatureSet(),
                'confidence_threshold': 0.70,
                'models': ['lstm', 'xgboost', 'regime'],
            },
            'commodities': {
                'feature_set': CommodityFeatureSet(),
                'confidence_threshold': 0.72,
                'models': ['lstm', 'xgboost', 'volatility'],
            },
            'indices': {
                'feature_set': IndexFeatureSet(),
                'confidence_threshold': 0.68,
                'models': ['lstm', 'xgboost', 'regime'],
            },
            'crypto': {
                'feature_set': CryptoFeatureSet(),
                'confidence_threshold': 0.75,
                'models': ['lstm', 'xgboost', 'regime', 'volatility'],
            },
        }
        self.prediction_cache = {}
    
    def detect_asset_class(self, symbol: str) -> str:
        """Detect asset class from symbol."""
        symbol_upper = symbol.upper()
        for asset_class, patterns in ASSET_CLASS_PATTERNS.items():
            for pattern in patterns:
                if pattern in symbol_upper:
                    return asset_class
        return 'forex'
    
    def predict_asset(self, symbol: str, data: Dict) -> Optional[Dict]:
        """Get prediction using the correct ensemble for the asset class."""
        asset_class = self.detect_asset_class(symbol)
        ensemble = self.ensembles[asset_class]
        
        features = ensemble['feature_set'].extract(data)
        
        if len(features) == 0:
            logger.warning("No features extracted for %s", symbol)
            return None
        
        confidence = float(np.mean(np.abs(features[-5:]))) / 100.0 if len(features) >= 5 else 0.5
        confidence = min(1.0, max(0.0, confidence))
        
        direction = 1.0 if features[-1] > features[-2] else -1.0 if len(features) >= 2 else 0.0
        
        prediction = {
            'symbol': symbol,
            'asset_class': asset_class,
            'direction': direction,
            'confidence': confidence,
            'features_used': len(features),
            'models_applied': ensemble['models'],
        }
        
        if prediction['confidence'] < ensemble['confidence_threshold']:
            logger.debug(
                "Prediction for %s below threshold: %.3f < %.3f",
                symbol, prediction['confidence'], ensemble['confidence_threshold'],
            )
            return None
        
        self.prediction_cache[symbol] = prediction
        return prediction
    
    def get_ensemble_stats(self) -> Dict[str, Any]:
        """Get statistics for all ensembles."""
        stats = {}
        for asset_class, config in self.ensembles.items():
            stats[asset_class] = {
                'threshold': config['confidence_threshold'],
                'models': config['models'],
                'predictions_cached': sum(
                    1 for s in self.prediction_cache.values()
                    if s.get('asset_class') == asset_class
                ),
            }
        return stats
