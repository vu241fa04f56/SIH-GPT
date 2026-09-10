"""
fetch_weather_api.py
────────────────────
Ingests weather data from Open-Meteo APIs for all cities.

Sources:
  - archive-api.open-meteo.com  → hourly historical weather (29 variables)
  - air-quality-api.open-meteo.com → 9 AQI variables (PM10, PM2.5, NH3, etc.)
  - marine-api.open-meteo.com    → wave height + SST for coastal cities
  - api.open-meteo.com/v1/elevation → one-time elevation fetch

Run standalone:
    python -m data_pipeline.ingestion.fetch_weather_api
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from loguru import logger
from sqlalchemy import select

from backend.core.config import settings
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import City, WeatherRecord

# ─── Variable lists ──────────────────────────────────────────────────────────

ARCHIVE_HOURLY_VARS = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature",
    "precipitation", "rain", "snowfall", "snow_depth",
    "weather_code", "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
    "surface_pressure", "pressure_msl", "vapour_pressure_deficit",
    "wind_speed_10m", "wind_speed_100m", "wind_direction_10m", "wind_direction_100m",
    "wind_gusts_10m", "et0_fao_evapotranspiration", "cape", "lifted_index",
    "shortwave_radiation", "direct_radiation", "diffuse_radiation",
    "direct_normal_irradiance", "soil_temperature_0_to_7cm", "soil_moisture_0_to_7cm",
    "uv_index", "uv_index_clear_sky",
]

AIR_QUALITY_HOURLY_VARS = [
    "us_aqi", "pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide",
    "sulphur_dioxide", "ozone", "ammonia", "dust", "alder_pollen",
]

MARINE_HOURLY_VARS = ["wave_height", "sea_surface_temperature"]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _date_range(days_back: int = 1) -> tuple[str, str]:
    """Return (start_date, end_date) strings for the last N days (UTC)."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days_back)
    return str(start), str(end)


async def _fetch_archive(
    client: httpx.AsyncClient,
    city: City,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Fetch hourly archive weather for one city. Returns list of row dicts."""
    params = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(ARCHIVE_HOURLY_VARS),
        "timezone": "Asia/Kolkata",
    }
    resp = await client.get(settings.OPEN_METEO_ARCHIVE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    rows = []
    for i, t in enumerate(times):
        row = {"city_id": city.id, "timestamp": datetime.fromisoformat(t)}
        for var in ARCHIVE_HOURLY_VARS:
            vals = hourly.get(var, [])
            row[var] = vals[i] if i < len(vals) else None
        rows.append(row)
    return rows


async def _fetch_air_quality(
    client: httpx.AsyncClient,
    city: City,
    start_date: str,
    end_date: str,
) -> dict[str, list]:
    """Returns {var_name: [hourly_values]} for air quality variables."""
    params = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(AIR_QUALITY_HOURLY_VARS),
        "timezone": "Asia/Kolkata",
    }
    resp = await client.get(settings.OPEN_METEO_AIR_QUALITY_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("hourly", {})


async def _fetch_marine(
    client: httpx.AsyncClient,
    city: City,
    start_date: str,
    end_date: str,
) -> dict[str, list]:
    """Fetch marine variables — only for coastal cities."""
    params = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(MARINE_HOURLY_VARS),
        "timezone": "Asia/Kolkata",
    }
    try:
        resp = await client.get(settings.OPEN_METEO_MARINE_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("hourly", {})
    except Exception as exc:
        logger.warning(f"Marine fetch failed for {city.name}: {exc}")
        return {}


# ─── Main ingestion function ─────────────────────────────────────────────────

async def ingest_weather_for_city(city: City, days_back: int = 1) -> int:
    """
    Fetch + store weather rows for a single city.

    Returns the number of new rows inserted.
    """
    start_date, end_date = _date_range(days_back)
    inserted = 0

    async with httpx.AsyncClient() as client:
        # Parallel fetch of archive + air-quality (+ marine if coastal)
        tasks = [
            _fetch_archive(client, city, start_date, end_date),
            _fetch_air_quality(client, city, start_date, end_date),
        ]
        if city.is_coastal:
            tasks.append(_fetch_marine(client, city, start_date, end_date))

        results = await asyncio.gather(*tasks, return_exceptions=True)

    archive_rows: list[dict] = results[0] if not isinstance(results[0], Exception) else []
    aq_data: dict = results[1] if not isinstance(results[1], Exception) else {}
    marine_data: dict = results[2] if (len(results) > 2 and not isinstance(results[2], Exception)) else {}

    # Merge air-quality and marine into archive rows by index
    async with get_async_session() as session:
        for i, row in enumerate(archive_rows):
            # Check for duplicates
            existing = await session.execute(
                select(WeatherRecord.id)
                .where(WeatherRecord.city_id == city.id)
                .where(WeatherRecord.timestamp == row["timestamp"])
                .limit(1)
            )
            if existing.scalar():
                continue

            # Merge AQ
            for var in AIR_QUALITY_HOURLY_VARS:
                vals = aq_data.get(var, [])
                row[var] = vals[i] if i < len(vals) else None

            # Merge marine
            for var in MARINE_HOURLY_VARS:
                vals = marine_data.get(var, [])
                row[var] = vals[i] if i < len(vals) else None

            session.add(WeatherRecord(**row))
            inserted += 1

    logger.info(f"[weather] {city.name}: inserted {inserted} new rows")
    return inserted


async def ingest_all_cities(days_back: int = 1, concurrency: int = 10) -> None:
    """
    Ingest weather data for all cities in the DB.

    Uses a semaphore to limit concurrent Open-Meteo calls.
    """
    async with get_async_session() as session:
        result = await session.execute(select(City))
        cities = result.scalars().all()

    if not cities:
        logger.warning("No cities found in DB. Run seed_database.py first.")
        return

    sem = asyncio.Semaphore(concurrency)

    async def _bounded(city: City) -> None:
        async with sem:
            try:
                await ingest_weather_for_city(city, days_back)
            except Exception as exc:
                logger.error(f"Failed for {city.name}: {exc}")

    await asyncio.gather(*[_bounded(c) for c in cities])
    logger.success(f"Weather ingestion complete — {len(cities)} cities processed")


if __name__ == "__main__":
    asyncio.run(ingest_all_cities())
