"""
speech_to_text.py
──────────────────
Voice input: converts audio bytes to text using Google Cloud Speech-to-Text.

Supported formats: LINEAR16, FLAC, WEBM_OPUS, MP3
Supports all Indian regional languages.

Usage:
    from chatbot.voice.speech_to_text import transcribe_audio

    text, lang = await transcribe_audio(audio_bytes, hint_language="hi-IN")
"""

from __future__ import annotations

import os

from loguru import logger

LANGUAGE_CODES = {
    "en": "en-IN",
    "hi": "hi-IN",
    "bn": "bn-IN",
    "te": "te-IN",
    "mr": "mr-IN",
    "ta": "ta-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    "ur": "ur-IN",
}


async def transcribe_audio(
    audio_bytes: bytes,
    hint_language: str = "en-IN",
    audio_encoding: str = "WEBM_OPUS",
    sample_rate_hertz: int = 48000,
) -> tuple[str, str]:
    """
    Transcribe audio bytes using Google Cloud STT.

    Parameters
    ----------
    audio_bytes      : Raw audio file bytes
    hint_language    : BCP-47 language code (e.g. 'hi-IN', 'en-IN')
    audio_encoding   : Audio encoding format
    sample_rate_hertz: Audio sample rate

    Returns
    -------
    (transcript, detected_language) tuple
    """
    gcp_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not gcp_creds or not os.path.exists(gcp_creds):
        logger.warning("[STT] GCP credentials not set. Returning empty transcript.")
        return "", hint_language

    try:
        from google.cloud import speech

        client = speech.SpeechClient()
        encoding_map = {
            "LINEAR16": speech.RecognitionConfig.AudioEncoding.LINEAR16,
            "FLAC": speech.RecognitionConfig.AudioEncoding.FLAC,
            "WEBM_OPUS": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            "MP3": speech.RecognitionConfig.AudioEncoding.MP3,
        }
        encoding = encoding_map.get(audio_encoding, speech.RecognitionConfig.AudioEncoding.WEBM_OPUS)

        config = speech.RecognitionConfig(
            encoding=encoding,
            sample_rate_hertz=sample_rate_hertz,
            language_code=hint_language,
            alternative_language_codes=list(LANGUAGE_CODES.values()),
            enable_automatic_punctuation=True,
            model="latest_long",
        )
        audio = speech.RecognitionAudio(content=audio_bytes)
        response = client.recognize(config=config, audio=audio)

        if not response.results:
            return "", hint_language

        best = response.results[0].alternatives[0]
        detected = getattr(response.results[0], "language_code", hint_language)
        return best.transcript, detected

    except Exception as exc:
        logger.error(f"STT error: {exc}")
        return "", hint_language
