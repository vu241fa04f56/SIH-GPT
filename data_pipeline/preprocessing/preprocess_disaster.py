"""
preprocess_disaster.py
──────────────────────
Preprocessing pipeline for raw DisasterRecord rows.

Steps:
  1. Load unprocessed disaster rows
  2. Encode disaster_type and severity as ordinal integers
  3. Normalise risk_score (already 0–1 but clipped)
  4. Flatten raw_features JSONB into feature columns
  5. Mark rows as processed

Usage:
    from data_pipeline.preprocessing.preprocess_disaster import preprocess_disaster_batch
    df = await preprocess_disaster_batch()
"""

from __future__ import annotations

import asyncio

import pandas as pd
from loguru import logger
from sqlalchemy import select, update

from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import DisasterRecord

# ─── Encoding maps ────────────────────────────────────────────────────────────

DISASTER_TYPE_MAP: dict[str, int] = {
    "cyclone": 0,
    "flood": 1,
    "heavy_rain": 2,
    "lightning": 3,
    "earthquake": 4,
    "landslide": 5,
    "typhoon": 6,
    "severe_wind": 7,
    "other": 8,
}

SEVERITY_MAP: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "extreme": 3,
}

# Extreme-weather features that appear in raw_features JSONB
RAW_FEATURE_COLS = [
    "cape", "wind_gusts_10m", "precipitation", "lifted_index",
    "pressure_msl", "rain", "snowfall",
]


def clean_disaster_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply preprocessing to a raw disaster DataFrame.

    Returns a DataFrame with encoded categoricals and flattened JSONB features.
    """
    df = df.copy()

    # ── Encode categoricals ──────────────────────────────────────────────────
    df["disaster_type_enc"] = (
        df["disaster_type"]
        .str.lower()
        .map(DISASTER_TYPE_MAP)
        .fillna(DISASTER_TYPE_MAP["other"])
        .astype(int)
    )
    df["severity_enc"] = (
        df["severity"]
        .str.lower()
        .map(SEVERITY_MAP)
        .fillna(0)
        .astype(int)
    )

    # ── Clip risk_score ───────────────────────────────────────────────────────
    if "risk_score" in df.columns:
        df["risk_score"] = df["risk_score"].clip(0.0, 1.0).fillna(0.0)

    # ── Resolve numeric cols: prefer individual columns, fallback to JSONB ───
    if "raw_features" in df.columns:
        for col in RAW_FEATURE_COLS:
            if col not in df.columns or df[col].isna().all():
                df[col] = df["raw_features"].apply(
                    lambda x: x.get(col) if isinstance(x, dict) else None
                ).astype(float)

    # ── Impute remaining NaNs ────────────────────────────────────────────────
    for col in RAW_FEATURE_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median() if not df[col].isna().all() else 0.0)

    return df


async def preprocess_disaster_batch(limit: int = 50_000) -> pd.DataFrame:
    """Load, clean, and mark unprocessed disaster rows."""
    async with get_async_session() as session:
        result = await session.execute(
            select(DisasterRecord)
            .where(DisasterRecord.is_processed == False)  # noqa: E712
            .limit(limit)
        )
        records = result.scalars().all()

    if not records:
        logger.info("No unprocessed disaster records.")
        return pd.DataFrame()

    rows = [
        {
            "id": r.id,
            "city_id": r.city_id,
            "timestamp": r.timestamp,
            "disaster_type": r.disaster_type,
            "severity": r.severity or "low",
            "risk_score": r.risk_score,
            # Individual typed columns
            "cape": r.cape,
            "wind_gusts_10m": r.wind_gusts_10m,
            "precipitation": r.precipitation,
            "lifted_index": r.lifted_index,
            "pressure_msl": r.pressure_msl,
            "rain": r.rain,
            "snowfall": r.snowfall,
            # Legacy JSONB fallback
            "raw_features": r.raw_features or {},
        }
        for r in records
    ]
    df = pd.DataFrame(rows)
    df_clean = clean_disaster_df(df)

    ids = df["id"].tolist()
    async with get_async_session() as session:
        await session.execute(
            update(DisasterRecord).where(DisasterRecord.id.in_(ids)).values(is_processed=True)
        )

    logger.success(f"Preprocessed {len(df_clean)} disaster rows")
    return df_clean


if __name__ == "__main__":
    asyncio.run(preprocess_disaster_batch())
