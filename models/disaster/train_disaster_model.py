"""
train_disaster_model.py
────────────────────────
Trains an XGBoost multiclass classifier to predict disaster type
and severity with a 3-hour lead time.

Inputs  : Preprocessed DisasterRecord rows
Target  : disaster_type_enc (multiclass), severity_enc (multiclass)
Outputs : models/disaster/model_registry/<version>/disaster_model.pkl
          models/disaster/model_registry/<version>/metadata.json
          models/disaster/model_registry/baseline_stats.json
          models/disaster/model_registry/active/active_version.json (pointer)
"""

from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from loguru import logger
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sqlalchemy import update
from xgboost import XGBClassifier

from backend.core.config import settings
from data_pipeline.preprocessing.preprocess_disaster import (
    RAW_FEATURE_COLS,
    preprocess_disaster_batch,
)
from data_pipeline.retraining.pipeline_state import update_last_train
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import ModelVersion

REGISTRY_ROOT = Path(settings.MODEL_REGISTRY_PATH) / "disaster" / "model_registry"
REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = RAW_FEATURE_COLS  # cape, wind_gusts_10m, precipitation, etc.
TARGET_COL = "disaster_type_enc"


async def train_disaster_model() -> Path:
    logger.info("Loading preprocessed disaster data...")
    df = await preprocess_disaster_batch(limit=600_000)

    if df.empty or len(df) < 50:
        logger.error("Not enough disaster data. Run ingestion or seed_database.py first.")
        return Path()

    feat_cols = [c for c in FEATURE_COLS if c in df.columns]
    X = df[feat_cols].fillna(0)
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)

    logger.info(f"Training XGBoost classifier on {len(X_train)} rows...")
    model = XGBClassifier(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        n_jobs=-1,
        tree_method="hist",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)
    acc = float(report.get("accuracy", 0))
    logger.info(f"Validation accuracy: {acc:.4f}")

    # ── Save Versioned Artifact ───────────────────────────────────────────────
    version = f"v_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    version_dir = REGISTRY_ROOT / version
    version_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = version_dir / "disaster_model.pkl"
    joblib.dump(model, pkl_path)

    metadata = {
        "version": version,
        "model_type": "disaster",
        "pkl_path": str(pkl_path),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_rows": len(X_train),
        "feature_cols": feat_cols,
        "metrics": report,
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

    active_pkl = active_dir / "disaster_model.pkl"
    shutil.copy2(pkl_path, active_pkl)
    shutil.copy2(version_dir / "metadata.json", active_dir / "metadata.json")

    with open(active_dir / "active_version.json", "w") as f:
        json.dump(
            {
                "version": version,
                "model_type": "disaster",
                "pkl_path": str(pkl_path.resolve()),
                "active_pkl": str(active_pkl.resolve()),
                "activated_at": datetime.now(timezone.utc).isoformat(),
                "metrics": {"accuracy": acc},
            },
            f,
            indent=2,
        )

    # ── Record in DB (ModelVersion) ──────────────────────────────────────────
    try:
        async with get_async_session() as session:
            await session.execute(
                update(ModelVersion)
                .where(ModelVersion.model_type == "disaster")
                .values(is_active=False)
            )
            mv = ModelVersion(
                model_type="disaster",
                version=version,
                pkl_path=str(pkl_path),
                metrics={"accuracy": acc},
                is_active=True,
                training_rows=len(X_train),
                notes=f"Trained automatically with {len(X_train)} rows",
            )
            session.add(mv)
            await session.commit()
            logger.info(f"Recorded ModelVersion in DB for disaster ({version})")
    except Exception as exc:
        logger.warning(f"Could not record ModelVersion in DB: {exc}")

    # ── Update Pipeline State ────────────────────────────────────────────────
    try:
        update_last_train("disaster", len(df))
    except Exception as exc:
        logger.warning(f"Could not update pipeline_state: {exc}")

    logger.success(f"Disaster model saved → {pkl_path} and active directory updated")
    return pkl_path


if __name__ == "__main__":
    asyncio.run(train_disaster_model())
