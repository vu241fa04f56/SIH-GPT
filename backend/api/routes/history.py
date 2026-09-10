"""
history.py
──────────
Historical weather and climate trend analysis routes.

GET /history/{city_id}            → raw hourly records for N days
GET /history/{city_id}/stats      → daily/weekly/monthly aggregate statistics
GET /history/{city_id}/trend      → linear trend + anomaly for key variables

These endpoints give researchers, climate analysts, and the chatbot tool
access to stored historical Open-Meteo archive data for any of the 130 Indian
cities, covering temperature, precipitation, wind, air quality, and more.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select

from backend.services.geo_service import get_city_by_id
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import WeatherRecord

router = APIRouter()

# ─── Response Schemas ─────────────────────────────────────────────────────────

class HourlyRecord(BaseModel):
    timestamp: datetime
    temperature_2m: Optional[float] = None
    relative_humidity_2m: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed_10m: Optional[float] = None
    wind_gusts_10m: Optional[float] = None
    us_aqi: Optional[float] = None
    uv_index: Optional[float] = None
    cloud_cover: Optional[float] = None
    pressure_msl: Optional[float] = None
    cape: Optional[float] = None


class VariableStat(BaseModel):
    mean: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    std_dev: Optional[float] = None
    total: Optional[float] = None   # meaningful for precipitation


class HistoricalStats(BaseModel):
    city_id: int
    city_name: str
    period_days: int
    record_count: int
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    temperature_2m: VariableStat = VariableStat()
    precipitation: VariableStat = VariableStat()
    wind_speed_10m: VariableStat = VariableStat()
    relative_humidity_2m: VariableStat = VariableStat()
    us_aqi: VariableStat = VariableStat()
    uv_index: VariableStat = VariableStat()


class TrendPoint(BaseModel):
    date: str           # YYYY-MM-DD
    value: Optional[float] = None
    anomaly: Optional[float] = None  # deviation from period mean


class ClimateTrend(BaseModel):
    city_id: int
    city_name: str
    variable: str
    period_days: int
    mean: Optional[float] = None
    trend_direction: str            # "warming", "cooling", "stable", "wetter", "drier"
    daily_points: list[TrendPoint]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_stats(values: list[float]) -> VariableStat:
    vals = [v for v in values if v is not None]
    if not vals:
        return VariableStat()
    return VariableStat(
        mean=round(statistics.mean(vals), 3),
        min=round(min(vals), 3),
        max=round(max(vals), 3),
        std_dev=round(statistics.stdev(vals), 3) if len(vals) > 1 else 0.0,
        total=round(sum(vals), 3),
    )


def _trend_direction(variable: str, daily_means: list[float]) -> str:
    if len(daily_means) < 2:
        return "stable"
    first_half = statistics.mean(daily_means[:len(daily_means)//2])
    second_half = statistics.mean(daily_means[len(daily_means)//2:])
    delta = second_half - first_half
    threshold = 0.3
    if variable in ("precipitation", "rain"):
        return "wetter" if delta > threshold else ("drier" if delta < -threshold else "stable")
    if variable in ("temperature_2m", "apparent_temperature"):
        return "warming" if delta > threshold else ("cooling" if delta < -threshold else "stable")
    return "increasing" if delta > threshold else ("decreasing" if delta < -threshold else "stable")


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/{city_id}/records", response_model=list[HourlyRecord])
async def historical_records(
    city_id: int,
    days: int = Query(default=7, ge=1, le=90, description="Number of past days to return"),
    limit: int = Query(default=168, ge=1, le=2160, description="Max rows returned"),
):
    """
    Return raw hourly weather records for a city over the past N days.

    Useful for researchers, dashboard charts, and climate analysis.
    Data sourced from Open-Meteo archive API (proxies GFS/ECMWF/IFS NWP data).
    """
    city = await get_city_by_id(city_id)
    if not city:
        raise HTTPException(status_code=404, detail=f"City {city_id} not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with get_async_session() as session:
        result = await session.execute(
            select(WeatherRecord)
            .where(WeatherRecord.city_id == city_id)
            .where(WeatherRecord.timestamp >= cutoff)
            .order_by(desc(WeatherRecord.timestamp))
            .limit(limit)
        )
        records = result.scalars().all()

    return [
        HourlyRecord(
            timestamp=r.timestamp,
            temperature_2m=r.temperature_2m,
            relative_humidity_2m=r.relative_humidity_2m,
            precipitation=r.precipitation,
            wind_speed_10m=r.wind_speed_10m,
            wind_gusts_10m=r.wind_gusts_10m,
            us_aqi=r.us_aqi,
            uv_index=r.uv_index,
            cloud_cover=r.cloud_cover,
            pressure_msl=r.pressure_msl,
            cape=r.cape,
        )
        for r in records
    ]


@router.get("/{city_id}/stats", response_model=HistoricalStats)
async def historical_stats(
    city_id: int,
    days: int = Query(default=30, ge=1, le=365, description="Analysis window in days"),
):
    """
    Compute aggregate climate statistics (mean, min, max, std, total) for a
    city over the past N days.

    Ideal for: climate analysts, agricultural planning, disaster preparedness
    briefings, and chatbot context about seasonal conditions.
    """
    city = await get_city_by_id(city_id)
    if not city:
        raise HTTPException(status_code=404, detail=f"City {city_id} not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with get_async_session() as session:
        result = await session.execute(
            select(WeatherRecord)
            .where(WeatherRecord.city_id == city_id)
            .where(WeatherRecord.timestamp >= cutoff)
            .order_by(WeatherRecord.timestamp)
        )
        records = result.scalars().all()

    if not records:
        raise HTTPException(
            status_code=503,
            detail=f"No historical data for city {city_id}. Run ingestion first."
        )

    return HistoricalStats(
        city_id=city_id,
        city_name=city.name,
        period_days=days,
        record_count=len(records),
        start=records[0].timestamp,
        end=records[-1].timestamp,
        temperature_2m=_safe_stats([r.temperature_2m for r in records]),
        precipitation=_safe_stats([r.precipitation for r in records]),
        wind_speed_10m=_safe_stats([r.wind_speed_10m for r in records]),
        relative_humidity_2m=_safe_stats([r.relative_humidity_2m for r in records]),
        us_aqi=_safe_stats([r.us_aqi for r in records]),
        uv_index=_safe_stats([r.uv_index for r in records]),
    )


@router.get("/{city_id}/trend", response_model=ClimateTrend)
async def climate_trend(
    city_id: int,
    variable: str = Query(
        default="temperature_2m",
        description="Variable to analyse: temperature_2m, precipitation, wind_speed_10m, us_aqi, relative_humidity_2m, uv_index",
    ),
    days: int = Query(default=30, ge=7, le=365, description="Analysis window in days"),
):
    """
    Compute daily means and anomalies for a single variable to identify
    climate trends (warming, cooling, wetter, drier, etc.).

    Supports: temperature_2m, precipitation, wind_speed_10m, us_aqi,
              relative_humidity_2m, uv_index
    """
    SUPPORTED = {
        "temperature_2m", "precipitation", "wind_speed_10m",
        "us_aqi", "relative_humidity_2m", "uv_index",
        "relative_humidity_2m", "pressure_msl", "cloud_cover",
    }
    if variable not in SUPPORTED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported variable '{variable}'. Choose from: {sorted(SUPPORTED)}"
        )

    city = await get_city_by_id(city_id)
    if not city:
        raise HTTPException(status_code=404, detail=f"City {city_id} not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with get_async_session() as session:
        result = await session.execute(
            select(WeatherRecord)
            .where(WeatherRecord.city_id == city_id)
            .where(WeatherRecord.timestamp >= cutoff)
            .order_by(WeatherRecord.timestamp)
        )
        records = result.scalars().all()

    if not records:
        raise HTTPException(status_code=503, detail="No data available for trend analysis.")

    # Group by calendar date
    daily: dict[str, list[float]] = {}
    for r in records:
        val = getattr(r, variable, None)
        if val is None:
            continue
        day_key = r.timestamp.strftime("%Y-%m-%d")
        daily.setdefault(day_key, []).append(val)

    daily_means = {k: statistics.mean(v) for k, v in sorted(daily.items())}
    all_vals = list(daily_means.values())
    period_mean = statistics.mean(all_vals) if all_vals else None

    points = [
        TrendPoint(
            date=date,
            value=round(mean, 3),
            anomaly=round(mean - period_mean, 3) if period_mean is not None else None,
        )
        for date, mean in daily_means.items()
    ]

    return ClimateTrend(
        city_id=city_id,
        city_name=city.name,
        variable=variable,
        period_days=days,
        mean=round(period_mean, 3) if period_mean is not None else None,
        trend_direction=_trend_direction(variable, all_vals),
        daily_points=points,
    )
