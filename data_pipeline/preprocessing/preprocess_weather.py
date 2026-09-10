"""
preprocess_weather.py
─────────────────────
Preprocessing pipeline for raw WeatherRecord rows.

Steps:
  1. Load unprocessed rows from DB
  2. Impute missing values (median for numerics)
  3. Clip outliers (3-sigma)
  4. Min-max normalise numeric columns
  5. Mark rows as processed
  6. Return a DataFrame suitable for model training / inference

Usage:
    from data_pipeline.preprocessing.preprocess_weather import preprocess_weather_batch

    df = await preprocess_weather_batch(city_id=42)
"""

from __future__ import annotations

import asyncio

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import select, update

from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import WeatherRecord

# Persisted numeric API columns. The bundled weather model separately builds
# its exact 39 engineered inputs from these observations and their lags.
WEATHER_FEATURE_COLS = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature",
    "precipitation", "rain", "snowfall", "snow_depth",
    "weather_code", "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
    "surface_pressure", "pressure_msl", "vapour_pressure_deficit",
    "wind_speed_10m", "wind_speed_100m", "wind_direction_10m", "wind_direction_100m",
    "wind_gusts_10m", "et0_fao_evapotranspiration", "cape", "lifted_index",
    "shortwave_radiation", "direct_radiation", "direct_normal_irradiance", "diffuse_radiation",
    "soil_temperature_0_to_7cm", "soil_moisture_0_to_7cm",
    "uv_index", "uv_index_clear_sky",
    "us_aqi", "pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide",
    "sulphur_dioxide", "ozone", "ammonia", "dust", "alder_pollen",
    "wave_height", "sea_surface_temperature",
]

# Columns to clip at physical limits before normalisation
CLIP_BOUNDS: dict[str, tuple[float, float]] = {
    "relative_humidity_2m": (0, 100),
    "cloud_cover": (0, 100),
    "uv_index": (0, 16),
    "precipitation": (0, 500),
    "wind_speed_10m": (0, 300),
    "wind_gusts_10m": (0, 400),
    "cape": (0, 8000),
}


def clean_weather_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply full preprocessing pipeline to a raw weather DataFrame.

    Parameters
    ----------
    df : Raw DataFrame with WeatherRecord columns.

    Returns
    -------
    pd.DataFrame with imputed, clipped, and normalised numeric features.
    """
    feat_cols = [c for c in WEATHER_FEATURE_COLS if c in df.columns]
    df = df.copy()

    # ── 1. Median imputation ──────────────────────────────────────────────────
    for col in feat_cols:
        if df[col].isna().any():
            median = df[col].median()
            df[col] = df[col].fillna(median if not np.isnan(median) else 0)

    # ── 2. Physical clip ──────────────────────────────────────────────────────
    for col, (lo, hi) in CLIP_BOUNDS.items():
        if col in df.columns:
            df[col] = df[col].clip(lo, hi)

    # ── 3. 3-sigma outlier clip ───────────────────────────────────────────────
    for col in feat_cols:
        mu, sigma = df[col].mean(), df[col].std()
        if sigma > 0:
            df[col] = df[col].clip(mu - 3 * sigma, mu + 3 * sigma)

    # ── 4. Min-max normalisation ──────────────────────────────────────────────
    for col in feat_cols:
        col_min, col_max = df[col].min(), df[col].max()
        if col_max > col_min:
            df[col] = (df[col] - col_min) / (col_max - col_min)
        else:
            df[col] = 0.0

    return df


async def preprocess_weather_batch(city_id: int | None = None, limit: int = 10_000) -> pd.DataFrame:
    """
    Load unprocessed WeatherRecord rows, clean them, mark as processed.

    Parameters
    ----------
    city_id : If given, only process rows for that city.
    limit   : Max rows to process in one batch.

    Returns
    -------
    Cleaned DataFrame.
    """
    async with get_async_session() as session:
        query = select(WeatherRecord).where(WeatherRecord.is_processed == False).limit(limit)  # noqa: E712
        if city_id is not None:
            query = query.where(WeatherRecord.city_id == city_id)
        result = await session.execute(query)
        records = result.scalars().all()

    if not records:
        logger.info("No unprocessed weather records found.")
        return pd.DataFrame()

    rows = [
        {col: getattr(r, col) for col in ["id", "city_id", "timestamp"] + WEATHER_FEATURE_COLS}
        for r in records
    ]
    df = pd.DataFrame(rows)
    df_clean = clean_weather_df(df)

    # Mark rows as processed
    ids = df["id"].tolist()
    async with get_async_session() as session:
        await session.execute(
            update(WeatherRecord).where(WeatherRecord.id.in_(ids)).values(is_processed=True)
        )

    logger.success(f"Preprocessed {len(df_clean)} weather rows")
    return df_clean


if __name__ == "__main__":
    asyncio.run(preprocess_weather_batch())
