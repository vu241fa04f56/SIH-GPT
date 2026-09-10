"""
weather.py
──────────
Weather prediction routes.

GET /predict/weather/{city_id}  → latest weather + 1-hour forecast
GET /predict/weather/summary    → compact summary for all cities (map overlay)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.schemas.weather_schema import WeatherCitySummary, WeatherPredictionResponse
from backend.services.geo_service import all_cities, get_city_by_id, nearest_city, resolve_city
from backend.services.inference_service import WEATHER_OUTPUT_FIELDS
from backend.services.websocket_service import ws_manager
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import WeatherRecord
from sqlalchemy import select, desc

router = APIRouter()


@router.get("/summary/all", response_model=list[WeatherCitySummary])
async def weather_summary_all(request: Request):
    """
    Return compact weather snapshot for all cities (used for map marker rendering).
    """
    cities = await all_cities()
    summaries = []

    for city in cities:
        async with get_async_session() as session:
            result = await session.execute(
                select(WeatherRecord)
                .where(WeatherRecord.city_id == city.id)
                .order_by(desc(WeatherRecord.timestamp))
                .limit(1)
            )
            latest = result.scalar_one_or_none()

        summaries.append(WeatherCitySummary(
            city_id=city.id,
            city_name=city.name,
            latitude=city.latitude,
            longitude=city.longitude,
            temperature_2m=getattr(latest, "temperature_2m", None),
            precipitation=getattr(latest, "precipitation", None),
            wind_speed_10m=getattr(latest, "wind_speed_10m", None),
            uv_index=getattr(latest, "uv_index", None),
            wind_direction_10m=getattr(latest, "wind_direction_10m", 210.0),
            relative_humidity_2m=getattr(latest, "relative_humidity_2m", None),
            us_aqi=getattr(latest, "us_aqi", None),
            pm2_5=getattr(latest, "pm2_5", None),
            state=getattr(city, "state", "India"),
        ))

    return summaries


@router.get("/{city_identifier}", response_model=WeatherPredictionResponse)
async def predict_weather(city_identifier: str, request: Request):
    """
    Return current weather features + 1-hour model forecast for a city by name or ID.
    Also broadcasts the result to all WebSocket clients.
    """
    city = await resolve_city(city_identifier)
    if not city:
        raise HTTPException(status_code=404, detail=f"City '{city_identifier}' not found")
    city_id = city.id

    # Fetch latest raw record from DB
    async with get_async_session() as session:
        result = await session.execute(
            select(WeatherRecord)
            .where(WeatherRecord.city_id == city_id)
            .order_by(desc(WeatherRecord.timestamp))
            .limit(25)
        )
        history = result.scalars().all()
        latest = history[0] if history else None


    if latest is None:
        raise HTTPException(
            status_code=503,
            detail="No weather data for this city yet. Run ingestion first.",
        )

    # Build current features dict
    feature_fields = WEATHER_OUTPUT_FIELDS
    current_features = {f: getattr(latest, f, None) for f in feature_fields}

    # Run inference
    inference: object = request.app.state.inference
    forecast = inference.predict_weather(
        current_features,
        history=history,
        latitude=city.latitude,
        longitude=city.longitude,
        timestamp=latest.timestamp,
    )

    response = WeatherPredictionResponse(
        city_id=city_id,
        city_name=city.name,
        timestamp=latest.timestamp,
        current=current_features,
        forecast_1h=forecast,
        source="model" if inference.weather_model else "stub",
    )

    # Broadcast via WebSocket in background
    try:
        import asyncio
        asyncio.create_task(ws_manager.broadcast({
            "type": "weather_update",
            "city_id": city_id,
            "city_name": city.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature_2m": current_features.get("temperature_2m"),
            "precipitation": current_features.get("precipitation"),
        }))
    except Exception:
        pass

    return response

