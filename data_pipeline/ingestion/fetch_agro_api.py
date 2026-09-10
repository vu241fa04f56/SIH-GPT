"""
fetch_agro_api.py
─────────────────
Builds agro-advisory input rows by combining:
  1. Latest weather data from Open-Meteo (via archive endpoint)
  2. A static crop-calendar mapping for each city's primary crops
  3. Elevation (already stored on City record)

All weather variables are stored as individual typed columns on AgroRecord
(not buried in the ``features`` JSONB blob) so they are directly queryable.
The ``features`` JSONB blob is still populated for backwards compatibility.

Run standalone:
    python -m data_pipeline.ingestion.fetch_agro_api
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from loguru import logger
from sqlalchemy import select

from backend.core.config import settings
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import AgroRecord, City

# ─── Crop calendar ───────────────────────────────────────────────────────────
# Maps state name → list of crop dicts with season month ranges.
CROP_CALENDAR: dict[str, list[dict]] = {
    "default": [
        {"crop": "rice",   "seasons": {"kharif": [6, 7, 8, 9, 10], "rabi": []}},
        {"crop": "wheat",  "seasons": {"kharif": [],                "rabi": [10, 11, 12, 1, 2, 3]}},
        {"crop": "maize",  "seasons": {"kharif": [6, 7, 8],         "rabi": [10, 11, 12]}},
    ],
    "Punjab": [
        {"crop": "wheat",  "seasons": {"kharif": [],    "rabi": [10, 11, 12, 1, 2]}},
        {"crop": "rice",   "seasons": {"kharif": [6, 7, 8], "rabi": []}},
    ],
    "Haryana": [
        {"crop": "wheat",  "seasons": {"kharif": [],    "rabi": [10, 11, 12, 1, 2]}},
        {"crop": "rice",   "seasons": {"kharif": [6, 7, 8], "rabi": []}},
    ],
    "Maharashtra": [
        {"crop": "sugarcane", "seasons": {"kharif": [1,2,3,4,5,6,7,8,9,10,11,12], "rabi": []}},
        {"crop": "cotton",    "seasons": {"kharif": [5, 6, 7, 8], "rabi": []}},
        {"crop": "soybean",   "seasons": {"kharif": [6, 7, 8],    "rabi": []}},
    ],
    "Gujarat": [
        {"crop": "cotton",    "seasons": {"kharif": [5, 6, 7, 8], "rabi": []}},
        {"crop": "wheat",     "seasons": {"kharif": [],            "rabi": [10, 11, 12, 1]}},
        {"crop": "groundnut", "seasons": {"kharif": [6, 7, 8],    "rabi": []}},
    ],
    "Rajasthan": [
        {"crop": "wheat",    "seasons": {"kharif": [],     "rabi": [10, 11, 12, 1, 2]}},
        {"crop": "mustard",  "seasons": {"kharif": [],     "rabi": [10, 11, 12, 1, 2]}},
        {"crop": "bajra",    "seasons": {"kharif": [6, 7, 8, 9], "rabi": []}},
    ],
    "Andhra Pradesh": [
        {"crop": "rice",     "seasons": {"kharif": [6, 7, 8, 9], "rabi": [11, 12, 1, 2]}},
        {"crop": "cotton",   "seasons": {"kharif": [5, 6, 7],    "rabi": []}},
        {"crop": "chilli",   "seasons": {"kharif": [6, 7],       "rabi": [10, 11]}},
    ],
    "Telangana": [
        {"crop": "rice",     "seasons": {"kharif": [6, 7, 8, 9], "rabi": [11, 12, 1]}},
        {"crop": "cotton",   "seasons": {"kharif": [5, 6, 7],    "rabi": []}},
    ],
    "Kerala": [
        {"crop": "rice",     "seasons": {"kharif": [6, 7, 8], "rabi": [11, 12, 1]}},
        {"crop": "coconut",  "seasons": {"kharif": list(range(1, 13)), "rabi": []}},
        {"crop": "rubber",   "seasons": {"kharif": list(range(1, 13)), "rabi": []}},
    ],
    "Tamil Nadu": [
        {"crop": "rice",      "seasons": {"kharif": [6, 7, 8], "rabi": [11, 12, 1, 2]}},
        {"crop": "sugarcane", "seasons": {"kharif": list(range(1, 13)), "rabi": []}},
        {"crop": "groundnut", "seasons": {"kharif": [5, 6, 7], "rabi": [10, 11, 12]}},
    ],
    "Karnataka": [
        {"crop": "rice",     "seasons": {"kharif": [6, 7, 8, 9], "rabi": []}},
        {"crop": "ragi",     "seasons": {"kharif": [6, 7, 8],    "rabi": [10, 11]}},
        {"crop": "coffee",   "seasons": {"kharif": list(range(1, 13)), "rabi": []}},
    ],
    "Madhya Pradesh": [
        {"crop": "wheat",    "seasons": {"kharif": [],     "rabi": [10, 11, 12, 1, 2, 3]}},
        {"crop": "soybean",  "seasons": {"kharif": [6, 7, 8], "rabi": []}},
        {"crop": "gram",     "seasons": {"kharif": [],     "rabi": [10, 11, 12, 1]}},
    ],
    "Uttar Pradesh": [
        {"crop": "wheat",    "seasons": {"kharif": [],     "rabi": [10, 11, 12, 1, 2, 3]}},
        {"crop": "rice",     "seasons": {"kharif": [6, 7, 8, 9], "rabi": []}},
        {"crop": "sugarcane","seasons": {"kharif": list(range(1, 13)), "rabi": []}},
    ],
    "West Bengal": [
        {"crop": "rice",     "seasons": {"kharif": [6, 7, 8, 9, 10], "rabi": [11, 12, 1]}},
        {"crop": "jute",     "seasons": {"kharif": [3, 4, 5, 6, 7],  "rabi": []}},
        {"crop": "tea",      "seasons": {"kharif": list(range(1, 13)), "rabi": []}},
    ],
    "Odisha": [
        {"crop": "rice",     "seasons": {"kharif": [6, 7, 8, 9, 10], "rabi": [11, 12, 1]}},
    ],
    "Bihar": [
        {"crop": "wheat",    "seasons": {"kharif": [],     "rabi": [10, 11, 12, 1, 2, 3]}},
        {"crop": "rice",     "seasons": {"kharif": [6, 7, 8, 9], "rabi": []}},
        {"crop": "maize",    "seasons": {"kharif": [6, 7], "rabi": [10, 11]}},
    ],
    "Assam": [
        {"crop": "rice",     "seasons": {"kharif": [5, 6, 7, 8, 9, 10], "rabi": [11, 12, 1]}},
        {"crop": "tea",      "seasons": {"kharif": list(range(1, 13)), "rabi": []}},
    ],
}

# ─── Weather variables fetched from Open-Meteo archive ───────────────────────
AGRO_WEATHER_VARS = [
    "temperature_2m", "relative_humidity_2m", "precipitation",
    "et0_fao_evapotranspiration", "wind_speed_10m", "cloud_cover",
    "uv_index", "shortwave_radiation",
]

# Crops treated as perennial / year-round
PERENNIAL_CROPS = {"sugarcane", "coconut", "rubber", "coffee", "tea"}


def _get_season(crop: str, month: int, crop_info: dict) -> str:
    """Determine the active season label for a crop in a given month."""
    if crop in PERENNIAL_CROPS:
        return "perennial"
    kharif_months = crop_info["seasons"].get("kharif", [])
    rabi_months   = crop_info["seasons"].get("rabi", [])
    if month in kharif_months:
        return "kharif"
    if month in rabi_months:
        return "rabi"
    return "off_season"


def _current_growth_stage(crop: str, month: int) -> str:
    """Estimate crop growth stage from current month. Simplified lookup."""
    stage_map: dict[str, dict[int, str]] = {
        "rice":    {6: "sowing", 7: "vegetative", 8: "vegetative", 9: "flowering",
                    10: "maturity", 11: "harvest"},
        "wheat":   {10: "sowing", 11: "germination", 12: "tillering",
                    1: "jointing", 2: "heading", 3: "maturity", 4: "harvest"},
        "maize":   {6: "sowing", 7: "vegetative", 8: "tasseling", 9: "maturity", 10: "harvest"},
        "cotton":  {5: "sowing", 6: "vegetative", 7: "flowering", 8: "boll_development",
                    9: "maturity", 10: "harvest"},
        "soybean": {6: "sowing", 7: "vegetative", 8: "flowering", 9: "pod_filling",
                    10: "harvest"},
        "sugarcane": {m: "growing" for m in range(1, 13)},
        "coconut":   {m: "growing" for m in range(1, 13)},
        "default":   {m: "growing" for m in range(1, 13)},
    }
    stages = stage_map.get(crop, stage_map["default"])
    return stages.get(month, "dormant")


async def _fetch_weather_for_agro(
    client: httpx.AsyncClient,
    city: City,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Fetch weather features relevant to agro advisory from Open-Meteo archive."""
    params = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(AGRO_WEATHER_VARS),
        "timezone": "Asia/Kolkata",
    }
    resp = await client.get(settings.OPEN_METEO_ARCHIVE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    rows = []
    for i, t in enumerate(times):
        row = {"timestamp": datetime.fromisoformat(t)}
        for var in AGRO_WEATHER_VARS:
            vals = hourly.get(var, [])
            row[var] = vals[i] if i < len(vals) else None
        rows.append(row)
    return rows


async def ingest_agro_for_city(city: City, days_back: int = 1) -> int:
    """Build and store agro-advisory rows for one city.

    Each fetched weather row is expanded per active crop; all API variables
    are stored as individual typed columns on AgroRecord as well as in the
    legacy ``features`` JSONB blob.

    Returns number of new rows inserted.
    """
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days_back)

    async with httpx.AsyncClient() as client:
        wx_rows = await _fetch_weather_for_agro(client, city, str(start), str(end))

    crops = CROP_CALENDAR.get(city.state, CROP_CALENDAR["default"])
    inserted = 0

    async with get_async_session() as session:
        for wx in wx_rows:
            month = wx["timestamp"].month
            for crop_info in crops:
                crop = crop_info["crop"]

                # Check if crop is in active season (or perennial)
                in_kharif = month in crop_info["seasons"].get("kharif", [])
                in_rabi   = month in crop_info["seasons"].get("rabi", [])
                if not (in_kharif or in_rabi or crop in PERENNIAL_CROPS):
                    continue

                season = _get_season(crop, month, crop_info)
                growth_stage = _current_growth_stage(crop, month)

                # Build the JSONB features blob (backwards compat)
                features = {
                    **{k: wx.get(k) for k in AGRO_WEATHER_VARS},
                    "elevation_m": city.elevation_m,
                    "month": month,
                    "crop": crop,
                    "season": season,
                    "growth_stage": growth_stage,
                }

                session.add(AgroRecord(
                    city_id=city.id,
                    timestamp=wx["timestamp"],
                    crop_type=crop,
                    growth_stage=growth_stage,
                    # ── Individual typed columns (queryable) ────────────────
                    month=month,
                    season=season,
                    temperature_2m=wx.get("temperature_2m"),
                    relative_humidity_2m=wx.get("relative_humidity_2m"),
                    precipitation=wx.get("precipitation"),
                    et0_fao_evapotranspiration=wx.get("et0_fao_evapotranspiration"),
                    wind_speed_10m=wx.get("wind_speed_10m"),
                    cloud_cover=wx.get("cloud_cover"),
                    uv_index=wx.get("uv_index"),
                    shortwave_radiation=wx.get("shortwave_radiation"),
                    elevation_m=city.elevation_m,
                    # ── Legacy JSONB blob ───────────────────────────────────
                    features=features,
                ))
                inserted += 1

    logger.info(f"[agro] {city.name}: {inserted} agro rows inserted")
    return inserted


async def ingest_all_cities(days_back: int = 1, concurrency: int = 10) -> None:
    """Run agro ingestion for all cities."""
    async with get_async_session() as session:
        result = await session.execute(select(City))
        cities = result.scalars().all()

    sem = asyncio.Semaphore(concurrency)

    async def _bounded(city: City) -> None:
        async with sem:
            try:
                await ingest_agro_for_city(city, days_back)
            except Exception as exc:
                logger.error(f"Agro ingest failed for {city.name}: {exc}")

    await asyncio.gather(*[_bounded(c) for c in cities])
    logger.success(f"Agro ingestion complete — {len(cities)} cities processed")


if __name__ == "__main__":
    asyncio.run(ingest_all_cities())
