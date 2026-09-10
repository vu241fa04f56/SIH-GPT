"""
translation_service.py
──────────────────────
Multilingual translation for WeatherGPT responses.

Primary: Google Cloud Translation API
Fallback: Gemini LLM translation (no extra credentials needed if GEMINI_API_KEY set)

Supported languages:
  hi (Hindi), bn (Bengali), te (Telugu), mr (Marathi), ta (Tamil),
  gu (Gujarati), ur (Urdu), kn (Kannada), ml (Malayalam), pa (Punjabi),
  en (English — passthrough)
"""

from __future__ import annotations

import os

from loguru import logger

SUPPORTED_LANGUAGES = {
    "en": "English", "hi": "Hindi", "bn": "Bengali", "te": "Telugu",
    "mr": "Marathi", "ta": "Tamil", "gu": "Gujarati", "ur": "Urdu",
    "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi",
}


async def translate_text(text: str, target_lang: str, source_lang: str = "en") -> str:
    """
    Translate text to target_lang.

    Falls back gracefully:
      1. Google Cloud Translation API (if credentials available)
      2. Gemini LLM translation (if GEMINI_API_KEY set)
      3. Returns original text with a language note
    """
    if target_lang == source_lang or target_lang == "en":
        return text

    if target_lang not in SUPPORTED_LANGUAGES:
        logger.warning(f"Unsupported language '{target_lang}'. Returning original.")
        return text

    # ── Try Google Cloud Translation ──────────────────────────────────────────
    gcp_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if gcp_creds and os.path.exists(gcp_creds):
        try:
            from google.cloud import translate_v2 as gc_translate
            client = gc_translate.Client()
            result = client.translate(text, target_language=target_lang, source_language=source_lang)
            return result["translatedText"]
        except Exception as exc:
            logger.warning(f"Google Translate failed: {exc}. Falling back to Gemini.")

    # ── Gemini fallback ────────────────────────────────────────────────────────
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
            prompt = (
                f"Translate the following text from English to {lang_name}. "
                f"Return ONLY the translated text, no explanation.\n\n{text}"
            )
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            logger.error(f"Gemini translation failed: {exc}")

    # ── Final fallback ─────────────────────────────────────────────────────────
    logger.warning("All translation methods failed. Returning English text.")
    return text


async def detect_language(text: str) -> str:
    """
    Detect the language of input text.
    Returns ISO 639-1 language code (e.g. 'hi', 'en').
    """
    gcp_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if gcp_creds and os.path.exists(gcp_creds):
        try:
            from google.cloud import translate_v2 as gc_translate
            client = gc_translate.Client()
            result = client.detect_language(text)
            return result.get("language", "en")
        except Exception:
            pass

    # Heuristic: check for Devanagari script
    if any("\u0900" <= ch <= "\u097F" for ch in text):
        return "hi"

    return "en"  # default to English
