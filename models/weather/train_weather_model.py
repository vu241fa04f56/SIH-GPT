"""
train_weather_model.py
──────────────────────
Trains an XGBoost multi-output regressor to predict the next-hour values
of all 39 weather features for a given city.

Inputs  : Preprocessed WeatherRecord rows (via preprocess_weather_batch)
Outputs : models/weather/model_registry/<version>/weather_model.pkl
          models/weather/model_registry/<version>/metadata.json
          models/weather/model_registry/baseline_stats.json   (for drift detection)
          models/weather/model_registry/active/active_version.json (pointer)

Usage:
    python models/weather/train_weather_model.py
    # or after seeding + ingestion:
    python -m models.weather.train_weather_model
"""

from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sqlalchemy import update
from xgboost import XGBRegressor

from backend.core.config import settings
from data_pipeline.preprocessing.preprocess_weather import (
    WEATHER_FEATURE_COLS,
    preprocess_weather_batch,
)
from data_pipeline.retraining.pipeline_state import update_last_train
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import ModelVersion

REGISTRY_ROOT = Path(settings.MODEL_REGISTRY_PATH) / "weather" / "model_registry"
REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)

# Features used as model inputs (all but targets; targets are same cols shifted)
# We predict feature[t+1] given feature[t..t-N]
LAG_STEPS = 3  # use last 3 hours as input


def _build_lagged_features(df: pd.DataFrame, target_cols: list[str], lags: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create lag features (t-1, t-2, ..., t-lags) and next-step targets.

    Returns (X, y) DataFrames.
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    feature_dfs = []
    for lag in range(1, lags + 1):
        lagged = df[target_cols].shift(lag).add_suffix(f"_lag{lag}")
        feature_dfs.append(lagged)

    X = pd.concat([df[target_cols]] + feature_dfs, axis=1)
    y = df[target_cols].shift(-1)  # next hour

    # Drop rows with NaN (first/last due to shifting)
    valid = X.notna().all(axis=1) & y.notna().all(axis=1)
    return X[valid], y[valid]


async def train_weather_model() -> Path:
    """Train the weather model and save it to the registry."""
    logger.info("Loading preprocessed weather data...")
    df = await preprocess_weather_batch(limit=200_000)

    if df.empty or len(df) < 100:
        logger.error("Not enough data to train. Run ingestion first.")
        return Path()

    feat_cols = [c for c in WEATHER_FEATURE_COLS if c in df.columns]

    # ── Build lag dataset ─────────────────────────────────────────────────────
    logger.info("Building lag features...")
    X, y = _build_lagged_features(df, feat_cols, LAG_STEPS)

    if len(X) < 50:
        logger.error("Dataset too small after lag feature construction.")
        return Path()

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, shuffle=False)

    # ── Train ─────────────────────────────────────────────────────────────────
    logger.info(f"Training XGBoost MultiOutputRegressor on {len(X_train)} rows...")
    base_reg = XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=-1,
        tree_method="hist",
        random_state=42,
    )
    model = MultiOutputRegressor(base_reg, n_jobs=-1)
    model.fit(X_train, y_train)

    # ── Evaluate ──────────────────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))
    logger.info(f"Validation — MAE: {mae:.4f}  R²: {r2:.4f}")

    # ── Save Versioned Artifact ───────────────────────────────────────────────
    version = f"v_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    version_dir = REGISTRY_ROOT / version
    version_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = version_dir / "weather_model.pkl"
    joblib.dump(model, pkl_path)

    metadata = {
        "version": version,
        "model_type": "weather",
        "pkl_path": str(pkl_path),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_rows": len(X_train),
        "feature_cols": feat_cols,
        "lag_steps": LAG_STEPS,
        "metrics": {"mae": mae, "r2": r2},
    }
    with open(version_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # ── Baseline stats for drift detection ────────────────────────────────────
    baseline_stats = {
        col: {"sample": X_train[col].dropna().tolist()[:2000]}
        for col in feat_cols
        if col in X_train.columns
    }
    with open(REGISTRY_ROOT / "baseline_stats.json", "w") as f:
        json.dump(baseline_stats, f)

    # ── Cross-Platform Active Pointer ─────────────────────────────────────────
    active_dir = REGISTRY_ROOT / "active"
    if active_dir.is_symlink():
        try:
            active_dir.unlink()
        except Exception:
            pass
    active_dir.mkdir(parents=True, exist_ok=True)

    # Copy directly into active/ directory so joblib.load can always find it
    active_pkl = active_dir / "weather_model.pkl"
    shutil.copy2(pkl_path, active_pkl)
    # Also provide weather_model.pickle alias if needed by inference loader
    shutil.copy2(pkl_path, active_dir / "weather_model.pickle")
    shutil.copy2(version_dir / "metadata.json", active_dir / "metadata.json")

    with open(active_dir / "active_version.json", "w") as f:
        json.dump(
            {
                "version": version,
                "model_type": "weather",
                "pkl_path": str(pkl_path.resolve()),
                "active_pkl": str(active_pkl.resolve()),
                "activated_at": datetime.now(timezone.utc).isoformat(),
                "metrics": {"mae": mae, "r2": r2},
            },
            f,
            indent=2,
        )

    # ── Record in DB (ModelVersion) ──────────────────────────────────────────
    try:
        async with get_async_session() as session:
            await session.execute(
                update(ModelVersion)
                .where(ModelVersion.model_type == "weather")
                .values(is_active=False)
            )
            mv = ModelVersion(
                model_type="weather",
                version=version,
                pkl_path=str(pkl_path),
                metrics={"mae": mae, "r2": r2},
                is_active=True,
                training_rows=len(X_train),
                notes=f"Trained automatically with {len(X_train)} rows",
            )
            session.add(mv)
            await session.commit()
            logger.info(f"Recorded ModelVersion in DB for weather ({version})")
    except Exception as exc:
        logger.warning(f"Could not record ModelVersion in DB: {exc}")

    # ── Update Pipeline State ────────────────────────────────────────────────
    try:
        update_last_train("weather", len(df))
    except Exception as exc:
        logger.warning(f"Could not update pipeline_state: {exc}")

    logger.success(f"Weather model saved → {pkl_path} and active directory updated")
    return pkl_path


if __name__ == "__main__":
    asyncio.run(train_weather_model())
