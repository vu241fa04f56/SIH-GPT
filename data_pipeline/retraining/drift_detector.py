"""
drift_detector.py
─────────────────
Population Stability Index (PSI) based drift detector for all 3 models:
  1. Weather
  2. Agro
  3. Disaster

Compares the distribution of the most recent N rows against
the training baseline stored in the model registry.

If PSI > threshold for a given model type, triggers retraining.

PSI interpretation:
  PSI < 0.1   → no significant change
  0.1–0.2     → moderate change, monitor
  PSI > 0.2   → significant drift, retrain

Run standalone:
    python -m data_pipeline.retraining.drift_detector
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import select

from backend.core.config import settings
from data_pipeline.preprocessing.preprocess_agro import (
    AGRO_NUMERIC_COLS,
    clean_agro_df,
)
from data_pipeline.preprocessing.preprocess_disaster import (
    RAW_FEATURE_COLS as DISASTER_FEATURE_COLS,
    clean_disaster_df,
)
from data_pipeline.preprocessing.preprocess_weather import (
    WEATHER_FEATURE_COLS,
    clean_weather_df,
)
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import (
    AgroRecord,
    DisasterRecord,
    ModelVersion,
    WeatherRecord,
)

PSI_THRESHOLD = 0.2
RECENT_ROWS = 5_000
N_BINS = 10


def compute_psi(expected: np.ndarray, actual: np.ndarray, bins: int = N_BINS) -> float:
    """
    Compute Population Stability Index between two distributions.

    Parameters
    ----------
    expected : 1-D array from the training baseline.
    actual   : 1-D array from recent production data.
    bins     : Number of histogram bins (use training bin edges for consistency).

    Returns
    -------
    PSI score (float). Higher = more drift.
    """
    eps = 1e-8
    breakpoints = np.percentile(expected, np.linspace(0, 100, bins + 1))
    breakpoints = np.unique(breakpoints)

    if len(breakpoints) < 2:
        return 0.0

    expected_pct = np.histogram(expected, bins=breakpoints)[0] / len(expected) + eps
    actual_pct = np.histogram(actual, bins=breakpoints)[0] / len(actual) + eps

    psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi)


def _load_baseline(model_type: str) -> dict | None:
    """
    Load baseline feature statistics stored during training.
    Expected file: models/<type>/model_registry/baseline_stats.json
    """
    path = Path(settings.MODEL_REGISTRY_PATH) / model_type / "model_registry" / "baseline_stats.json"
    if not path.exists():
        logger.warning(f"No baseline stats at {path} — skipping drift check for {model_type}")
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as exc:
        logger.warning(f"Could not load baseline stats for {model_type}: {exc}")
        return None


# ─── Weather Drift ───────────────────────────────────────────────────────────

async def _load_recent_weather() -> pd.DataFrame:
    """Load the most recent RECENT_ROWS weather records."""
    async with get_async_session() as session:
        result = await session.execute(
            select(WeatherRecord)
            .order_by(WeatherRecord.timestamp.desc())
            .limit(RECENT_ROWS)
        )
        records = result.scalars().all()

    if not records:
        return pd.DataFrame()

    rows = [
        {col: getattr(r, col) for col in WEATHER_FEATURE_COLS if hasattr(r, col)}
        for r in records
    ]
    return pd.DataFrame(rows)


async def check_weather_drift() -> float:
    """Return mean PSI across weather features vs. training baseline."""
    df_recent = await _load_recent_weather()
    if df_recent.empty:
        return 0.0

    baseline = _load_baseline("weather")
    if not baseline:
        return 0.0

    psi_scores = []
    df_clean = clean_weather_df(df_recent)
    for col in WEATHER_FEATURE_COLS:
        if col not in df_clean.columns or col not in baseline:
            continue
        b_vals = np.array(baseline[col].get("sample", []))
        if len(b_vals) == 0:
            continue
        a_vals = df_clean[col].dropna().values
        if len(a_vals) < 50:
            continue
        psi_scores.append(compute_psi(b_vals, a_vals))

    mean_psi = float(np.mean(psi_scores)) if psi_scores else 0.0
    logger.info(f"Weather drift PSI = {mean_psi:.4f} (threshold={PSI_THRESHOLD})")
    return mean_psi


# ─── Agro Drift ──────────────────────────────────────────────────────────────

async def _load_recent_agro() -> pd.DataFrame:
    """Load the most recent RECENT_ROWS agro records."""
    async with get_async_session() as session:
        result = await session.execute(
            select(AgroRecord)
            .order_by(AgroRecord.timestamp.desc())
            .limit(RECENT_ROWS)
        )
        records = result.scalars().all()

    if not records:
        return pd.DataFrame()

    rows = [
        {
            "id": r.id, "city_id": r.city_id, "timestamp": r.timestamp,
            "crop_type": r.crop_type or "other",
            "growth_stage": r.growth_stage or "growing",
            "season": r.season or "kharif",
            "month": r.month,
            "advisory_label": r.advisory_label,
            "temperature_2m": r.temperature_2m,
            "relative_humidity_2m": r.relative_humidity_2m,
            "precipitation": r.precipitation,
            "et0_fao_evapotranspiration": r.et0_fao_evapotranspiration,
            "wind_speed_10m": r.wind_speed_10m,
            "cloud_cover": r.cloud_cover,
            "uv_index": r.uv_index,
            "shortwave_radiation": r.shortwave_radiation,
            "elevation_m": r.elevation_m,
            "features": r.features or {},
        }
        for r in records
    ]
    return pd.DataFrame(rows)


async def check_agro_drift() -> float:
    """Return mean PSI across agro features vs. training baseline."""
    df_recent = await _load_recent_agro()
    if df_recent.empty:
        return 0.0

    baseline = _load_baseline("agro")
    if not baseline:
        return 0.0

    psi_scores = []
    df_clean = clean_agro_df(df_recent)
    for col in AGRO_NUMERIC_COLS:
        if col not in df_clean.columns or col not in baseline:
            continue
        b_vals = np.array(baseline[col].get("sample", []))
        if len(b_vals) == 0:
            continue
        a_vals = df_clean[col].dropna().values
        if len(a_vals) < 50:
            continue
        psi_scores.append(compute_psi(b_vals, a_vals))

    mean_psi = float(np.mean(psi_scores)) if psi_scores else 0.0
    logger.info(f"Agro drift PSI = {mean_psi:.4f} (threshold={PSI_THRESHOLD})")
    return mean_psi


# ─── Disaster Drift ──────────────────────────────────────────────────────────

async def _load_recent_disaster() -> pd.DataFrame:
    """Load the most recent RECENT_ROWS disaster records."""
    async with get_async_session() as session:
        result = await session.execute(
            select(DisasterRecord)
            .order_by(DisasterRecord.timestamp.desc())
            .limit(RECENT_ROWS)
        )
        records = result.scalars().all()

    if not records:
        return pd.DataFrame()

    rows = [
        {
            "id": r.id, "city_id": r.city_id, "timestamp": r.timestamp,
            "disaster_type": r.disaster_type,
            "severity": r.severity or "low",
            "risk_score": r.risk_score,
            "cape": r.cape,
            "wind_gusts_10m": r.wind_gusts_10m,
            "precipitation": r.precipitation,
            "lifted_index": r.lifted_index,
            "pressure_msl": r.pressure_msl,
            "rain": r.rain,
            "snowfall": r.snowfall,
            "raw_features": r.raw_features or {},
        }
        for r in records
    ]
    return pd.DataFrame(rows)


async def check_disaster_drift() -> float:
    """Return mean PSI across disaster features vs. training baseline."""
    df_recent = await _load_recent_disaster()
    if df_recent.empty:
        return 0.0

    baseline = _load_baseline("disaster")
    if not baseline:
        return 0.0

    psi_scores = []
    df_clean = clean_disaster_df(df_recent)
    for col in DISASTER_FEATURE_COLS:
        if col not in df_clean.columns or col not in baseline:
            continue
        b_vals = np.array(baseline[col].get("sample", []))
        if len(b_vals) == 0:
            continue
        a_vals = df_clean[col].dropna().values
        if len(a_vals) < 50:
            continue
        psi_scores.append(compute_psi(b_vals, a_vals))

    mean_psi = float(np.mean(psi_scores)) if psi_scores else 0.0
    logger.info(f"Disaster drift PSI = {mean_psi:.4f} (threshold={PSI_THRESHOLD})")
    return mean_psi


# ─── Combined Check ──────────────────────────────────────────────────────────

async def run_drift_check() -> dict[str, float]:
    """
    Run drift checks for all 3 model types.
    Trigger retraining only where PSI exceeds threshold.
    Returns dict of {model_type: psi_score}.
    """
    results: dict[str, float] = {}

    # 1. Weather
    try:
        weather_psi = await check_weather_drift()
        results["weather"] = weather_psi
        if weather_psi > PSI_THRESHOLD:
            logger.warning(f"Weather drift detected (PSI={weather_psi:.3f}). Triggering retrain...")
            from data_pipeline.retraining.retrain_weather_model import retrain_weather_model
            await retrain_weather_model()
    except Exception as exc:
        logger.error(f"Failed weather drift check: {exc}")

    # 2. Agro
    try:
        agro_psi = await check_agro_drift()
        results["agro"] = agro_psi
        if agro_psi > PSI_THRESHOLD:
            logger.warning(f"Agro drift detected (PSI={agro_psi:.3f}). Triggering retrain...")
            from data_pipeline.retraining.retrain_agro_model import retrain_agro_model
            await retrain_agro_model()
    except Exception as exc:
        logger.error(f"Failed agro drift check: {exc}")

    # 3. Disaster
    try:
        disaster_psi = await check_disaster_drift()
        results["disaster"] = disaster_psi
        if disaster_psi > PSI_THRESHOLD:
            logger.warning(f"Disaster drift detected (PSI={disaster_psi:.3f}). Triggering retrain...")
            from data_pipeline.retraining.retrain_disaster_model import retrain_disaster_model
            await retrain_disaster_model()
    except Exception as exc:
        logger.error(f"Failed disaster drift check: {exc}")

    return results


if __name__ == "__main__":
    asyncio.run(run_drift_check())
