"""
fetch_disaster_api.py
─────────────────────
Derives disaster-risk rows from Open-Meteo extreme-weather variables.

Strategy:
  Open-Meteo does not provide a disaster event feed directly.
  We pull extreme-weather variables (CAPE, wind gusts, precipitation,
  lifted_index) for each city and apply rule-based thresholds to label
  each hourly slot with a disaster type + severity.

  All extreme-weather variables are stored as individual typed columns on
  DisasterRecord (not only in the ``raw_features`` JSONB blob) so they are
  directly queryable via SQL.

  When you have the 600K-row historical disaster CSV, run:
      python scripts/seed_database.py
  to load it directly into the disaster_records table instead.

Run standalone:
    python -m data_pipeline.ingestion.fetch_disaster_api
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from loguru import logger
from sqlalchemy import select

from backend.core.config import settings
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import City, DisasterRecord

# ─── Extreme-weather variable list ───────────────────────────────────────────

EXTREME_VARS = [
    "cape",               # Convective Available Potential Energy (J/kg)
    "wind_gusts_10m",     # km/h
    "precipitation",      # mm/hr
    "lifted_index",       # K — negative = instability = storm risk
    "pressure_msl",       # hPa — low pressure = cyclone
    "rain",               # mm/hr
    "snowfall",           # cm/hr
]


# ─── Threshold rules ─────────────────────────────────────────────────────────

def _classify_disaster(row: dict) -> tuple[str | None, str | None, float]:
    """
    Apply meteorological thresholds to produce (disaster_type, severity, risk_score).
    Returns (None, None, 0.0) if no disaster risk detected.

    Thresholds are conservative starting points — calibrate against the
    historical disaster dataset after seeding.
    """
    cape     = row.get("cape")     or 0
    gusts    = row.get("wind_gusts_10m") or 0
    precip   = row.get("precipitation") or 0
    li       = row.get("lifted_index") or 0
    pressure = row.get("pressure_msl") or 1013

    # ── Cyclone ──────────────────────────────────────────────────────────────
    if gusts > 118 and pressure < 980:
        severity = "extreme" if gusts > 200 else "high"
        return "cyclone", severity, min(gusts / 200, 1.0)

    # ── Severe Thunderstorm / Lightning ───────────────────────────────────────
    if cape > 2500 and li < -4:
        severity = "high" if cape > 4000 else "medium"
        return "lightning", severity, min(cape / 4000, 1.0)

    # ── Heavy Rain / Flood ────────────────────────────────────────────────────
    if precip > 64:    # IMD heavy rain threshold
        severity = "extreme" if precip > 204 else "high" if precip > 115 else "medium"
        return "heavy_rain", severity, min(precip / 204, 1.0)

    if precip > 20:
        return "flood", "medium", min(precip / 115, 1.0)

    # ── Strong Winds ─────────────────────────────────────────────────────────
    if gusts > 60:
        severity = "high" if gusts > 90 else "medium"
        return "severe_wind", severity, min(gusts / 118, 1.0)

    return None, None, 0.0


# ─── Ingestion ────────────────────────────────────────────────────────────────

async def _fetch_extreme_vars(
    client: httpx.AsyncClient,
    city: City,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Fetch all extreme-weather hourly variables from Open-Meteo archive."""
    params = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(EXTREME_VARS),
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
        for var in EXTREME_VARS:
            vals = hourly.get(var, [])
            row[var] = vals[i] if i < len(vals) else None
        rows.append(row)
    return rows


async def ingest_disaster_for_city(city: City, days_back: int = 1) -> int:
    """
    Derive disaster-risk rows for a single city.

    Each raw API row that exceeds a meteorological threshold is stored as a
    DisasterRecord with all extreme-weather variables in individual typed
    columns (queryable) AND in the legacy ``raw_features`` JSONB blob.

    Returns count of inserted rows.
    """
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days_back)

    async with httpx.AsyncClient() as client:
        raw_rows = await _fetch_extreme_vars(client, city, str(start), str(end))

    inserted = 0
    async with get_async_session() as session:
        for row in raw_rows:
            disaster_type, severity, risk_score = _classify_disaster(row)
            if not disaster_type:
                continue

            # Dedup check
            existing = await session.execute(
                select(DisasterRecord.id)
                .where(DisasterRecord.city_id == city.id)
                .where(DisasterRecord.timestamp == row["timestamp"])
                .where(DisasterRecord.disaster_type == disaster_type)
                .limit(1)
            )
            if existing.scalar():
                continue

            session.add(DisasterRecord(
                city_id=city.id,
                timestamp=row["timestamp"],
                disaster_type=disaster_type,
                severity=severity,
                risk_score=risk_score,
                is_predicted=True,
                lead_hours=3.0,
                # ── Individual typed columns (queryable) ────────────────────
                cape=row.get("cape"),
                wind_gusts_10m=row.get("wind_gusts_10m"),
                precipitation=row.get("precipitation"),
                lifted_index=row.get("lifted_index"),
                pressure_msl=row.get("pressure_msl"),
                rain=row.get("rain"),
                snowfall=row.get("snowfall"),
                # ── Legacy JSONB blob ───────────────────────────────────────
                raw_features=row,
                source="open_meteo_derived",
            ))
            inserted += 1

    logger.info(f"[disaster] {city.name}: {inserted} risk rows inserted")
    return inserted


async def ingest_all_cities(days_back: int = 1, concurrency: int = 10) -> None:
    """Run disaster ingestion for all cities."""
    async with get_async_session() as session:
        result = await session.execute(select(City))
        cities = result.scalars().all()

    sem = asyncio.Semaphore(concurrency)

    async def _bounded(city: City) -> None:
        async with sem:
            try:
                await ingest_disaster_for_city(city, days_back)
            except Exception as exc:
                logger.error(f"Disaster ingest failed for {city.name}: {exc}")

    await asyncio.gather(*[_bounded(c) for c in cities])
    logger.success(f"Disaster ingestion complete — {len(cities)} cities processed")


if __name__ == "__main__":
    asyncio.run(ingest_all_cities())
