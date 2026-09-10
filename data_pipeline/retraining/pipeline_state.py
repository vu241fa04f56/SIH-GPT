"""
pipeline_state.py
─────────────────
Tracks row counts and timestamps of model training runs to enable
continuous retraining triggered by new ingestion rows.

State file: models/pipeline_state.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from sqlalchemy import func, select

from backend.core.config import settings
from data_pipeline.storage.db_connection import get_async_session
from data_pipeline.storage.db_models import AgroRecord, DisasterRecord, WeatherRecord

STATE_FILE = Path(settings.MODEL_REGISTRY_PATH) / "pipeline_state.json"

DEFAULT_THRESHOLDS = {
    "weather": 500,    # retrain if >= 500 new weather rows
    "agro": 200,       # retrain if >= 200 new agro rows
    "disaster": 100,   # retrain if >= 100 new disaster rows
}

TABLE_MAP = {
    "weather": WeatherRecord,
    "agro": AgroRecord,
    "disaster": DisasterRecord,
}


def _load_state() -> dict:
    if not STATE_FILE.exists():
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        return {
            "weather": {"last_trained_at": None, "last_trained_row_count": 0},
            "agro": {"last_trained_at": None, "last_trained_row_count": 0},
            "disaster": {"last_trained_at": None, "last_trained_row_count": 0},
        }
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning(f"Could not read pipeline_state.json: {exc}. Using default state.")
        return {
            "weather": {"last_trained_at": None, "last_trained_row_count": 0},
            "agro": {"last_trained_at": None, "last_trained_row_count": 0},
            "disaster": {"last_trained_at": None, "last_trained_row_count": 0},
        }


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_last_trained_count(model_type: str) -> int:
    state = _load_state()
    return state.get(model_type, {}).get("last_trained_row_count", 0)


def update_last_train(model_type: str, row_count: int) -> None:
    state = _load_state()
    state[model_type] = {
        "last_trained_at": datetime.now(timezone.utc).isoformat(),
        "last_trained_row_count": row_count,
    }
    _save_state(state)
    logger.info(f"Updated pipeline state for '{model_type}': rows={row_count}")


async def get_total_table_rows(model_type: str) -> int:
    table_cls = TABLE_MAP.get(model_type)
    if not table_cls:
        return 0
    async with get_async_session() as session:
        result = await session.execute(select(func.count(table_cls.id)))
        return int(result.scalar_one() or 0)


async def get_unprocessed_rows(model_type: str) -> int:
    table_cls = TABLE_MAP.get(model_type)
    if not table_cls:
        return 0
    async with get_async_session() as session:
        result = await session.execute(
            select(func.count(table_cls.id)).where(table_cls.is_processed == False)  # noqa: E712
        )
        return int(result.scalar_one() or 0)


async def check_retrain_needed(model_type: str, threshold: int | None = None) -> tuple[bool, int]:
    """
    Check whether enough new data has accumulated to trigger model retraining.
    Returns (needs_retrain, new_rows_count).
    """
    thresh = threshold or DEFAULT_THRESHOLDS.get(model_type, 100)
    total_rows = await get_total_table_rows(model_type)
    last_trained = get_last_trained_count(model_type)
    new_rows = max(0, total_rows - last_trained)

    logger.info(
        f"Retrain check for '{model_type}': total={total_rows}, "
        f"last_trained_at={last_trained}, new_rows={new_rows}, threshold={thresh}"
    )

    return (new_rows >= thresh, new_rows)
