"""
geo_service.py
──────────────
Geospatial utilities for WeatherGPT.

Services:
  - City lookup by name or (lat, lon)
  - PostGIS point-in-polygon check (is a user inside a disaster risk zone?)
  - Nearest city to a given coordinate
"""

from __future__ import annotations

import math

from loguru import logger
from sqlalchemy import func, select, text

from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import AlertSubscription, City


async def get_city_by_name(name: str) -> City | None:
    """Case-insensitive city name lookup."""
    async with get_async_session() as session:
        result = await session.execute(
            select(City).where(func.lower(City.name) == name.lower()).limit(1)
        )
        return result.scalar_one_or_none()


async def get_city_by_id(city_id: int) -> City | None:
    async with get_async_session() as session:
        result = await session.execute(select(City).where(City.id == city_id))
        return result.scalar_one_or_none()


async def nearest_city(lat: float, lon: float) -> City | None:
    """
    Return the nearest city to a given (lat, lon) using PostGIS ST_Distance.
    Falls back to Haversine computation if PostGIS is unavailable.
    """
    async with get_async_session() as session:
        try:
            point = f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)"
            result = await session.execute(
                select(City)
                .order_by(text(f"cities.geom <-> {point}"))
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as exc:
            logger.warning(f"PostGIS nearest query failed ({exc}). Falling back to Haversine.")
            return await _nearest_haversine(session, lat, lon)


async def _nearest_haversine(session, lat: float, lon: float) -> City | None:
    """Haversine fallback when PostGIS is not available."""
    result = await session.execute(select(City))
    cities = result.scalars().all()
    if not cities:
        return None
    return min(cities, key=lambda c: _haversine(lat, lon, c.latitude, c.longitude))


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in km between two WGS-84 points."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def subscriptions_in_risk_zone(
    center_lat: float,
    center_lon: float,
    radius_km: float = 100.0,
) -> list[AlertSubscription]:
    """
    Return all device subscriptions whose location falls within radius_km
    of the given disaster epicentre, using PostGIS ST_DWithin.
    """
    radius_deg = radius_km / 111.0  # rough degree conversion
    async with get_async_session() as session:
        point = f"ST_SetSRID(ST_MakePoint({center_lon}, {center_lat}), 4326)"
        result = await session.execute(
            select(AlertSubscription).where(
                text(f"ST_DWithin(alert_subscriptions.geom, {point}, {radius_deg})")
            )
        )
        return result.scalars().all()


async def all_cities() -> list[City]:
    """Return all cities (used by the data pipeline to iterate over)."""
    async with get_async_session() as session:
        result = await session.execute(select(City).order_by(City.id))
        return result.scalars().all()
