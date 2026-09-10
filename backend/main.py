"""
main.py
───────
FastAPI application entry point for WeatherGPT backend.

Startup:
  - Loads all active model .pkl files into memory
  - Registers all routers
  - Starts WebSocket connection manager
  - Configures CORS

Run:
    uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.api.routes import advisory, alerts, chat, disaster, history, voice, weather
from backend.core.config import settings
from backend.services.inference_service import InferenceService
from backend.services.websocket_service import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup; clean up on shutdown."""
    logger.info("🚀 WeatherGPT backend starting up...")
    app.state.inference = InferenceService()
    app.state.inference.load_all_models()
    logger.success("Models loaded. Server ready.")
    yield
    logger.info("Shutting down WeatherGPT backend.")


app = FastAPI(
    title="WeatherGPT API",
    description=(
        "AI-powered weather forecasting, disaster early warning, "
        "and agro-advisory platform for India."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
allowed_origins_list = list(settings.ALLOWED_ORIGINS)
for dev_origin in [
    "http://localhost:8082",
    "http://localhost:8081",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8001",
    "http://127.0.0.1:8082",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:5173",
    "http://10.0.2.2:8082",
]:
    if dev_origin not in allowed_origins_list:
        allowed_origins_list.append(dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|10\.0\.2\.2)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(weather.router, prefix="/predict/weather", tags=["Weather"])
app.include_router(disaster.router, prefix="/predict/disaster", tags=["Disaster"])
app.include_router(advisory.router, prefix="/advisory", tags=["Agro Advisory"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(chat.router, prefix="/chat", tags=["Chatbot"])
app.include_router(history.router, prefix="/history", tags=["Climate History"])
app.include_router(voice.router, prefix="/voice", tags=["Voice Interaction"])


# ─── WebSocket ────────────────────────────────────────────────────────────────
from fastapi import WebSocket, WebSocketDisconnect  # noqa: E402


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for live prediction broadcasts.

    Clients connect here and receive JSON push updates whenever
    new predictions are generated for any city.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; server pushes data proactively
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    inference = getattr(app.state, "inference", None)
    return {
        "status": "ok",
        "version": "1.1.0",
        "models": inference.model_status() if inference else {},
    }
