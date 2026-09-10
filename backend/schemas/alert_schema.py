"""Pydantic v2 schemas for push alert subscriptions."""

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class SubscribeRequest(BaseModel):
    fcm_token: str = Field(..., description="Firebase Cloud Messaging device token")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    language: str = Field(default="en", max_length=8)
    disaster_types: Optional[list[str]] = Field(
        default=None,
        description="Filter alerts to specific disaster types. None = all types.",
    )


class SubscribeResponse(BaseModel):
    subscription_id: str
    message: str = "Subscribed successfully"


class UnsubscribeRequest(BaseModel):
    fcm_token: str
