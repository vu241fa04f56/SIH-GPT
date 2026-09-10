"""
train_agro_model.py
───────────────────
Trains a Random Forest classifier to produce crop-specific advisory labels.

Advisory labels (examples):
  - "optimal_conditions"
  - "irrigate_now"
  - "delay_sowing"
  - "apply_fungicide"
  - "harvest_window_open"
  - "storm_risk_suspend_operations"

Inputs  : Preprocessed AgroRecord rows (features + advisory_label)
Outputs : models/agro/model_registry/<version>/agro_model.pkl
          models/agro/model_registry/<version>/metadata.json
          models/agro/model_registry/baseline_stats.json
          models/agro/model_registry/active/active_version.json (pointer)
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
from loguru import logger
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sqlalchemy import update

from backend.core.config import settings
from data_pipeline.preprocessing.preprocess_agro import (
    AGRO_NUMERIC_COLS,
    preprocess_agro_batch,
)
from data_pipeline.retraining.pipeline_state import update_last_train
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import ModelVersion

REGISTRY_ROOT = Path(settings.MODEL_REGISTRY_PATH) / "agro" / "model_registry"
REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = AGRO_NUMERIC_COLS + ["crop_enc", "stage_enc"]
TARGET_COL = "advisory_label"


def _rule_based_label(row) -> str:
    """Assign a rule-based advisory label for rows that lack one."""
    try:
        precip = float(row.get("precipitation", 0) or 0)
        temp = float(row.get("temperature_2m", 25) or 25)
        rh = float(row.get("relative_humidity_2m", 60) or 60)
    except Exception:
        precip, temp, rh = 0.0, 25.0, 60.0

    if precip > 50:
        return "storm_risk_suspend_operations"
    if temp > 38:
        return "heat_stress_irrigate"
    if rh > 85:
        return "apply_fungicide"
    if rh < 30:
        return "irrigate_now"
    return "optimal_conditions"


async def train_agro_model() -> Path:
    logger.info("Loading preprocessed agro data...")
    df = await preprocess_agro_batch(limit=100_000)

    if df.empty or len(df) < 50:
        logger.error("Not enough agro data to train.")
        return Path()

    # Fill missing labels with rule-based assignments
    if "advisory_label" not in df.columns or df["advisory_label"].isna().all():
        df["advisory_label"] = df.apply(_rule_based_label, axis=1)
    else:
        mask = df["advisory_label"].isna()
        if mask.any():
            df.loc[mask, "advisory_label"] = df[mask].apply(_rule_based_label, axis=1)

    feat_cols = [c for c in FEATURE_COLS if c in df.columns]
    X = df[feat_cols].fillna(0)
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)

    logger.info(f"Training RandomForest on {len(X_train)} rows...")
    model = RandomForestClassifier(
        n_estimators=200, max_depth=12, n_jobs=-1, random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)
    acc = float(report.get("accuracy", 0))
    logger.info(f"Validation accuracy: {acc:.4f}")

    # ── Save Versioned Artifact ───────────────────────────────────────────────
    version = f"v_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    version_dir = REGISTRY_ROOT / version
    version_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = version_dir / "agro_model.pkl"
    joblib.dump(model, pkl_path)

    metadata = {
        "version": version,
        "model_type": "agro",
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
        for col in AGRO_NUMERIC_COLS
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

    active_pkl = active_dir / "agro_model.pkl"
    shutil.copy2(pkl_path, active_pkl)
    shutil.copy2(version_dir / "metadata.json", active_dir / "metadata.json")

    with open(active_dir / "active_version.json", "w") as f:
        json.dump(
            {
                "version": version,
                "model_type": "agro",
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
                .where(ModelVersion.model_type == "agro")
                .values(is_active=False)
            )
            mv = ModelVersion(
                model_type="agro",
                version=version,
                pkl_path=str(pkl_path),
                metrics={"accuracy": acc},
                is_active=True,
                training_rows=len(X_train),
                notes=f"Trained automatically with {len(X_train)} rows",
            )
            session.add(mv)
            await session.commit()
            logger.info(f"Recorded ModelVersion in DB for agro ({version})")
    except Exception as exc:
        logger.warning(f"Could not record ModelVersion in DB: {exc}")

    # ── Update Pipeline State ────────────────────────────────────────────────
    try:
        update_last_train("agro", len(df))
    except Exception as exc:
        logger.warning(f"Could not update pipeline_state: {exc}")

    logger.success(f"Agro model saved → {pkl_path} and active directory updated")
    return pkl_path


if __name__ == "__main__":
    asyncio.run(train_agro_model())
