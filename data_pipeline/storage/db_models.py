"""
db_models.py
────────────
SQLAlchemy ORM models for all three datasets.

Tables:
    - City              — 800 Indian cities with PostGIS geometry
    - WeatherRecord     — weather/AQ/marine API rows (raw + processed)
    - DisasterRecord    — disaster event rows
    - AgroRecord        — crop-advisory feature rows
    - AlertSubscription — device FCM tokens + location
    - ModelVersion      — model registry metadata
"""

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data_pipeline.storage.db_connection import Base


# ─── City ────────────────────────────────────────────────────────────────────

class City(Base):
    """Indian city / district master table."""

    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    district: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_m: Mapped[float | None] = mapped_column(Float)
    # PostGIS point — SRID 4326 (WGS-84)
    geom: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )
    is_coastal: Mapped[bool] = mapped_column(Boolean, default=False)

    weather_records: Mapped[list["WeatherRecord"]] = relationship(back_populates="city")
    disaster_records: Mapped[list["DisasterRecord"]] = relationship(back_populates="city")
    agro_records: Mapped[list["AgroRecord"]] = relationship(back_populates="city")

    __table_args__ = (
        Index("ix_cities_geom", "geom", postgresql_using="gist"),
    )


# ─── WeatherRecord ───────────────────────────────────────────────────────────

class WeatherRecord(Base):
    """
    Enriched weather observation row used to construct the model's 39 inputs.

    Feature list (Open-Meteo fields):
    temperature_2m, relative_humidity_2m, dew_point_2m, apparent_temperature,
    precipitation, rain, snowfall, snow_depth,
    weather_code, cloud_cover, cloud_cover_low, cloud_cover_mid, cloud_cover_high,
    surface_pressure, pressure_msl, vapour_pressure_deficit,
    wind_speed_10m, wind_speed_100m, wind_direction_10m, wind_direction_100m,
    wind_gusts_10m, et0_fao_evapotranspiration, cape, lifted_index,
    shortwave_radiation, direct_radiation, diffuse_radiation,
    uv_index, uv_index_clear_sky,
    # Air quality (separate Open-Meteo call, joined)
    pm10, pm2_5, carbon_monoxide, nitrogen_dioxide, sulphur_dioxide, ozone,
    ammonia, dust, alder_pollen,
    # Marine (coastal cities only)
    wave_height, sea_surface_temperature
    """

    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Atmospheric ──────────────────────────────────────────────────────────
    temperature_2m: Mapped[float | None] = mapped_column(Float)
    relative_humidity_2m: Mapped[float | None] = mapped_column(Float)
    dew_point_2m: Mapped[float | None] = mapped_column(Float)
    apparent_temperature: Mapped[float | None] = mapped_column(Float)
    precipitation: Mapped[float | None] = mapped_column(Float)
    rain: Mapped[float | None] = mapped_column(Float)
    snowfall: Mapped[float | None] = mapped_column(Float)
    snow_depth: Mapped[float | None] = mapped_column(Float)
    weather_code: Mapped[int | None] = mapped_column(Integer)
    cloud_cover: Mapped[float | None] = mapped_column(Float)
    cloud_cover_low: Mapped[float | None] = mapped_column(Float)
    cloud_cover_mid: Mapped[float | None] = mapped_column(Float)
    cloud_cover_high: Mapped[float | None] = mapped_column(Float)
    surface_pressure: Mapped[float | None] = mapped_column(Float)
    pressure_msl: Mapped[float | None] = mapped_column(Float)
    vapour_pressure_deficit: Mapped[float | None] = mapped_column(Float)

    # ── Wind ─────────────────────────────────────────────────────────────────
    wind_speed_10m: Mapped[float | None] = mapped_column(Float)
    wind_speed_100m: Mapped[float | None] = mapped_column(Float)
    wind_direction_10m: Mapped[float | None] = mapped_column(Float)
    wind_direction_100m: Mapped[float | None] = mapped_column(Float)
    wind_gusts_10m: Mapped[float | None] = mapped_column(Float)

    # ── Radiation / Energy ───────────────────────────────────────────────────
    et0_fao_evapotranspiration: Mapped[float | None] = mapped_column(Float)
    cape: Mapped[float | None] = mapped_column(Float)
    lifted_index: Mapped[float | None] = mapped_column(Float)
    shortwave_radiation: Mapped[float | None] = mapped_column(Float)
    direct_radiation: Mapped[float | None] = mapped_column(Float)
    diffuse_radiation: Mapped[float | None] = mapped_column(Float)
    direct_normal_irradiance: Mapped[float | None] = mapped_column(Float)
    soil_temperature_0_to_7cm: Mapped[float | None] = mapped_column(Float)
    soil_moisture_0_to_7cm: Mapped[float | None] = mapped_column(Float)
    uv_index: Mapped[float | None] = mapped_column(Float)
    uv_index_clear_sky: Mapped[float | None] = mapped_column(Float)

    # ── Air Quality ──────────────────────────────────────────────────────────
    pm10: Mapped[float | None] = mapped_column(Float)
    pm2_5: Mapped[float | None] = mapped_column(Float)
    us_aqi: Mapped[float | None] = mapped_column(Float)
    carbon_monoxide: Mapped[float | None] = mapped_column(Float)
    nitrogen_dioxide: Mapped[float | None] = mapped_column(Float)
    sulphur_dioxide: Mapped[float | None] = mapped_column(Float)
    ozone: Mapped[float | None] = mapped_column(Float)
    ammonia: Mapped[float | None] = mapped_column(Float)
    dust: Mapped[float | None] = mapped_column(Float)
    alder_pollen: Mapped[float | None] = mapped_column(Float)

    # ── Marine (coastal only) ─────────────────────────────────────────────────
    wave_height: Mapped[float | None] = mapped_column(Float)
    sea_surface_temperature: Mapped[float | None] = mapped_column(Float)

    city: Mapped["City"] = relationship(back_populates="weather_records")

    __table_args__ = (
        Index("ix_weather_city_ts", "city_id", "timestamp"),
    )


# ─── DisasterRecord ───────────────────────────────────────────────────────────

class DisasterRecord(Base):
    """Disaster event row (historical or model-derived risk).

    Individual API columns
    ─────────────────────
    All extreme-weather variables fetched from Open-Meteo are stored as
    dedicated typed columns so they are directly queryable via SQL.
    The legacy ``raw_features`` JSONB column is kept for backwards compat.
    """

    __tablename__ = "disaster_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    disaster_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # e.g. earthquake, cyclone, flood, heavy_rain, lightning, typhoon, landslide
    severity: Mapped[str | None] = mapped_column(String(32))  # low / medium / high / extreme
    risk_score: Mapped[float | None] = mapped_column(Float)   # 0.0–1.0
    is_predicted: Mapped[bool] = mapped_column(Boolean, default=False)  # True = model output
    lead_hours: Mapped[float | None] = mapped_column(Float)   # prediction horizon in hours

    # ── Open-Meteo extreme-weather variables (individual columns) ────────────
    cape: Mapped[float | None] = mapped_column(Float)           # J/kg — thunderstorm/cyclone
    wind_gusts_10m: Mapped[float | None] = mapped_column(Float) # km/h
    precipitation: Mapped[float | None] = mapped_column(Float)  # mm/hr
    lifted_index: Mapped[float | None] = mapped_column(Float)   # K
    pressure_msl: Mapped[float | None] = mapped_column(Float)   # hPa
    rain: Mapped[float | None] = mapped_column(Float)           # mm/hr
    snowfall: Mapped[float | None] = mapped_column(Float)       # cm/hr

    # ── Legacy JSONB blob (kept for backwards compat) ─────────────────────────
    raw_features: Mapped[dict | None] = mapped_column(JSONB)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Source metadata
    source: Mapped[str | None] = mapped_column(String(64))   # "open_meteo_derived" | "seed_csv"

    city: Mapped["City"] = relationship(back_populates="disaster_records")

    __table_args__ = (
        Index("ix_disaster_city_ts", "city_id", "timestamp"),
        Index("ix_disaster_type", "disaster_type"),
    )


# ─── AgroRecord ───────────────────────────────────────────────────────────────

class AgroRecord(Base):
    """Agro-advisory input row (weather + crop context).

    Individual API columns
    ─────────────────────
    All variables fetched from Open-Meteo archive API are stored as
    dedicated typed columns so they are directly queryable via SQL.
    The legacy ``features`` JSONB column is kept for backwards compatibility.
    """

    __tablename__ = "agro_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    crop_type: Mapped[str | None] = mapped_column(String(64), index=True)
    growth_stage: Mapped[str | None] = mapped_column(String(64))

    # ── Season / calendar context ────────────────────────────────────────────
    month: Mapped[int | None] = mapped_column(Integer)        # 1–12
    season: Mapped[str | None] = mapped_column(String(16))    # kharif | rabi | perennial

    # ── Open-Meteo archive weather variables (individual columns) ────────────
    temperature_2m: Mapped[float | None] = mapped_column(Float)
    relative_humidity_2m: Mapped[float | None] = mapped_column(Float)
    precipitation: Mapped[float | None] = mapped_column(Float)
    et0_fao_evapotranspiration: Mapped[float | None] = mapped_column(Float)
    wind_speed_10m: Mapped[float | None] = mapped_column(Float)
    cloud_cover: Mapped[float | None] = mapped_column(Float)
    uv_index: Mapped[float | None] = mapped_column(Float)
    shortwave_radiation: Mapped[float | None] = mapped_column(Float)

    # ── Derived / city-level ─────────────────────────────────────────────────
    elevation_m: Mapped[float | None] = mapped_column(Float)
    soil_moisture: Mapped[float | None] = mapped_column(Float)

    # ── Model output ─────────────────────────────────────────────────────────
    advisory_label: Mapped[str | None] = mapped_column(String(128))
    advisory_text: Mapped[str | None] = mapped_column(Text)

    # ── Legacy JSONB blob (kept for backwards compat) ─────────────────────────
    features: Mapped[dict | None] = mapped_column(JSONB)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    city: Mapped["City"] = relationship(back_populates="agro_records")

    __table_args__ = (
        Index("ix_agro_city_ts", "city_id", "timestamp"),
        Index("ix_agro_crop", "crop_type"),
    )


# ─── AlertSubscription ────────────────────────────────────────────────────────

class AlertSubscription(Base):
    """Device subscription for FCM push alerts."""

    __tablename__ = "alert_subscriptions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fcm_token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="en")
    disaster_types: Mapped[list | None] = mapped_column(JSONB)  # null = all
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    geom: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )

    __table_args__ = (
        Index("ix_subscriptions_geom", "geom", postgresql_using="gist"),
    )


# ─── ModelVersion ────────────────────────────────────────────────────────────

class ModelVersion(Base):
    """Model registry — tracks each trained model artefact."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # "weather" | "disaster" | "agro"
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    pkl_path: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    training_rows: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
