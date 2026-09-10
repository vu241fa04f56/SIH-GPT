"""
chatbot/server.py
─────────────────
Standalone FastAPI application for the WeatherGPT chatbot microservice.

This service runs on port 8001 and exposes:
  POST /chat    → Gemini-powered conversational weather assistant
  GET  /health  → Liveness probe

The chatbot internally calls the backend API (http://backend:8000) to
fetch live weather, disaster, and agro predictions before responding.

Run:
    uvicorn chatbot.server:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.chat import router as chat_router
from backend.api.routes.voice import router as voice_router

app = FastAPI(
    title="WeatherGPT Chatbot",
    description="Gemini-powered conversational weather assistant for India.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8082",
        "http://localhost:8081",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8082",
        "http://127.0.0.1:8081",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|10\.0\.2\.2)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(chat_router, prefix="/chat", tags=["Chatbot"])
app.include_router(voice_router, prefix="/voice", tags=["Voice Interaction"])


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health() -> dict:
    return {"status": "ok", "service": "chatbot"}
