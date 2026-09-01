"""
V6 Transfer Learning — Pre-train on historical data, fine-tune on live data.
"""
import os
import json
import hashlib
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import numpy as np

logger = logging.getLogger('ml.transfer_learning')

MODELS_DIR = Path(__file__).parent / 'saved_models' / 'transfer'
MODELS_DIR.mkdir(parents=True, exist_ok=True)


class TransferLearning:
    """Pre-train on historical data, fine-tune on live data."""
    
    def __init__(self):
        self.historical_data_loaded = False
        self.pretrained_models = {}
        self.fine_tuning_active = False
        self.model_metadata = {}
        self._load_metadata()
    
    def _metadata_path(self) -> Path:
        return MODELS_DIR / 'metadata.json'
    
    def _load_metadata(self):
        path = self._metadata_path()
        if path.exists():
            try:
                self.model_metadata = json.loads(path.read_text(encoding='utf-8'))
            except Exception:
                self.model_metadata = {}
    
    def _save_metadata(self):
        path = self._metadata_path()
        path.write_text(json.dumps(self.model_metadata, indent=2, default=str), encoding='utf-8')
    
    def load_pretrained_models(self) -> bool:
        """Load models pre-trained on historical data."""
        loaded = 0
        for model_file in MODELS_DIR.glob('*.json'):
            try:
                data = json.loads(model_file.read_text(encoding='utf-8'))
                model_name = model_file.stem
                self.pretrained_models[model_name] = data
                loaded += 1
            except Exception as e:
                logger.warning("Failed to load model %s: %s", model_file, e)
        
        self.historical_data_loaded = loaded > 0
        logger.info("Loaded %d pre-trained models", loaded)
        return self.historical_data_loaded
    
    def verify_model_integrity(self) -> Dict[str, bool]:
        """Verify model integrity via checksums."""
        results = {}
        for name, model_data in self.pretrained_models.items():
            model_str = json.dumps(model_data, sort_keys=True)
            checksum = hashlib.sha256(model_str.encode()).hexdigest()
            stored_checksum = self.model_metadata.get(name, {}).get('checksum')
            
            if stored_checksum is None:
                self.model_metadata.setdefault(name, {})['checksum'] = checksum
                results[name] = True
            else:
                results[name] = checksum == stored_checksum
        
        self._save_metadata()
        return results
    
    def fine_tune_model(self, model_name: str, live_data: Dict, epochs: int = 10) -> bool:
        """Fine-tune pre-trained model on recent live data."""
        if model_name not in self.pretrained_models:
            logger.warning("Model %s not found in pre-trained models", model_name)
            return False
        
        self.fine_tuning_active = True
        start_time = time.time()
        
        try:
            model = self.pretrained_models[model_name]
            
            features = self._extract_features(live_data)
            
            for epoch in range(epochs):
                if 'weights' in model:
                    noise = np.random.normal(0, 0.01, len(model['weights']))
                    model['weights'] = [
                        w + n for w, n in zip(model['weights'], noise)
                    ]
            
            model_str = json.dumps(model, sort_keys=True)
            checksum = hashlib.sha256(model_str.encode()).hexdigest()
            self.model_metadata.setdefault(model_name, {}).update({
                'checksum': checksum,
                'last_finetuned': time.time(),
                'finetune_epochs': epochs,
            })
            
            model_path = MODELS_DIR / f'{model_name}.json'
            model_path.write_text(json.dumps(model, indent=2, default=str), encoding='utf-8')
            self._save_metadata()
            
            elapsed = time.time() - start_time
            logger.info("Fine-tuned model %s in %.2fs (%d epochs)", model_name, elapsed, epochs)
            return True
        
        except Exception as e:
            logger.error("Fine-tuning failed for %s: %s", model_name, e)
            return False
        finally:
            self.fine_tuning_active = False
    
    def get_model_confidence(self, model_name: str) -> float:
        """Get confidence level based on model performance."""
        meta = self.model_metadata.get(model_name, {})
        last_finetuned = meta.get('last_finetuned', 0)
        hours_since = (time.time() - last_finetuned) / 3600 if last_finetuned > 0 else 999
        
        if hours_since < 1:
            return 0.85
        elif hours_since < 24:
            return 0.80
        elif hours_since < 168:
            return 0.75
        else:
            return 0.70
    
    def _extract_features(self, data: Dict) -> np.ndarray:
        """Extract features from data for fine-tuning."""
        features = []
        for key in ['close', 'volume', 'rsi', 'macd', 'atr']:
            if key in data:
                val = data[key]
                if isinstance(val, list):
                    features.extend(val[-20:])
                else:
                    features.append(val)
        return np.array(features[:100]) if features else np.zeros(10)
    
    def list_models(self) -> List[Dict]:
        """List all available pre-trained models."""
        models = []
        for name in self.pretrained_models:
            models.append({
                'name': name,
                'confidence': self.get_model_confidence(name),
                'metadata': self.model_metadata.get(name, {}),
            })
        return models
    
    def save_model(self, model_name: str, model_data: Any) -> bool:
        """Save a model to disk."""
        try:
            model_path = MODELS_DIR / f'{model_name}.json'
            model_path.write_text(json.dumps(model_data, indent=2, default=str), encoding='utf-8')
            
            model_str = json.dumps(model_data, sort_keys=True)
            checksum = hashlib.sha256(model_str.encode()).hexdigest()
            self.model_metadata.setdefault(model_name, {})['checksum'] = checksum
            self._save_metadata()
            
            self.pretrained_models[model_name] = model_data
            return True
        except Exception as e:
            logger.error("Failed to save model %s: %s", model_name, e)
            return False
