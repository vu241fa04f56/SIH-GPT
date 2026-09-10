"""
scheduler.py
────────────
APScheduler cron jobs for the WeatherGPT data pipeline with continuous
ingestion, preprocessing, and model retraining.

Continuous Flow:
  1. Ingest new rows from Open-Meteo APIs into live database (separate tables)
  2. Preprocess unprocessed rows
  3. Continuous retraining: if new row count exceeds threshold, retrain model
  4. Daily drift check (PSI) as a fallback safety net

Schedule:
  - Every hour (:05) → ingest weather → preprocess → retrain if >= threshold
  - Every hour (:10) → ingest disaster → preprocess → retrain if >= threshold
  - Every 6 hrs (:15) → ingest agro → preprocess → retrain if >= threshold
  - Daily 02:00 IST  → PSI drift check across all 3 models

Run:
    python -m data_pipeline.ingestion.scheduler
    python -m data_pipeline.ingestion.scheduler --once
    python -m data_pipeline.ingestion.scheduler --force-retrain
"""

from __future__ import annotations

import asyncio
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from data_pipeline.ingestion.fetch_agro_api import ingest_all_cities as ingest_agro
from data_pipeline.ingestion.fetch_disaster_api import ingest_all_cities as ingest_disaster
from data_pipeline.ingestion.fetch_weather_api import ingest_all_cities as ingest_weather
from data_pipeline.preprocessing.preprocess_agro import preprocess_agro_batch
from data_pipeline.preprocessing.preprocess_disaster import preprocess_disaster_batch
from data_pipeline.preprocessing.preprocess_weather import preprocess_weather_batch
from data_pipeline.retraining.drift_detector import run_drift_check
from data_pipeline.retraining.pipeline_state import check_retrain_needed
from data_pipeline.retraining.retrain_agro_model import retrain_agro_model
from data_pipeline.retraining.retrain_disaster_model import retrain_disaster_model
from data_pipeline.retraining.retrain_weather_model import retrain_weather_model


# ─── Job wrappers ────────────────────────────────────────────────────────────

async def job_ingest_weather(force_retrain: bool = False) -> None:
    """Ingest weather, preprocess new records, and trigger continuous retraining."""
    logger.info("⏰ Starting weather ingestion cycle...")
    try:
        await ingest_weather(days_back=1)
    except Exception as exc:
        logger.error(f"Weather ingestion error: {exc}")

    try:
        logger.info("⚙️ Preprocessing new weather records...")
        await preprocess_weather_batch(limit=50_000)
    except Exception as exc:
        logger.error(f"Weather preprocessing error: {exc}")

    try:
        needed, count = await check_retrain_needed("weather")
        if force_retrain or needed:
            logger.info(f"🔄 Continuous Training: retraining weather model ({count} new rows)...")
            await retrain_weather_model()
        else:
            logger.info(f"Weather model up to date ({count} new rows, threshold not reached).")
    except Exception as exc:
        logger.error(f"Weather retraining check error: {exc}")


async def job_ingest_disaster(force_retrain: bool = False) -> None:
    """Ingest disaster data, preprocess new records, and trigger continuous retraining."""
    logger.info("⏰ Starting disaster ingestion cycle...")
    try:
        await ingest_disaster(days_back=1)
    except Exception as exc:
        logger.error(f"Disaster ingestion error: {exc}")

    try:
        logger.info("⚙️ Preprocessing new disaster records...")
        await preprocess_disaster_batch(limit=50_000)
    except Exception as exc:
        logger.error(f"Disaster preprocessing error: {exc}")

    try:
        needed, count = await check_retrain_needed("disaster")
        if force_retrain or needed:
            logger.info(f"🔄 Continuous Training: retraining disaster model ({count} new rows)...")
            await retrain_disaster_model()
        else:
            logger.info(f"Disaster model up to date ({count} new rows, threshold not reached).")
    except Exception as exc:
        logger.error(f"Disaster retraining check error: {exc}")


async def job_ingest_agro(force_retrain: bool = False) -> None:
    """Ingest agro data, preprocess new records, and trigger continuous retraining."""
    logger.info("⏰ Starting agro ingestion cycle...")
    try:
        await ingest_agro(days_back=1)
    except Exception as exc:
        logger.error(f"Agro ingestion error: {exc}")

    try:
        logger.info("⚙️ Preprocessing new agro records...")
        await preprocess_agro_batch(limit=50_000)
    except Exception as exc:
        logger.error(f"Agro preprocessing error: {exc}")

    try:
        needed, count = await check_retrain_needed("agro")
        if force_retrain or needed:
            logger.info(f"🔄 Continuous Training: retraining agro model ({count} new rows)...")
            await retrain_agro_model()
        else:
            logger.info(f"Agro model up to date ({count} new rows, threshold not reached).")
    except Exception as exc:
        logger.error(f"Agro retraining check error: {exc}")


async def job_drift_and_retrain() -> None:
    """Daily fallback drift detection: retrain any model whose PSI > threshold."""
    logger.info("⏰ Running daily drift check + fallback retraining...")
    try:
        await run_drift_check()
    except Exception as exc:
        logger.error(f"Daily drift check error: {exc}")


# ─── Scheduler setup ─────────────────────────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    # Weather: every hour at :05
    scheduler.add_job(
        job_ingest_weather,
        trigger=CronTrigger(minute=5),
        id="ingest_weather",
        name="Hourly weather ingestion + continuous retrain",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Disaster: every hour at :10
    scheduler.add_job(
        job_ingest_disaster,
        trigger=CronTrigger(minute=10),
        id="ingest_disaster",
        name="Hourly disaster ingestion + continuous retrain",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Agro: every 6 hours at :15
    scheduler.add_job(
        job_ingest_agro,
        trigger=CronTrigger(hour="0,6,12,18", minute=15),
        id="ingest_agro",
        name="6-hourly agro ingestion + continuous retrain",
        replace_existing=True,
    )

    # Drift check + retrain: daily at 02:00 IST
    scheduler.add_job(
        job_drift_and_retrain,
        trigger=CronTrigger(hour=2, minute=0),
        id="drift_retrain",
        name="Daily PSI drift check and fallback retraining",
        replace_existing=True,
    )

    return scheduler


# ─── Entry point ─────────────────────────────────────────────────────────────

async def main(run_once: bool = False, force_retrain: bool = False) -> None:
    """Start the continuous ingestion & retraining scheduler loop."""
    if run_once or force_retrain:
        logger.info(f"Execution flag detected (run_once={run_once}, force_retrain={force_retrain})")
        logger.info("Executing weather pipeline...")
        await job_ingest_weather(force_retrain=force_retrain)

        logger.info("Executing disaster pipeline...")
        await job_ingest_disaster(force_retrain=force_retrain)

        logger.info("Executing agro pipeline...")
        await job_ingest_agro(force_retrain=force_retrain)

        logger.info("Executing drift check...")
        await job_drift_and_retrain()
        return

    scheduler = create_scheduler()
    scheduler.start()
    logger.success("Continuous Data & Training Scheduler started. Press Ctrl+C to exit.")

    try:
        await asyncio.Event().wait()  # run forever
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    is_once = "--once" in sys.argv
    is_force = "--force-retrain" in sys.argv
    asyncio.run(main(run_once=is_once, force_retrain=is_force))
