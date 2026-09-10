"""
retrain_agro_model.py — Retraining wrapper for the agro model.
"""

import asyncio
from loguru import logger
from models.agro.train_agro_model import train_agro_model


async def retrain_agro_model() -> None:
    logger.info("🔄 Retraining agro model...")
    path = await train_agro_model()
    if path:
        logger.success(f"Agro model retrained → {path}")
    else:
        logger.error("Agro model retraining failed.")


if __name__ == "__main__":
    asyncio.run(retrain_agro_model())
