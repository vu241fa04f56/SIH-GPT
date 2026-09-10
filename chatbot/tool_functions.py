"""
tool_functions.py
─────────────────
Tools exposed to the Gemini LLM via function-calling.

Each tool calls the WeatherGPT backend REST API and returns
a structured dict. The LLM uses these results to ground its responses.

Tool declarations follow the google-generativeai SDK format.
"""

from __future__ import annotations

import os

import httpx
import google.generativeai as genai
from loguru import logger

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# ─── Tool implementations ─────────────────────────────────────────────────────

async def get_weather(city_id: int) -> dict:
    """Fetch live weather prediction for a city by ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND_URL}/predict/weather/{city_id}", timeout=15)
        resp.raise_for_status()
        return resp.json()


async def get_disaster_risk(city_id: int) -> dict:
    """Fetch 3-hour-ahead disaster risk for a city."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND_URL}/predict/disaster/{city_id}", timeout=15)
        resp.raise_for_status()
        return resp.json()


async def get_agro_advisory(city_id: int, crop: str = "rice") -> dict:
    """Fetch crop advisory for a city."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BACKEND_URL}/advisory/{city_id}", params={"crop": crop}, timeout=15
        )
        resp.raise_for_status()
        return resp.json()


async def search_city_by_name(city_name: str) -> dict:
    """Look up a city by name and return its ID + coordinates."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BACKEND_URL}/predict/weather/summary/all", timeout=20
        )
        if resp.status_code != 200:
            return {"error": "Could not fetch city list"}
        cities = resp.json()
        name_lower = city_name.lower()
        matches = [c for c in cities if name_lower in c.get("city_name", "").lower()]
        if matches:
            return matches[0]
        return {"error": f"City '{city_name}' not found"}


async def get_historical_weather(city_id: int, days: int = 30, variable: str = "temperature_2m") -> dict:
    """
    Fetch historical weather statistics and climate trend for a city.

    Returns aggregate stats (mean, min, max) plus daily anomalies
    for the requested variable over the past N days.
    Useful for questions about recent climate patterns, seasonal analysis,
    heatwave trends, rainfall deficits, etc.
    """
    async with httpx.AsyncClient() as client:
        # Get stats
        stats_resp = await client.get(
            f"{BACKEND_URL}/history/{city_id}/stats",
            params={"days": days},
            timeout=20,
        )
        # Get trend
        trend_resp = await client.get(
            f"{BACKEND_URL}/history/{city_id}/trend",
            params={"variable": variable, "days": days},
            timeout=20,
        )

    result: dict = {"city_id": city_id, "days": days}
    if stats_resp.status_code == 200:
        result["stats"] = stats_resp.json()
    if trend_resp.status_code == 200:
        result["trend"] = trend_resp.json()
    if not result.get("stats") and not result.get("trend"):
        return {"error": f"No historical data for city {city_id}"}
    return result


# ─── Tool executor ────────────────────────────────────────────────────────────

_TOOL_MAP = {
    "get_weather": get_weather,
    "get_disaster_risk": get_disaster_risk,
    "get_agro_advisory": get_agro_advisory,
    "search_city_by_name": search_city_by_name,
    "get_historical_weather": get_historical_weather,
}


async def execute_tool(name: str, args: dict) -> dict:
    """Dispatch a tool call by name with arguments."""
    fn = _TOOL_MAP.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await fn(**args)
    except Exception as exc:
        logger.error(f"Tool '{name}' failed: {exc}")
        return {"error": str(exc)}


# ─── Gemini tool declarations ─────────────────────────────────────────────────

TOOL_DECLARATIONS = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="search_city_by_name",
                description="Search for an Indian city by name and return its city_id and coordinates.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "city_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Name of the Indian city (e.g. 'Mumbai', 'Delhi')",
                        )
                    },
                    required=["city_name"],
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="get_weather",
                description=(
                    "Fetch current weather and 1-hour forecast for a city. "
                    "Returns all 39 weather features including temperature, humidity, "
                    "wind, precipitation, UV index, and air quality."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "city_id": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="Numeric city ID from search_city_by_name",
                        )
                    },
                    required=["city_id"],
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="get_disaster_risk",
                description=(
                    "Fetch 3-hour-ahead disaster risk for a city. "
                    "Returns disaster_type, severity, risk_score (0–1), "
                    "and recommended safety action."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "city_id": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="Numeric city ID",
                        )
                    },
                    required=["city_id"],
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="get_agro_advisory",
                description=(
                    "Fetch crop-specific agricultural advisory for a city. "
                    "Returns advisory_label and actionable advisory_text."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "city_id": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="Numeric city ID",
                        ),
                        "crop": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Crop name: rice, wheat, maize, sugarcane, cotton, etc.",
                        ),
                    },
                    required=["city_id"],
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="get_historical_weather",
                description=(
                    "Fetch historical weather statistics and climate trend for a city. "
                    "Use this for questions about: past weather, seasonal trends, "
                    "recent heatwaves, rainfall deficit, air quality history, "
                    "climate change analysis, or any question involving 'last N days', "
                    "'this month', 'recent', 'trend', 'average', 'warmest', 'driest'."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "city_id": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="Numeric city ID from search_city_by_name",
                        ),
                        "days": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="Number of past days to analyse (default 30, max 90)",
                        ),
                        "variable": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description=(
                                "Weather variable to trend: temperature_2m, precipitation, "
                                "wind_speed_10m, us_aqi, relative_humidity_2m, uv_index"
                            ),
                        ),
                    },
                    required=["city_id"],
                ),
            ),
        ]
    )
]
