"""Model loading and feature-compatible inference for the bundled pipelines."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from loguru import logger

from backend.core.config import settings


WEATHER_OUTPUT_FIELDS = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature",
    "precipitation", "rain", "snowfall", "snow_depth", "weather_code", "cloud_cover",
    "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high", "surface_pressure",
    "pressure_msl", "vapour_pressure_deficit", "wind_speed_10m", "wind_speed_100m",
    "wind_direction_10m", "wind_direction_100m", "wind_gusts_10m",
    "et0_fao_evapotranspiration", "cape", "lifted_index", "shortwave_radiation",
    "direct_radiation", "direct_normal_irradiance", "diffuse_radiation", "uv_index",
    "uv_index_clear_sky", "soil_temperature_0_to_7cm", "soil_moisture_0_to_7cm",
    "us_aqi", "pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide",
    "sulphur_dioxide", "ozone", "ammonia", "dust", "alder_pollen", "wave_height",
    "sea_surface_temperature",
]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _record_value(record: Any, key: str, default: float = 0.0) -> float:
    if isinstance(record, dict):
        return _number(record.get(key), default)
    return _number(getattr(record, key, None), default)


def _wet_bulb_celsius(temp: float, humidity: float) -> float:
    """Stull approximation used to recreate the saved model input."""
    rh = min(100.0, max(1.0, humidity))
    return (
        temp * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(temp + rh) - math.atan(rh - 1.676331)
        + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh) - 4.686035
    )


class InferenceService:
    """Load each bundled artifact once and adapt live records to its saved schema."""

    def __init__(self) -> None:
        self.weather_model: Any | None = None
        self.disaster_model: Any | None = None
        self.agro_model: Any | None = None
        self._registry_root = Path(settings.MODEL_REGISTRY_PATH)
        self.load_errors: dict[str, str] = {}

    def _load_active_model(self, model_type: str) -> Any | None:
        active_dir = self._registry_root / model_type / "model_registry" / "active"
        candidates = sorted(active_dir.glob("*.pkl")) + sorted(active_dir.glob("*.pickle"))
        if not candidates:
            logger.warning(f"No bundled/active model for '{model_type}'.")
            return None
        try:
            artifact = joblib.load(candidates[0])
            logger.info(f"Loaded {model_type} model from {candidates[0]}")
            return artifact
        except Exception as exc:
            self.load_errors[model_type] = str(exc)
            logger.exception(f"Could not load {model_type} model: {exc}")
            return None

    def load_all_models(self) -> None:
        self.weather_model = self._load_active_model("weather")
        self.disaster_model = self._load_active_model("disaster")
        self.agro_model = self._load_active_model("agro")

    def model_status(self) -> dict[str, dict[str, Any]]:
        return {
            name: {"loaded": model is not None, "error": self.load_errors.get(name)}
            for name, model in (("weather", self.weather_model), ("disaster", self.disaster_model), ("agro", self.agro_model))
        }

    def _weather_inputs(self, current: dict, history: list[Any] | None, latitude: float,
                        longitude: float, timestamp: datetime | None) -> pd.DataFrame:
        artifact = self.weather_model
        columns = artifact["feature_columns"]
        row = {column: _number(current.get(column)) for column in columns}
        row["direct_normal_irradiance"] = _number(current.get("direct_normal_irradiance", current.get("direct_radiation")))
        row["latitude"], row["longitude"] = latitude, longitude
        speed = _number(current.get("wind_speed_10m"))
        direction = math.radians(_number(current.get("wind_direction_10m")))
        row["wind_u_vector"] = -speed * math.sin(direction)
        row["wind_v_vector"] = -speed * math.cos(direction)
        row["wet_bulb_temp"] = _wet_bulb_celsius(_number(current.get("temperature_2m")), _number(current.get("relative_humidity_2m"), 50.0))
        ts = timestamp or datetime.now(timezone.utc)
        hour_angle = 2 * math.pi * ts.hour / 24
        day_angle = 2 * math.pi * ts.timetuple().tm_yday / 365.25
        row.update(sin_hour=math.sin(hour_angle), cos_hour=math.cos(hour_angle), sin_day=math.sin(day_angle), cos_day=math.cos(day_angle))

        records = history or []  # newest-first, including the current row at index 0
        pressure_3h = _record_value(records[3], "surface_pressure") if len(records) > 3 else _number(current.get("surface_pressure"))
        row["pressure_tendency_3h"] = _number(current.get("surface_pressure")) - pressure_3h
        for lag in (1, 2, 3, 24):
            rec = records[lag] if len(records) > lag else current
            row[f"temp_lag_{lag}"] = _record_value(rec, "temperature_2m", _number(current.get("temperature_2m")))
            row[f"humidity_lag_{lag}"] = _record_value(rec, "relative_humidity_2m", _number(current.get("relative_humidity_2m")))
            row[f"radiation_lag_{lag}"] = _record_value(rec, "shortwave_radiation", _number(current.get("shortwave_radiation")))
        return pd.DataFrame([[row[c] for c in columns]], columns=columns)

    def predict_weather(self, features: dict, history: list[Any] | None = None,
                        latitude: float = 0.0, longitude: float = 0.0,
                        timestamp: datetime | None = None) -> dict:
        if not isinstance(self.weather_model, dict) or "models" not in self.weather_model:
            return {col: features.get(col) for col in WEATHER_OUTPUT_FIELDS}
        artifact = self.weather_model
        frame = self._weather_inputs(features, history, latitude, longitude, timestamp)
        predicted: dict[str, float] = {}
        for target, model in artifact["models"].items():
            value = float(np.ravel(model.predict(frame))[0])
            if artifact.get("target_transforms", {}).get(target, {}).get("name") == "log1p":
                value = float(np.expm1(value))
            predicted[target] = value
        if "wind_direction_sin" in predicted and "wind_direction_cos" in predicted:
            predicted["wind_direction_10m"] = math.degrees(math.atan2(predicted.pop("wind_direction_sin"), predicted.pop("wind_direction_cos"))) % 360
        forecast = {col: features.get(col) for col in WEATHER_OUTPUT_FIELDS}
        forecast.update(predicted)
        for key in ("precipitation", "rain", "wind_speed_10m", "wind_gusts_10m", "shortwave_radiation", "direct_normal_irradiance", "diffuse_radiation"):
            if forecast.get(key) is not None:
                forecast[key] = max(0.0, _number(forecast[key]))
        if forecast.get("relative_humidity_2m") is not None:
            forecast["relative_humidity_2m"] = min(100.0, max(0.0, _number(forecast["relative_humidity_2m"])))
        if forecast.get("cloud_cover") is not None:
            forecast["cloud_cover"] = min(100.0, max(0.0, _number(forecast["cloud_cover"])))
        return forecast

    def predict_disaster(self, features: dict, history: list[Any] | None = None,
                         elevation: float = 0.0) -> dict:
        artifact = self.disaster_model
        if not isinstance(artifact, dict) or not {"model", "scaler", "label_encoder"}.issubset(artifact):
            return {"disaster_type": "none", "risk_score": 0.0, "lead_hours": 3.0}
        records = history or []
        rain24 = sum(_record_value(r, "rain") for r in records[:24])
        rain48 = sum(_record_value(r, "rain") for r in records[:48])
        wind = _number(features.get("wind_speed_10m")); gust = _number(features.get("wind_gusts_10m"))
        pressure = _number(features.get("surface_pressure", features.get("pressure_msl")), 1013.0)
        precip = _number(features.get("precipitation")); pm25 = _number(features.get("pm2_5"))
        row = {
            "temp_2m": _number(features.get("temperature_2m")), "precip_1h": precip,
            "rain_24h": rain24, "rain_48h": rain48, "wind_speed_10m": wind,
            "wind_gusts_10m": gust, "surface_pressure": pressure,
            "weather_code": _number(features.get("weather_code")), "us_aqi": _number(features.get("us_aqi")),
            "pm2_5": pm25, "river_discharge": _number(features.get("river_discharge")), "elevation": elevation,
            "max_quake_mag": _number(features.get("max_quake_mag")), "quake_depth": _number(features.get("quake_depth")),
            "tsunami_flag": _number(features.get("tsunami_flag")), "gdacs_cyclone": _number(features.get("gdacs_cyclone")),
            "gdacs_volcano": _number(features.get("gdacs_volcano")),
            "wind_pressure_shear": gust * max(0.0, 1013.25 - pressure),
            "precipitation_saturation_rate": precip * _number(features.get("relative_humidity_2m")) / 100.0,
            "thermal_particulate_index": max(0.0, _number(features.get("temperature_2m")) - 25.0) * pm25,
        }
        order = artifact.get("feature_order") or list(row)
        frame = pd.DataFrame([[row.get(c, 0.0) for c in order]], columns=order)
        probabilities = np.ravel(artifact["model"].predict_proba(artifact["scaler"].transform(frame)))
        encoded = np.array([int(np.argmax(probabilities))])
        label = str(artifact["label_encoder"].inverse_transform(encoded)[0])
        classes = list(artifact["label_encoder"].classes_)
        nominal_probability = float(probabilities[classes.index("nominal")]) if "nominal" in classes else 0.0
        if label == "nominal":
            return {"disaster_type": "none", "risk_score": 1.0 - nominal_probability, "lead_hours": 3.0}
        return {"disaster_type": label, "risk_score": float(probabilities[encoded[0]]), "lead_hours": 3.0}

    @staticmethod
    def _safe_encode(encoder: Any, value: str) -> int:
        classes = list(encoder.classes_); normalized = value.casefold()
        selected = next((c for c in classes if str(c).casefold() == normalized), classes[0])
        return int(encoder.transform([selected])[0])

    def predict_advisory(self, features: dict, history: list[Any] | None = None) -> dict:
        artifact = self.agro_model
        if not isinstance(artifact, dict) or "models" not in artifact:
            return {"advisory_label": "UNKNOWN", "advisory_text": "Advisory model is unavailable.", "predictions": {}}
        now = features.get("timestamp") or datetime.now(timezone.utc); records = history or []
        def values(key: str, hours: int) -> list[float]:
            return [_record_value(r, key) for r in records[:hours]] or [_number(features.get(key))]
        def total(key: str, hours: int) -> float:
            return float(sum(values(key, hours)))
        temps1, humidity1 = values("temperature_2m", 24), values("relative_humidity_2m", 24)
        daily_rain = [total("rain", min((offset + 1) * 24, len(records))) - total("rain", min(offset * 24, len(records))) for offset in range(14)]
        dry_days = next((i for i, rain in enumerate(daily_rain) if rain > 0.1), len(daily_rain))
        rainy_days = next((i for i, rain in enumerate(daily_rain) if rain <= 0.1), len(daily_rain))
        doy_angle = 2 * math.pi * now.timetuple().tm_yday / 365.25
        row = {
            "latitude": _number(features.get("latitude")), "longitude": _number(features.get("longitude")),
            "temperature_2m_mean": float(np.mean(temps1)), "temperature_2m_min": min(temps1), "temperature_2m_max": max(temps1),
            "relative_humidity_2m_mean": float(np.mean(humidity1)), "precipitation_sum": total("precipitation", 24),
            "wind_speed_10m_max": max(values("wind_speed_10m", 24)), "surface_pressure_mean": float(np.mean(values("surface_pressure", 24))),
            "shortwave_radiation_sum": total("shortwave_radiation", 24), "dew_point_2m_mean": float(np.mean(values("dew_point_2m", 24))),
            "vapor_pressure_deficit": float(np.mean(values("vapour_pressure_deficit", 24))), "et0_fao_evapotranspiration": total("et0_fao_evapotranspiration", 24),
            "rainfall_1d": total("rain", 24), "rainfall_3d_sum": total("rain", 72), "rainfall_7d_sum": total("rain", 168), "rainfall_14d_sum": total("rain", 336),
            "temperature_3d_mean": float(np.mean(values("temperature_2m", 72))), "temperature_7d_mean": float(np.mean(values("temperature_2m", 168))),
            "temperature_3d_max": max(values("temperature_2m", 72)), "temperature_7d_max": max(values("temperature_2m", 168)), "temperature_3d_min": min(values("temperature_2m", 72)),
            "humidity_3d_mean": float(np.mean(values("relative_humidity_2m", 72))), "humidity_7d_mean": float(np.mean(values("relative_humidity_2m", 168))),
            "et0_3d_sum": total("et0_fao_evapotranspiration", 72), "et0_7d_sum": total("et0_fao_evapotranspiration", 168),
            "wind_speed_3d_mean": float(np.mean(values("wind_speed_10m", 72))), "consecutive_dry_days": dry_days, "consecutive_rain_days": rainy_days,
            "doy_sin": math.sin(doy_angle), "doy_cos": math.cos(doy_angle), "month": now.month,
        }
        category_values = {"crop": str(features.get("crop_type", "Rice")), "crop_stage": str(features.get("growth_stage", "Tillering")), "agro_season": str(features.get("agro_season", "KHARIF"))}
        for name, value in category_values.items():
            row[f"{name}_enc"] = self._safe_encode(artifact["cat_encoders"][name], value)
        columns = artifact["all_features"]; frame = pd.DataFrame([[row.get(c, 0.0) for c in columns]], columns=columns)
        predictions = {}
        for target, model in artifact["models"].items():
            encoded = np.asarray(model.predict(frame), dtype=int)
            predictions[target] = str(artifact["target_encoders"][target].inverse_transform(encoded)[0])
        risk = predictions.get("crop_weather_risk", "UNKNOWN")
        advisory = (f"Crop weather risk: {risk}. Irrigation: {predictions.get('irrigation', 'UNKNOWN')}. "
                    f"Heat stress: {predictions.get('heat_stress', 'UNKNOWN')}. Waterlogging: {predictions.get('waterlogging_risk', 'UNKNOWN')}. "
                    f"Spraying: {predictions.get('spraying_suitability', 'UNKNOWN')}.")
        return {"advisory_label": risk, "advisory_text": advisory, "predictions": predictions}
