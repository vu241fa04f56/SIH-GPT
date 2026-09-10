"""
test_weather.py
───────────────
Integration tests for the weather prediction endpoint.

Run:
    pytest backend/tests/test_weather.py -v
"""

import pytest
from httpx import AsyncClient

from backend.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_weather_city_not_found():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/predict/weather/999999")
    assert resp.status_code in (404, 503)


@pytest.mark.anyio
async def test_weather_summary_all():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/predict/weather/summary/all")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_chat_endpoint_stub():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            json={"message": "What is the weather in Delhi?", "language": "en"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
