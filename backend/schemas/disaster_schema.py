"""Pydantic v2 schemas for disaster prediction."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DisasterPredictionResponse(BaseModel):
    city_id: int
    city_name: str
    timestamp: datetime
    disaster_type: str  # "none" | "cyclone" | "flood" | etc.
    severity: Optional[str] = None  # "low" | "medium" | "high" | "extreme"
    risk_score: float = Field(ge=0.0, le=1.0)
    lead_hours: float = 3.0
    recommended_action: Optional[str] = None
    is_active: bool = False  # True if risk_score > 0.6

    model_config = {"from_attributes": True}


class DisasterMapOverlay(BaseModel):
    """All cities with current disaster risk, for the map overlay."""
    cities: list[dict]  # [{city_id, lat, lon, disaster_type, risk_score, severity}]
    generated_at: datetime
