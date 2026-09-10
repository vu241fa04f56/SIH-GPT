"""
disaster.py
───────────
Disaster prediction routes.

GET /predict/disaster/{city_id}  → 3-hour-ahead risk prediction
GET /predict/disaster/overlay    → all cities risk map for frontend overlay
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import desc, select

from backend.schemas.disaster_schema import DisasterMapOverlay, DisasterPredictionResponse
from backend.services.alert_service import broadcast_disaster_alert
from backend.services.geo_service import all_cities, get_city_by_id, resolve_city, subscriptions_in_risk_zone
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import DisasterRecord, WeatherRecord

router = APIRouter()

RISK_ALERT_THRESHOLD = 0.6  # risk_score above this triggers FCM alerts

ACTION_MAP = {
    "air_pollution": "Limit outdoor activity and use a well-fitting mask if air quality is poor.",
    "cold_wave": "Stay warm, avoid prolonged exposure, and check on vulnerable people.",
    "cyclone": "Move to higher ground. Stay indoors. Avoid coastal areas.",
    "drought": "Conserve water and follow local irrigation and crop advisories.",
    "extreme_temperature": "Avoid peak exposure, hydrate, and follow local health advisories.",
    "flood": "Move to elevated areas. Avoid flooded roads. Follow IMD guidance.",
    "heat_wave": "Hydrate frequently and avoid direct sun during the hottest hours.",
    "heavy_rain": "Avoid low-lying areas. Do not drive in flooded streets.",
    "heavy_rainfall": "Avoid low-lying areas. Do not drive in flooded streets.",
    "high_pressure": "Monitor official forecasts for rapid weather changes.",
    "lightning": "Stay indoors. Avoid open fields and tall trees.",
    "earthquake": "Drop, cover, hold on. Move away from buildings after shaking stops.",
    "landslide": "Evacuate slopes immediately. Move to flat ground.",
    "low_pressure": "Monitor IMD bulletins; prepare for heavy rain and strong winds.",
    "storm_surge": "Leave beaches and low coastal areas; move inland or to higher ground.",
    "strong_winds": "Secure loose objects and avoid travel during peak gusts.",
    "thunderstorm": "Stay indoors and away from windows, open fields, and tall trees.",
    "tsunami": "Move inland and to high ground immediately; follow official evacuation routes.",
    "typhoon": "Evacuate if advised. Secure loose objects. Stay away from windows.",
    "volcano": "Follow official evacuation orders and protect yourself from ash exposure.",
    "severe_wind": "Secure outdoor items. Avoid travel during peak gusts.",
    "none": "No significant disaster risk currently detected.",
}


@router.get("/overlay", response_model=DisasterMapOverlay)
@router.get("/overlay/all", response_model=DisasterMapOverlay)
async def disaster_overlay_all(request: Request):
    """Return disaster risk for all cities (used by the frontend map overlay)."""
    cities = await all_cities()
    inference = request.app.state.inference
    city_data = []

    for city in cities:
        async with get_async_session() as session:
            result = await session.execute(
                select(WeatherRecord)
                .where(WeatherRecord.city_id == city.id)
                .order_by(desc(WeatherRecord.timestamp))
                .limit(48)
            )
            history = result.scalars().all()
            latest_wx = history[0] if history else None

        features = {}
        if latest_wx:
            for col in ["temperature_2m", "relative_humidity_2m", "precipitation", "rain",
                        "wind_speed_10m", "wind_gusts_10m", "surface_pressure", "pressure_msl",
                        "weather_code", "us_aqi", "pm2_5"]:
                features[col] = getattr(latest_wx, col, 0.0) or 0.0

        pred = inference.predict_disaster(features, history=history, elevation=city.elevation_m or 0.0)
        city_data.append({
            "city_id": city.id,
            "city_name": city.name,
            "lat": city.latitude,
            "lon": city.longitude,
            "disaster_type": pred.get("disaster_type", "none"),
            "risk_score": pred.get("risk_score", 0.0),
        })

    return DisasterMapOverlay(cities=city_data, generated_at=datetime.now(timezone.utc))


@router.get("/{city_identifier}", response_model=DisasterPredictionResponse)
async def predict_disaster(city_identifier: str, request: Request):
    """
    Return 3-hour-ahead disaster risk prediction for a city by name or ID.
    Triggers FCM alerts if risk_score > threshold.
    """
    city = await resolve_city(city_identifier)
    if not city:
        raise HTTPException(status_code=404, detail=f"City '{city_identifier}' not found")
    city_id = city.id


    # Get latest weather for feature input
    async with get_async_session() as session:
        result = await session.execute(
            select(WeatherRecord)
            .where(WeatherRecord.city_id == city_id)
            .order_by(desc(WeatherRecord.timestamp))
            .limit(48)
        )
        history = result.scalars().all()
        latest_wx = history[0] if history else None

    features = {}
    if latest_wx:
        for col in ["temperature_2m", "relative_humidity_2m", "precipitation", "rain",
                    "wind_speed_10m", "wind_gusts_10m", "surface_pressure", "pressure_msl",
                    "weather_code", "us_aqi", "pm2_5"]:
            features[col] = getattr(latest_wx, col, 0.0) or 0.0

    # Run inference
    inference = request.app.state.inference
    result_dict = inference.predict_disaster(features, history=history, elevation=city.elevation_m or 0.0)

    disaster_type = result_dict.get("disaster_type", "none")
    risk_score = result_dict.get("risk_score", 0.0)
    is_active = risk_score > RISK_ALERT_THRESHOLD

    # Trigger FCM alerts if high risk
    if is_active and disaster_type != "none":
        subs = await subscriptions_in_risk_zone(city.latitude, city.longitude, radius_km=100)
        if subs:
            await broadcast_disaster_alert(
                subscriptions=subs,
                city_name=city.name,
                disaster_type=disaster_type,
                severity="high" if risk_score > 0.8 else "medium",
                risk_score=risk_score,
            )

    return DisasterPredictionResponse(
        city_id=city_id,
        city_name=city.name,
        timestamp=datetime.now(timezone.utc),
        disaster_type=disaster_type,
        severity="high" if risk_score > 0.8 else "medium" if risk_score > 0.6 else "low",
        risk_score=risk_score,
        lead_hours=3.0,
        recommended_action=ACTION_MAP.get(disaster_type, ACTION_MAP["none"]),
        is_active=is_active,
    )

