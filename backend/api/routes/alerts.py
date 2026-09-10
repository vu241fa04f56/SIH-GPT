"""
alerts.py — FCM subscription management routes.

POST /alerts/subscribe
DELETE /alerts/unsubscribe
"""

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.schemas.alert_schema import SubscribeRequest, SubscribeResponse, UnsubscribeRequest
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import AlertSubscription

router = APIRouter()


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(body: SubscribeRequest):
    """Register a device FCM token + location for disaster push alerts."""
    sub_id = str(uuid.uuid4())

    async with get_async_session() as session:
        # Upsert on fcm_token
        existing = await session.execute(
            select(AlertSubscription).where(AlertSubscription.fcm_token == body.fcm_token)
        )
        sub = existing.scalar_one_or_none()

        if sub:
            sub.latitude = body.latitude
            sub.longitude = body.longitude
            sub.language = body.language
            sub.disaster_types = body.disaster_types
            sub_id = str(sub.id)
        else:
            new_sub = AlertSubscription(
                id=uuid.UUID(sub_id),
                fcm_token=body.fcm_token,
                latitude=body.latitude,
                longitude=body.longitude,
                language=body.language,
                disaster_types=body.disaster_types,
            )
            session.add(new_sub)

    return SubscribeResponse(subscription_id=sub_id)


@router.delete("/unsubscribe")
async def unsubscribe(body: UnsubscribeRequest):
    """Remove a device subscription."""
    async with get_async_session() as session:
        result = await session.execute(
            select(AlertSubscription).where(AlertSubscription.fcm_token == body.fcm_token)
        )
        sub = result.scalar_one_or_none()
        if sub:
            await session.delete(sub)
    return {"message": "Unsubscribed"}
