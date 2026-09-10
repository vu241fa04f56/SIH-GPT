"""
test_disaster.py
────────────────
Tests for the disaster prediction endpoint and alert subscription.
"""

import pytest
from httpx import AsyncClient

from backend.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_disaster_city_not_found():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/predict/disaster/999999")
    assert resp.status_code in (404, 503)


@pytest.mark.anyio
async def test_disaster_overlay():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/predict/disaster/overlay/all")
    assert resp.status_code == 200
    data = resp.json()
    assert "cities" in data
    assert "generated_at" in data


@pytest.mark.anyio
async def test_alert_subscribe():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/alerts/subscribe",
            json={
                "fcm_token": "test-token-abc123",
                "latitude": 19.07,
                "longitude": 72.87,
                "language": "en",
            },
        )
    assert resp.status_code == 200
    assert "subscription_id" in resp.json()
