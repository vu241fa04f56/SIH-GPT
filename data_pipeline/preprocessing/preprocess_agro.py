"""
preprocess_agro.py
──────────────────
Preprocessing pipeline for raw AgroRecord rows.

Steps:
  1. Load unprocessed agro rows (prefer individual typed columns, fallback JSONB)
  2. Encode crop_type and growth_stage as integers
  3. Normalise numeric weather features
  4. Mark rows processed
"""

from __future__ import annotations

import asyncio

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import select, update

from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import AgroRecord

CROP_MAP: dict[str, int] = {
    "rice": 0, "wheat": 1, "maize": 2, "sugarcane": 3,
    "cotton": 4, "soybean": 5, "coconut": 6, "rubber": 7,
    "tea": 8, "coffee": 9, "jute": 10, "ragi": 11,
    "groundnut": 12, "mustard": 13, "bajra": 14, "gram": 15,
    "chilli": 16, "other": 99,
}

GROWTH_STAGE_MAP: dict[str, int] = {
    "sowing": 0, "germination": 1, "tillering": 2, "vegetative": 3,
    "jointing": 4, "heading": 5, "flowering": 6, "tasseling": 6,
    "boll_development": 6, "pod_filling": 6, "maturity": 7,
    "harvest": 8, "dormant": 9, "growing": 5, "off_season": 9,
}

SEASON_MAP: dict[str, int] = {
    "kharif": 0, "rabi": 1, "perennial": 2, "off_season": 3,
}

# Individual typed columns added in 0002 migration
AGRO_NUMERIC_COLS = [
    "temperature_2m", "relative_humidity_2m", "precipitation",
    "et0_fao_evapotranspiration", "wind_speed_10m", "cloud_cover",
    "uv_index", "shortwave_radiation", "elevation_m",
]


def clean_agro_df(df: pd.DataFrame) -> pd.DataFrame:
    """Apply full preprocessing pipeline to a raw agro DataFrame."""
    df = df.copy()

    # ── Categorical encodings ─────────────────────────────────────────────────
    df["crop_enc"]   = df["crop_type"].str.lower().map(CROP_MAP).fillna(CROP_MAP["other"]).astype(int)
    df["stage_enc"]  = df["growth_stage"].str.lower().map(GROWTH_STAGE_MAP).fillna(5).astype(int)
    df["season_enc"] = df.get("season", pd.Series(["kharif"] * len(df))).str.lower().map(SEASON_MAP).fillna(0).astype(int)
    df["month"]      = df.get("month", df["timestamp"].dt.month if "timestamp" in df.columns else 1).fillna(1).astype(int)

    # ── Resolve numeric cols: prefer individual columns, fallback to JSONB ───
    for col in AGRO_NUMERIC_COLS:
        if col not in df.columns or df[col].isna().all():
            # Try to extract from JSONB features blob
            if "features" in df.columns:
                df[col] = df["features"].apply(
                    lambda x: x.get(col) if isinstance(x, dict) else None
                ).astype(float)

    # ── Impute + normalise ─────────────────────────────────────────────────────
    for col in AGRO_NUMERIC_COLS:
        if col in df.columns:
            median = df[col].median()
            df[col] = df[col].fillna(0.0 if np.isnan(median) else median)
            col_min, col_max = df[col].min(), df[col].max()
            if col_max > col_min:
                df[col] = (df[col] - col_min) / (col_max - col_min)

    return df


async def preprocess_agro_batch(limit: int = 20_000) -> pd.DataFrame:
    """Load, clean, and mark unprocessed AgroRecord rows."""
    async with get_async_session() as session:
        result = await session.execute(
            select(AgroRecord).where(AgroRecord.is_processed == False).limit(limit)  # noqa: E712
        )
        records = result.scalars().all()

    if not records:
        logger.info("No unprocessed agro records.")
        return pd.DataFrame()

    rows = [
        {
            "id": r.id, "city_id": r.city_id, "timestamp": r.timestamp,
            "crop_type": r.crop_type or "other",
            "growth_stage": r.growth_stage or "growing",
            "season": r.season or "kharif",
            "month": r.month,
            "advisory_label": r.advisory_label,
            # Individual typed columns
            "temperature_2m": r.temperature_2m,
            "relative_humidity_2m": r.relative_humidity_2m,
            "precipitation": r.precipitation,
            "et0_fao_evapotranspiration": r.et0_fao_evapotranspiration,
            "wind_speed_10m": r.wind_speed_10m,
            "cloud_cover": r.cloud_cover,
            "uv_index": r.uv_index,
            "shortwave_radiation": r.shortwave_radiation,
            "elevation_m": r.elevation_m,
            # Legacy JSONB blob (fallback)
            "features": r.features or {},
        }
        for r in records
    ]
    df = pd.DataFrame(rows)
    df_clean = clean_agro_df(df)

    ids = df["id"].tolist()
    async with get_async_session() as session:
        await session.execute(
            update(AgroRecord).where(AgroRecord.id.in_(ids)).values(is_processed=True)
        )

    logger.success(f"Preprocessed {len(df_clean)} agro rows")
    return df_clean


if __name__ == "__main__":
    asyncio.run(preprocess_agro_batch())
