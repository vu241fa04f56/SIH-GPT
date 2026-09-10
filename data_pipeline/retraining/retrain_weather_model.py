"""
retrain_weather_model.py — Retraining wrapper for the weather model.
Delegates to models/weather/train_weather_model.py.
"""

import asyncio

from loguru import logger

from models.weather.train_weather_model import train_weather_model


async def retrain_weather_model() -> None:
    logger.info("🔄 Retraining weather model...")
    path = await train_weather_model()
    if path:
        logger.success(f"Weather model retrained → {path}")
    else:
        logger.error("Weather model retraining failed.")


if __name__ == "__main__":
    asyncio.run(retrain_weather_model())
