import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler, StandardScaler

logger = logging.getLogger("ml.preprocessing")


class DataPreprocessor:
    """
    Data normalization, windowing, and preprocessing for ML models.
    """

    def __init__(self):
        self._scaler: Optional[StandardScaler] = None
        self._robust_scaler: Optional[RobustScaler] = None
        self._feature_names: list = []
        self._is_fitted = False

    def fit_transform(
        self, X: np.ndarray, feature_names: Optional[list] = None
    ) -> np.ndarray:
        self._feature_names = feature_names or [f"f_{i}" for i in range(X.shape[1])]
        self._scaler = StandardScaler()
        self._robust_scaler = RobustScaler()

        X_2d = X.reshape(-1, X.shape[-1]) if X.ndim == 3 else X

        X_scaled = self._robust_scaler.fit_transform(X_2d)
        X_scaled = self._scaler.fit_transform(X_scaled)

        self._is_fitted = True

        if X.ndim == 3:
            return X_scaled.reshape(X.shape)
        return X_scaled

    def transform(self, X: np.ndarray) -> np.ndarray:
        if not self._is_fitted:
            raise RuntimeError("Preprocessor not fitted. Call fit_transform first.")

        X_2d = X.reshape(-1, X.shape[-1]) if X.ndim == 3 else X
        X_scaled = self._robust_scaler.transform(X_2d)
        X_scaled = self._scaler.transform(X_scaled)

        if X.ndim == 3:
            return X_scaled.reshape(X.shape)
        return X_scaled

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        if not self._is_fitted:
            raise RuntimeError("Preprocessor not fitted.")

        X_2d = X.reshape(-1, X.shape[-1]) if X.ndim == 3 else X
        X_inv = self._scaler.inverse_transform(X_2d)
        X_inv = self._robust_scaler.inverse_transform(X_inv)

        if X.ndim == 3:
            return X_inv.reshape(X.shape)
        return X_inv

    def create_windows(
        self,
        data: np.ndarray,
        window_size: int = 60,
        horizon: int = 1,
    ) -> Tuple[np.ndarray, np.ndarray]:
        X, y = [], []
        for i in range(window_size, len(data) - horizon + 1):
            X.append(data[i - window_size:i])
            y.append(data[i + horizon - 1, :3])
        return np.array(X), np.array(y)

    def handle_nan(self, X: np.ndarray) -> np.ndarray:
        if X.ndim == 3:
            for i in range(X.shape[0]):
                df = pd.DataFrame(X[i])
                df = df.ffill().bfill()
                df = df.fillna(0)
                X[i] = df.values
        else:
            df = pd.DataFrame(X)
            df = df.ffill().bfill()
            df = df.fillna(0)
            X = df.values
        return X

    def remove_outliers(
        self, X: np.ndarray, method: str = "zscore", threshold: float = 4.0
    ) -> np.ndarray:
        if method == "zscore":
            if X.ndim == 3:
                for i in range(X.shape[0]):
                    mean = np.nanmean(X[i], axis=0)
                    std = np.nanstd(X[i], axis=0) + 1e-10
                    z = np.abs((X[i] - mean) / std)
                    X[i][z > threshold] = np.nan
                X = self.handle_nan(X)
            else:
                mean = np.nanmean(X, axis=0)
                std = np.nanstd(X, axis=0) + 1e-10
                z = np.abs((X - mean) / std)
                X[z > threshold] = np.nan
                X = pd.DataFrame(X).ffill().bfill().fillna(0).values
        return X

    def balance_classes(
        self, X: np.ndarray, y: np.ndarray, method: str = "undersample"
    ) -> Tuple[np.ndarray, np.ndarray]:
        from collections import Counter

        if y.ndim > 1:
            y_labels = np.argmax(y, axis=1)
        else:
            y_labels = y

        counter = Counter(y_labels)
        min_count = min(counter.values())

        if method == "undersample":
            indices = []
            for cls in counter.keys():
                cls_indices = np.where(y_labels == cls)[0]
                selected = np.random.choice(cls_indices, min_count, replace=False)
                indices.extend(selected)
            indices = sorted(indices)
            return X[indices], y[indices]

        return X, y

    def save_preprocessor(self, path: str):
        import joblib
        joblib.dump({
            "scaler": self._scaler,
            "robust_scaler": self._robust_scaler,
            "feature_names": self._feature_names,
        }, path)

    def load_preprocessor(self, path: str):
        import joblib
        data = joblib.load(path)
        self._scaler = data["scaler"]
        self._robust_scaler = data["robust_scaler"]
        self._feature_names = data["feature_names"]
        self._is_fitted = True
