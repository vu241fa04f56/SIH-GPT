"""
llm_engine.py
─────────────
Gemini-powered chatbot engine with function-calling (tool use).

The LLM is given a set of tools that call the WeatherGPT backend APIs.
It never invents weather numbers — it calls the tools and uses the results.

Usage:
    chatbot = WeatherGPTChatbot()
    response = await chatbot.chat(
        message="What is the weather in Mumbai?",
        language="en",
        user_lat=19.07, user_lon=72.87,
    )
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import google.generativeai as genai
import httpx
from loguru import logger

from chatbot.intent_parser import extract_city_and_intent
from chatbot.tool_functions import TOOL_DECLARATIONS, execute_tool

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"
GUIDANCE_DIR = Path(__file__).parent / "prompts" / "disaster_guidance_templates"

BACKEND_BASE_URL = os.getenv("VITE_API_URL", "http://localhost:8000")


class WeatherGPTChatbot:
    """
    Stateless chatbot engine. Each call to `chat()` runs a complete
    Gemini function-calling cycle and returns the final response.

    For multi-turn support, pass `history` (list of Content objects) in.
    """

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set — chatbot will use stub responses.")
        genai.configure(api_key=api_key)

        self._model = genai.GenerativeModel(
            model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
            system_instruction=self._load_system_prompt(),
            tools=TOOL_DECLARATIONS,
        )

    def _load_system_prompt(self) -> str:
        if SYSTEM_PROMPT_PATH.exists():
            return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        return (
            "You are WeatherGPT, an AI assistant specializing in Indian weather, "
            "disaster early warnings, and agricultural advisories. "
            "Always use the provided tools to fetch real data before responding."
        )

    def _load_disaster_guidance(self, disaster_type: str) -> str | None:
        path = GUIDANCE_DIR / f"{disaster_type}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    async def chat(
        self,
        message: str,
        language: str = "en",
        user_lat: float | None = None,
        user_lon: float | None = None,
        history: list | None = None,
    ) -> dict:
        """
        Run a full Gemini function-calling cycle.

        Returns a dict with keys:
            reply         : str — final text response
            intent        : str | None
            city_name     : str | None
            disaster_alert: dict | None
        """
        # Parse intent and city from user message
        parsed = await extract_city_and_intent(message, user_lat, user_lon)
        intent = parsed.get("intent")
        city_name = parsed.get("city_name")

        # If no Gemini key, return a stub
        if not os.getenv("GEMINI_API_KEY"):
            return self._stub_response(message, intent, city_name)

        try:
            chat_session = self._model.start_chat(history=history or [])
            response = chat_session.send_message(message)

            # ── Agentic function-calling loop ─────────────────────────────────
            max_iterations = 5
            for _ in range(max_iterations):
                if not response.candidates:
                    break
                part = response.candidates[0].content.parts[0]

                if hasattr(part, "function_call") and part.function_call:
                    fn_call = part.function_call
                    tool_name = fn_call.name
                    tool_args = dict(fn_call.args)

                    logger.debug(f"Tool call: {tool_name}({tool_args})")
                    tool_result = await execute_tool(tool_name, tool_args)

                    # Check if disaster type returned — load vetted guidance
                    disaster_alert = None
                    if isinstance(tool_result, dict):
                        dt = tool_result.get("disaster_type", "none")
                        if dt and dt != "none" and tool_result.get("risk_score", 0) > 0.5:
                            guidance = self._load_disaster_guidance(dt)
                            if guidance:
                                tool_result["official_guidance"] = guidance
                            disaster_alert = tool_result

                    # Feed result back to the model
                    response = chat_session.send_message(
                        genai.protos.Content(
                            role="tool",
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=tool_name,
                                    response={"result": json.dumps(tool_result, default=str)},
                                )
                            )],
                        )
                    )
                else:
                    # Final text response
                    final_text = part.text if hasattr(part, "text") else str(part)
                    return {
                        "reply": final_text,
                        "intent": intent,
                        "city_name": city_name,
                        "disaster_alert": disaster_alert if "disaster_alert" in dir() else None,
                    }

            # Fallback if loop exhausted
            return {
                "reply": "I was unable to retrieve data at this moment. Please try again.",
                "intent": intent,
                "city_name": city_name,
                "disaster_alert": None,
            }

        except Exception as exc:
            logger.error(f"Gemini chat error: {exc}")
            return self._stub_response(message, intent, city_name)

    def _stub_response(self, message: str, intent: str | None, city_name: str | None) -> dict:
        city = city_name or "your location"
        return {
            "reply": (
                f"[Stub mode — set GEMINI_API_KEY to enable live responses] "
                f"You asked about {city}. I detected intent: {intent or 'general'}."
            ),
            "intent": intent,
            "city_name": city_name,
            "disaster_alert": None,
        }
