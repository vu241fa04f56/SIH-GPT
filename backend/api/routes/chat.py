"""
chat.py — Chatbot API route.

POST /chat  → send a message, get a Gemini-powered response
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chatbot.llm_engine import WeatherGPTChatbot

router = APIRouter()
_chatbot: WeatherGPTChatbot | None = None


def get_chatbot() -> WeatherGPTChatbot:
    global _chatbot
    if _chatbot is None:
        _chatbot = WeatherGPTChatbot()
    return _chatbot


class ChatRequest(BaseModel):
    message: str
    language: str = "en"
    latitude: float | None = None
    longitude: float | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    intent: str | None = None
    city_name: str | None = None
    disaster_alert: dict | None = None
    language: str = "en"


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """
    Send a message to WeatherGPT.

    The LLM uses Gemini function-calling to pull live predictions
    from the backend before responding.
    """
    try:
        chatbot = get_chatbot()
        response = await chatbot.chat(
            message=body.message,
            language=body.language,
            user_lat=body.latitude,
            user_lon=body.longitude,
        )
        return ChatResponse(
            reply=response.get("reply", ""),
            intent=response.get("intent"),
            city_name=response.get("city_name"),
            disaster_alert=response.get("disaster_alert"),
            language=body.language,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
