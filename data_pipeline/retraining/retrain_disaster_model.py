"""
retrain_disaster_model.py — Retraining wrapper for the disaster model.
"""

import asyncio
from loguru import logger
from models.disaster.train_disaster_model import train_disaster_model


async def retrain_disaster_model() -> None:
    logger.info("🔄 Retraining disaster model...")
    path = await train_disaster_model()
    if path:
        logger.success(f"Disaster model retrained → {path}")
    else:
        logger.error("Disaster model retraining failed.")


if __name__ == "__main__":
    asyncio.run(retrain_disaster_model())
