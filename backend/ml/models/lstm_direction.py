import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.models.lstm")


class LSTMDirectionModel:
    """
    LSTM model with attention mechanism for price direction prediction.
    Predicts: Bullish / Bearish / Neutral + confidence score.
    """

    def __init__(
        self,
        sequence_length: int = 60,
        n_features: int = 150,
        lstm_units_1: int = 128,
        lstm_units_2: int = 64,
        dense_units: int = 32,
        dropout_rate: float = 0.3,
        learning_rate: float = 0.001,
        n_classes: int = 3,
    ):
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.lstm_units_1 = lstm_units_1
        self.lstm_units_2 = lstm_units_2
        self.dense_units = dense_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.n_classes = n_classes
        self._model = None
        self._history = None

    def build_model(self):
        try:
            import tensorflow as tf
            from tensorflow.keras.layers import (
                LSTM, Dense, Dropout, Input, Multiply,
                Permute, RepeatVector, Flatten, Activation,
            )
            from tensorflow.keras.models import Model

            inputs = Input(shape=(self.sequence_length, self.n_features))

            lstm_out_1 = LSTM(
                self.lstm_units_1,
                return_sequences=True,
                dropout=self.dropout_rate,
                recurrent_dropout=self.dropout_rate,
            )(inputs)

            lstm_out_2 = LSTM(
                self.lstm_units_2,
                return_sequences=True,
                dropout=self.dropout_rate,
                recurrent_dropout=self.dropout_rate,
            )(lstm_out_1)

            attention = Dense(1, activation="tanh")(lstm_out_2)
            attention = Flatten()(attention)
            attention = Activation("softmax")(attention)
            attention = RepeatVector(self.lstm_units_2)(attention)
            attention = Permute([2, 1])(attention)

            context = Multiply()([lstm_out_2, attention])
            context = tf.keras.layers.Lambda(
                lambda x: tf.keras.backend.sum(x, axis=1)
            )(context)

            dense = Dense(self.dense_units, activation="relu")(context)
            dense = Dropout(self.dropout_rate)(dense)
            output = Dense(self.n_classes, activation="softmax")(dense)

            self._model = Model(inputs=inputs, outputs=output)
            self._model.compile(
                optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
                loss="sparse_categorical_crossentropy",
                metrics=["accuracy"],
            )

            logger.info("LSTM model built: %d params", self._model.count_params())
            return self._model

        except ImportError:
            logger.error("TensorFlow not installed. Cannot build LSTM model.")
            return None

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        patience: int = 15,
    ) -> Dict[str, Any]:
        if self._model is None:
            self.build_model()

        if self._model is None:
            return {"error": "Model not built"}

        try:
            import tensorflow as tf

            callbacks = [
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_loss",
                    patience=patience,
                    restore_best_weights=True,
                ),
                tf.keras.callbacks.ReduceLROnPlateau(
                    monitor="val_loss",
                    factor=0.5,
                    patience=5,
                    min_lr=1e-6,
                ),
            ]

            self._history = self._model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=epochs,
                batch_size=batch_size,
                callbacks=callbacks,
                verbose=1,
            )

            return {
                "epochs_trained": len(self._history.history["loss"]),
                "final_train_loss": self._history.history["loss"][-1],
                "final_val_loss": self._history.history["val_loss"][-1],
                "final_train_acc": self._history.history["accuracy"][-1],
                "final_val_acc": self._history.history["val_accuracy"][-1],
            }

        except Exception as e:
            logger.error("Training error: %s", e)
            return {"error": str(e)}

    def predict(self, X: np.ndarray) -> Dict[str, Any]:
        if self._model is None:
            return {"error": "Model not loaded"}

        try:
            predictions = self._model.predict(X, verbose=0)
            predicted_class = np.argmax(predictions, axis=1)
            confidence = np.max(predictions, axis=1)

            class_map = {0: "BEARISH", 1: "BULLISH", 2: "NEUTRAL"}

            return {
                "predictions": [class_map[c] for c in predicted_class],
                "confidence": confidence.tolist(),
                "probabilities": predictions.tolist(),
                "direction": class_map[predicted_class[-1]],
                "confidence_score": float(confidence[-1]),
            }

        except Exception as e:
            logger.error("Prediction error: %s", e)
            return {"error": str(e)}

    def predict_batch(self, X: np.ndarray) -> Dict[str, Any]:
        return self.predict(X)

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        if self._model is None:
            return {"error": "Model not loaded"}

        try:
            loss, accuracy = self._model.evaluate(X_test, y_test, verbose=0)

            predictions = self._model.predict(X_test, verbose=0)
            predicted_class = np.argmax(predictions, axis=1)

            from sklearn.metrics import (
                classification_report, confusion_matrix, f1_score,
            )

            report = classification_report(
                y_test, predicted_class,
                target_names=["BEARISH", "BULLISH", "NEUTRAL"],
                output_dict=True,
            )

            cm = confusion_matrix(y_test, predicted_class)

            return {
                "loss": float(loss),
                "accuracy": float(accuracy),
                "f1_macro": float(f1_score(y_test, predicted_class, average="macro")),
                "classification_report": report,
                "confusion_matrix": cm.tolist(),
            }

        except Exception as e:
            logger.error("Evaluation error: %s", e)
            return {"error": str(e)}

    def save_model(self, path: str):
        if self._model is not None:
            self._model.save(path)
            logger.info("Model saved to %s", path)

    def load_model(self, path: str):
        try:
            import tensorflow as tf
            self._model = tf.keras.models.load_model(path)
            logger.info("Model loaded from %s", path)
        except Exception as e:
            logger.error("Failed to load model: %s", e)

    @property
    def summary(self) -> Optional[str]:
        if self._model is not None:
            import io
            import sys
            buf = io.StringIO()
            self._model.summary(print_fn=lambda x: buf.write(x + "\n"))
            return buf.getvalue()
        return None
