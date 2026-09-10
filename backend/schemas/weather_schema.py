"""
Pydantic v2 schemas for weather prediction requests and responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WeatherFeatures(BaseModel):
    """Complete weather, air-quality and marine payload."""

    temperature_2m: Optional[float] = None
    relative_humidity_2m: Optional[float] = None
    dew_point_2m: Optional[float] = None
    apparent_temperature: Optional[float] = None
    precipitation: Optional[float] = None
    rain: Optional[float] = None
    snowfall: Optional[float] = None
    snow_depth: Optional[float] = None
    weather_code: Optional[int] = None
    cloud_cover: Optional[float] = None
    cloud_cover_low: Optional[float] = None
    cloud_cover_mid: Optional[float] = None
    cloud_cover_high: Optional[float] = None
    surface_pressure: Optional[float] = None
    pressure_msl: Optional[float] = None
    vapour_pressure_deficit: Optional[float] = None
    wind_speed_10m: Optional[float] = None
    wind_speed_100m: Optional[float] = None
    wind_direction_10m: Optional[float] = None
    wind_direction_100m: Optional[float] = None
    wind_gusts_10m: Optional[float] = None
    et0_fao_evapotranspiration: Optional[float] = None
    cape: Optional[float] = None
    lifted_index: Optional[float] = None
    shortwave_radiation: Optional[float] = None
    direct_radiation: Optional[float] = None
    direct_normal_irradiance: Optional[float] = None
    diffuse_radiation: Optional[float] = None
    uv_index: Optional[float] = None
    uv_index_clear_sky: Optional[float] = None
    soil_temperature_0_to_7cm: Optional[float] = None
    soil_moisture_0_to_7cm: Optional[float] = None
    us_aqi: Optional[float] = None
    pm10: Optional[float] = None
    pm2_5: Optional[float] = None
    carbon_monoxide: Optional[float] = None
    nitrogen_dioxide: Optional[float] = None
    sulphur_dioxide: Optional[float] = None
    ozone: Optional[float] = None
    ammonia: Optional[float] = None
    dust: Optional[float] = None
    alder_pollen: Optional[float] = None
    wave_height: Optional[float] = None
    sea_surface_temperature: Optional[float] = None


class WeatherPredictionResponse(BaseModel):
    city_id: int
    city_name: str
    timestamp: datetime
    current: WeatherFeatures
    forecast_1h: WeatherFeatures
    source: str = "model"

    model_config = {"from_attributes": True}


class WeatherCitySummary(BaseModel):
    """Compact city summary for map markers."""
    city_id: int
    city_name: str
    latitude: float
    longitude: float
    temperature_2m: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed_10m: Optional[float] = None
    uv_index: Optional[float] = None
    risk_score: Optional[float] = Field(default=0.0)
    disaster_type: Optional[str] = None
