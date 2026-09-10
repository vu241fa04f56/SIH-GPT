"""
advisory.py — Agro advisory routes.

GET /advisory/{city_id}?crop={crop_type}
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc, select

from backend.services.geo_service import get_city_by_id
from data_pipeline.preprocessing.preprocess_agro import CROP_MAP, GROWTH_STAGE_MAP
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import AgroRecord, WeatherRecord

router = APIRouter()


class AdvisoryResponse(BaseModel):
    city_id: int
    city_name: str
    crop_type: str
    growth_stage: str
    advisory_label: str
    advisory_text: str
    predictions: dict[str, str]
    timestamp: datetime


@router.get("/{city_id:int}", response_model=AdvisoryResponse)
async def get_advisory(
    city_id: int,
    request: Request,
    crop: str = Query(default="rice", description="Crop type"),
):
    """Return agro advisory for a city and crop type."""
    city = await get_city_by_id(city_id)
    if not city:
        raise HTTPException(status_code=404, detail=f"City {city_id} not found")

    # Get latest weather as feature input
    async with get_async_session() as session:
        result = await session.execute(
            select(WeatherRecord)
            .where(WeatherRecord.city_id == city_id)
            .order_by(desc(WeatherRecord.timestamp))
            .limit(336)
        )
        history = result.scalars().all()
        latest_wx = history[0] if history else None

    month = datetime.now(timezone.utc).month
    crop_stages = {
        "rice": {6: "Transplanting", 7: "Tillering", 8: "Vegetative", 9: "Flowering", 10: "Grain_Filling", 11: "Maturity"},
        "wheat": {11: "Vegetative", 12: "Tillering", 1: "Flowering", 2: "Grain_Filling", 3: "Maturity"},
        "maize": {6: "Vegetative", 7: "Tasseling", 8: "Silking", 9: "Grain_Filling", 10: "Maturity"},
    }
    growth_stage = crop_stages.get(crop.lower(), {}).get(month, "Vegetative")
    season = "KHARIF" if 5 <= month <= 10 else "RABI"

    features = {
        "crop_type": crop,
        "growth_stage": growth_stage,
        "agro_season": season,
        "timestamp": datetime.now(timezone.utc),
        "latitude": city.latitude,
        "longitude": city.longitude,
    }
    if latest_wx:
        for col in ["temperature_2m", "relative_humidity_2m", "precipitation",
                    "et0_fao_evapotranspiration", "wind_speed_10m", "cloud_cover",
                    "uv_index", "shortwave_radiation"]:
            features[col] = getattr(latest_wx, col, 0.0) or 0.0
    features["elevation_m"] = city.elevation_m or 0.0

    inference = request.app.state.inference
    result_dict = inference.predict_advisory(features, history=history)

    return AdvisoryResponse(
        city_id=city_id,
        city_name=city.name,
        crop_type=crop,
        growth_stage=growth_stage,
        advisory_label=result_dict["advisory_label"],
        advisory_text=result_dict["advisory_text"],
        predictions=result_dict.get("predictions", {}),
        timestamp=datetime.now(timezone.utc),
    )
