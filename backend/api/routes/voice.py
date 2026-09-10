"""
voice.py
────────
Voice interaction API route.

POST /voice/transcribe   → Upload audio → returns transcript text
POST /voice/respond      → Upload audio → full pipeline: STT → Chatbot → TTS → returns audio
GET  /voice/synthesize   → Text → TTS audio (for testing TTS output)

This closes the loop for voice-enabled interaction in rural settings:
  User speaks in Hindi/Tamil/Bengali → STT → Gemini chatbot → TTS → audio response

Supported formats: WEBM_OPUS (browser), MP3, FLAC, LINEAR16
Supported languages: en, hi, bn, te, mr, ta, gu, kn, ml, pa (11 Indian languages)
"""

from __future__ import annotations

import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from chatbot.llm_engine import WeatherGPTChatbot
from chatbot.voice.speech_to_text import LANGUAGE_CODES, transcribe_audio
from chatbot.voice.text_to_speech import synthesize_speech

router = APIRouter()

# Singleton chatbot (same pattern as chat.py)
_chatbot: WeatherGPTChatbot | None = None


def _get_chatbot() -> WeatherGPTChatbot:
    global _chatbot
    if _chatbot is None:
        _chatbot = WeatherGPTChatbot()
    return _chatbot


# ─── Schemas ──────────────────────────────────────────────────────────────────

class TranscribeResponse(BaseModel):
    transcript: str
    detected_language: str
    language_name: str


class VoiceRespondResponse(BaseModel):
    transcript: str
    reply: str
    language: str
    audio_available: bool


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    audio: UploadFile = File(..., description="Audio file (webm, mp3, flac, wav)"),
    language: str = Form(default="en", description="Hint language code: en, hi, bn, te, mr, ta, gu, kn, ml, pa"),
):
    """
    Convert uploaded audio to text using Google Cloud Speech-to-Text.

    Supports all 11 Indian languages + English. The language param is a hint;
    STT performs automatic language detection across all supported languages.

    Returns transcript + detected language code.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file received.")

    # Determine encoding from content type
    content_type = audio.content_type or ""
    if "webm" in content_type or "ogg" in content_type:
        encoding = "WEBM_OPUS"
    elif "mp3" in content_type or "mpeg" in content_type:
        encoding = "MP3"
    elif "flac" in content_type:
        encoding = "FLAC"
    else:
        encoding = "WEBM_OPUS"  # browser default

    bcp47 = LANGUAGE_CODES.get(language, "en-IN")
    transcript, detected_lang = await transcribe_audio(
        audio_bytes, hint_language=bcp47, audio_encoding=encoding
    )

    lang_names = {
        "en-IN": "English", "hi-IN": "Hindi", "bn-IN": "Bengali",
        "te-IN": "Telugu", "mr-IN": "Marathi", "ta-IN": "Tamil",
        "gu-IN": "Gujarati", "kn-IN": "Kannada", "ml-IN": "Malayalam",
        "pa-IN": "Punjabi", "ur-IN": "Urdu",
    }

    return TranscribeResponse(
        transcript=transcript or "(no speech detected)",
        detected_language=detected_lang,
        language_name=lang_names.get(detected_lang, detected_lang),
    )


@router.post("/respond", response_model=VoiceRespondResponse)
async def voice_respond(
    audio: UploadFile = File(..., description="Audio query from user"),
    language: str = Form(default="en", description="Language code: en, hi, bn, te, mr, ta, gu, kn, ml, pa"),
    latitude: float = Form(default=None),
    longitude: float = Form(default=None),
):
    """
    Full voice pipeline: Audio → STT → Gemini Chatbot → Text reply.

    Returns the text transcript, chatbot reply, and whether TTS audio is available.
    Use POST /voice/synthesize separately to convert the reply text to audio.

    This is the primary endpoint for voice-enabled rural weather queries.
    Example: Farmer speaks a question in Hindi → gets a Hindi text answer.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    content_type = audio.content_type or ""
    if "webm" in content_type or "ogg" in content_type:
        encoding = "WEBM_OPUS"
    elif "mp3" in content_type:
        encoding = "MP3"
    elif "flac" in content_type:
        encoding = "FLAC"
    else:
        encoding = "WEBM_OPUS"

    bcp47 = LANGUAGE_CODES.get(language, "en-IN")
    transcript, detected_lang = await transcribe_audio(
        audio_bytes, hint_language=bcp47, audio_encoding=encoding
    )

    if not transcript or transcript == "(no speech detected)":
        return VoiceRespondResponse(
            transcript="",
            reply="Sorry, I could not understand the audio. Please speak clearly and try again.",
            language=language,
            audio_available=False,
        )

    # Send transcript to chatbot
    chatbot = _get_chatbot()
    try:
        response = await chatbot.chat(
            message=transcript,
            language=language,
            user_lat=latitude,
            user_lon=longitude,
        )
        reply_text = response.get("reply", "I'm sorry, I couldn't generate a response.")
    except Exception as exc:
        reply_text = f"Chatbot error: {exc}"

    # Check if TTS is available (GCP credentials set)
    import os
    tts_available = bool(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "") and
        os.path.exists(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))
    )

    return VoiceRespondResponse(
        transcript=transcript,
        reply=reply_text,
        language=language,
        audio_available=tts_available,
    )


@router.post("/synthesize", response_class=Response)
async def synthesize(
    text: str = Form(..., description="Text to convert to speech"),
    language: str = Form(default="en", description="Language code: en, hi, bn, te, mr, ta, gu, kn, ml, pa"),
    speaking_rate: float = Form(default=0.9, description="Speaking rate (0.5–2.0)"),
):
    """
    Convert text to speech audio (MP3 bytes).

    Returns raw MP3 audio bytes. Used to give voice responses to weather queries.
    Supports all 11 Indian languages with Indian WaveNet voices.

    If GCP credentials are not configured, returns 503 with a helpful message.
    """
    audio_bytes = await synthesize_speech(text, lang=language, speaking_rate=speaking_rate)

    if not audio_bytes:
        raise HTTPException(
            status_code=503,
            detail=(
                "Text-to-speech is unavailable. "
                "Set GOOGLE_APPLICATION_CREDENTIALS in .env to enable voice output."
            ),
        )

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=response.mp3"},
    )
