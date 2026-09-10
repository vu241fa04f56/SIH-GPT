"""
intent_parser.py
─────────────────
Lightweight rule-based intent and entity extractor.

Runs before the LLM call to:
  1. Identify what the user is asking (intent)
  2. Extract the mentioned city name
  3. Fall back to user's GPS location if no city mentioned

This keeps the first Gemini call focused on data retrieval,
not entity extraction.
"""

from __future__ import annotations

import re

from loguru import logger

from backend.services.geo_service import nearest_city

# ─── Intent patterns ─────────────────────────────────────────────────────────

INTENT_PATTERNS: dict[str, list[str]] = {
    "weather": [
        r"weather", r"temperature", r"temp", r"humid", r"rain", r"rainfall",
        r"wind", r"forecast", r"sky", r"cloud", r"sun", r"snow",
    ],
    "disaster": [
        r"disaster", r"cyclone", r"flood", r"earthquake", r"landslide",
        r"typhoon", r"lightning", r"storm", r"alert", r"warning", r"safe",
        r"evacuate", r"danger", r"risk",
    ],
    "agro_advisory": [
        r"crop", r"farm", r"agro", r"sow", r"harvest", r"irrigat",
        r"fertiliz", r"pesticide", r"rice", r"wheat", r"maize", r"cotton",
        r"sugarcane", r"agriculture",
    ],
    "air_quality": [
        r"air quality", r"aqi", r"pm2\.?5", r"pm10", r"pollution",
        r"smog", r"ammonia", r"nitrogen", r"ozone",
    ],
}

# ─── City name extraction ─────────────────────────────────────────────────────

# Top Indian cities — extend as needed
KNOWN_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Bangalore", "Chennai", "Kolkata",
    "Hyderabad", "Ahmedabad", "Pune", "Surat", "Jaipur", "Lucknow",
    "Kanpur", "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam",
    "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik",
    "Faridabad", "Meerut", "Rajkot", "Kalyan", "Vasai", "Varanasi",
    "Srinagar", "Aurangabad", "Dhanbad", "Amritsar", "Navi Mumbai",
    "Allahabad", "Ranchi", "Howrah", "Coimbatore", "Jabalpur",
    "Gwalior", "Vijayawada", "Jodhpur", "Madurai", "Raipur",
    "Kota", "Chandigarh", "Guwahati", "Solapur", "Hubbali",
]

CITY_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in KNOWN_CITIES) + r")\b",
    re.IGNORECASE,
)


def detect_intent(text: str) -> str:
    """Return the highest-confidence intent label for a message."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, text_lower))
        if score:
            scores[intent] = score
    if not scores:
        return "general"
    return max(scores, key=scores.get)


def extract_city_from_text(text: str) -> str | None:
    """Return the first recognised Indian city name from the text."""
    match = CITY_PATTERN.search(text)
    return match.group(1) if match else None


async def extract_city_and_intent(
    text: str,
    user_lat: float | None = None,
    user_lon: float | None = None,
) -> dict:
    """
    Parse a user message to extract intent and city.

    Falls back to nearest city via GPS if no city name found in text.
    """
    intent = detect_intent(text)
    city_name = extract_city_from_text(text)

    if not city_name and user_lat is not None and user_lon is not None:
        try:
            city = await nearest_city(user_lat, user_lon)
            city_name = city.name if city else None
        except Exception as exc:
            logger.warning(f"Nearest city lookup failed: {exc}")

    return {"intent": intent, "city_name": city_name}
