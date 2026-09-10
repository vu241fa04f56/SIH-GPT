"""Smoke-test the exact model artifacts shipped with the project."""

from datetime import datetime, timezone

from backend.services.inference_service import InferenceService


def test_bundled_models_load_and_predict():
    service = InferenceService()
    service.load_all_models()
    assert all(item["loaded"] for item in service.model_status().values())

    current = {
        "temperature_2m": 28.0, "relative_humidity_2m": 70.0,
        "dew_point_2m": 22.0, "apparent_temperature": 31.0,
        "precipitation": 0.2, "rain": 0.2, "surface_pressure": 1005.0,
        "pressure_msl": 1008.0, "wind_speed_10m": 12.0,
        "wind_direction_10m": 180.0, "wind_gusts_10m": 20.0,
        "et0_fao_evapotranspiration": 0.1, "vapour_pressure_deficit": 0.8,
        "soil_temperature_0_to_7cm": 27.0, "soil_moisture_0_to_7cm": 0.25,
        "shortwave_radiation": 300.0, "direct_normal_irradiance": 450.0,
        "diffuse_radiation": 120.0, "cloud_cover": 50.0,
        "weather_code": 2, "us_aqi": 80.0, "pm2_5": 40.0,
    }
    history = [{**current, "rain": 0.1} for _ in range(336)]
    now = datetime.now(timezone.utc)

    weather = service.predict_weather(current, history, 25.6, 85.1, now)
    disaster = service.predict_disaster(current, history, 53.0)
    agro = service.predict_advisory({
        **current, "crop_type": "Rice", "growth_stage": "Tillering",
        "agro_season": "KHARIF", "latitude": 25.6, "longitude": 85.1,
        "timestamp": now,
    }, history)

    assert weather["temperature_2m"] is not None
    assert {"disaster_type", "risk_score", "lead_hours"} <= disaster.keys()
    assert len(agro["predictions"]) == 5
