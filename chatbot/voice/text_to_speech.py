"""
text_to_speech.py
──────────────────
Voice output: converts response text to audio using Google Cloud TTS.

Usage:
    from chatbot.voice.text_to_speech import synthesize_speech

    audio_bytes = await synthesize_speech("Mumbai mein aaj barish hogi.", lang="hi")
    # Write audio_bytes to a .mp3 / .wav file or stream to client
"""

from __future__ import annotations

import os

from loguru import logger

VOICE_MAP: dict[str, dict] = {
    "en": {"language_code": "en-IN", "name": "en-IN-Wavenet-A", "gender": "FEMALE"},
    "hi": {"language_code": "hi-IN", "name": "hi-IN-Wavenet-A", "gender": "FEMALE"},
    "bn": {"language_code": "bn-IN", "name": "bn-IN-Wavenet-A", "gender": "FEMALE"},
    "te": {"language_code": "te-IN", "name": "te-IN-Standard-A", "gender": "FEMALE"},
    "mr": {"language_code": "mr-IN", "name": "mr-IN-Wavenet-A", "gender": "FEMALE"},
    "ta": {"language_code": "ta-IN", "name": "ta-IN-Wavenet-A", "gender": "FEMALE"},
    "gu": {"language_code": "gu-IN", "name": "gu-IN-Wavenet-A", "gender": "FEMALE"},
    "kn": {"language_code": "kn-IN", "name": "kn-IN-Wavenet-A", "gender": "FEMALE"},
    "ml": {"language_code": "ml-IN", "name": "ml-IN-Wavenet-A", "gender": "FEMALE"},
    "pa": {"language_code": "pa-IN", "name": "pa-IN-Standard-A", "gender": "FEMALE"},
}


async def synthesize_speech(
    text: str,
    lang: str = "en",
    speaking_rate: float = 0.9,
    audio_format: str = "MP3",
) -> bytes:
    """
    Convert text to speech audio bytes.

    Parameters
    ----------
    text          : The text to synthesize
    lang          : ISO 639-1 language code (e.g. 'hi', 'en')
    speaking_rate : Speed factor (0.5–4.0, default 0.9 for clarity)
    audio_format  : 'MP3' or 'LINEAR16'

    Returns
    -------
    Audio bytes (empty bytes if TTS is unavailable)
    """
    gcp_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not gcp_creds or not os.path.exists(gcp_creds):
        logger.warning("[TTS] GCP credentials not set. Returning empty audio.")
        return b""

    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()
        voice_info = VOICE_MAP.get(lang, VOICE_MAP["en"])
        gender_map = {
            "FEMALE": texttospeech.SsmlVoiceGender.FEMALE,
            "MALE": texttospeech.SsmlVoiceGender.MALE,
        }

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_info["language_code"],
            name=voice_info["name"],
            ssml_gender=gender_map.get(voice_info["gender"], texttospeech.SsmlVoiceGender.FEMALE),
        )
        fmt_map = {
            "MP3": texttospeech.AudioEncoding.MP3,
            "LINEAR16": texttospeech.AudioEncoding.LINEAR16,
        }
        audio_config = texttospeech.AudioConfig(
            audio_encoding=fmt_map.get(audio_format, texttospeech.AudioEncoding.MP3),
            speaking_rate=speaking_rate,
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content

    except Exception as exc:
        logger.error(f"TTS error: {exc}")
        return b""
