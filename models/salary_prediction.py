"""
Salary prediction model for JobPulse AI.

Uses Random Forest / Gradient Boosting to predict salary based on:
- Job role
- Location
- Experience
- Number of skills

Gracefully disables itself if insufficient salary data is available.
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

from src.config import logger

MIN_RECORDS_REQUIRED = 100


class SalaryPredictor:
    """Predict salary based on job attributes."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.model = None
        self.label_encoders: dict = {}
        self.feature_names: list = []
        self.is_trained = False
        self.metrics: dict = {}
        self._error_reason: Optional[str] = None

    def _prepare_features(self) -> pd.DataFrame:
        """Prepare feature matrix from the DataFrame."""
        df = self.df.copy()
        df = df.dropna(subset=["salary_average"])
        if len(df) == 0:
            raise ValueError("No records with salary data available")

        features = pd.DataFrame(index=df.index)

        if "standardized_job_title" in df.columns:
            le = LabelEncoder()
            features["role_encoded"] = le.fit_transform(df["standardized_job_title"].fillna("Unknown"))
            self.label_encoders["standardized_job_title"] = le

        if "city" in df.columns:
            le = LabelEncoder()
            features["location_encoded"] = le.fit_transform(df["city"].fillna("Unknown"))
            self.label_encoders["city"] = le

        if "experience_min" in df.columns:
            features["experience_min"] = pd.to_numeric(df["experience_min"], errors="coerce").fillna(0)
        if "experience_max" in df.columns:
            features["experience_max"] = pd.to_numeric(df["experience_max"], errors="coerce").fillna(0)
        if "experience_category" in df.columns:
            le = LabelEncoder()
            features["exp_category_encoded"] = le.fit_transform(df["experience_category"].fillna("Not Specified"))
            self.label_encoders["experience_category"] = le

        if "industry" in df.columns:
            le = LabelEncoder()
            features["industry_encoded"] = le.fit_transform(df["industry"].fillna("Other"))
            self.label_encoders["industry"] = le

        if "skills_count" in df.columns:
            features["skills_count"] = pd.to_numeric(df["skills_count"], errors="coerce").fillna(0)

        return features

    def train(self, model_type: str = "random_forest") -> dict:
        """
        Train the salary prediction model.

        Parameters
        ----------
        model_type : str
            'random_forest' or 'gradient_boosting'

        Returns
        -------
        dict
            Evaluation metrics (MAE, RMSE, R2 or error reason).
        """
        salary_data = self.df.dropna(subset=["salary_average"])
        if len(salary_data) < MIN_RECORDS_REQUIRED:
            self._error_reason = (
                f"Insufficient data: only {len(salary_data)} records with salary data. "
                f"Minimum required: {MIN_RECORDS_REQUIRED}."
            )
            logger.warning(self._error_reason)
            return {"available": False, "reason": self._error_reason}

        try:
            features = self._prepare_features()
        except Exception as e:
            self._error_reason = f"Failed to prepare features: {e}"
            logger.error(self._error_reason)
            return {"available": False, "reason": self._error_reason}

        if len(features.columns) == 0:
            self._error_reason = "No usable features for salary prediction"
            return {"available": False, "reason": self._error_reason}

        salary_data = salary_data.loc[features.index].copy()
        X = features
        y = salary_data["salary_average"]

        # Filter extreme outliers (>99.5 percentile)
        upper_bound = y.quantile(0.995)
        mask = y <= upper_bound
        X, y = X[mask], y[mask]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        if model_type == "gradient_boosting":
            model = GradientBoostingRegressor(n_estimators=150, max_depth=4, random_state=42)
        else:
            model = RandomForestRegressor(n_estimators=150, max_depth=10, random_state=42)

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        metrics = {
            "available": True,
            "model_type": model_type,
            "mae": float(mean_absolute_error(y_test, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
            "r2": float(r2_score(y_test, y_pred)),
            "n_samples": int(len(y)),
        }

        self.model = model
        self.feature_names = list(X.columns)
        self.is_trained = True
        self.metrics = metrics
        logger.info("Salary model trained: %s", metrics)
        return metrics

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Predict salary for new feature rows."""
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
        for col in self.feature_names:
            if col not in features.columns:
                features[col] = 0
        features = features[self.feature_names]
        return self.model.predict(features)

    def save_model(self, filepath=None) -> str:
        """Save the trained model to a pickle file."""
        if not self.is_trained:
            raise ValueError("Model not trained")
        if filepath is None:
            filepath = Path(__file__).resolve().parent.parent / "models" / "salary_predictor.pkl"
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "label_encoders": self.label_encoders,
                    "feature_names": self.feature_names,
                    "metrics": self.metrics,
                },
                f,
            )
        logger.info("Model saved to %s", filepath)
        return str(filepath)

    @classmethod
    def load_model(cls, filepath=None) -> "SalaryPredictor":
        """Load a trained model from a pickle file."""
        if filepath is None:
            filepath = Path(__file__).resolve().parent.parent / "models" / "salary_predictor.pkl"
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")
        with open(filepath, "rb") as f:
            data = pickle.load(f)
        instance = cls.__new__(cls)
        instance.model = data["model"]
        instance.label_encoders = data["label_encoders"]
        instance.feature_names = data["feature_names"]
        instance.metrics = data["metrics"]
        instance.is_trained = True
        instance.df = pd.DataFrame()
        return instance

    def get_error_reason(self) -> Optional[str]:
        """Return the reason for unavailability, if any."""
        return self._error_reason