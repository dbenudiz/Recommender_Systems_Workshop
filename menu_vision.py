# pip install google-genai python-dotenv
"""
menu_vision.py — Extract beer names and breweries from a menu image via Gemini vision.
Uses google-genai SDK (not the deprecated google-generativeai package).

Setup: put GOOGLE_API_KEY=your-key in a .env file in the project root (see .env.example).
Free tier: 500 requests/day on gemini-2.5-flash-lite (aistudio.google.com).
"""

import json
import logging
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

# Models tried in order on 503 overload — only models with confirmed free-tier quota.
_MODELS = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]

# Singleton client — created once on first call, reused for every request.
_CLIENT: genai.Client | None = None

_PROMPT = (
    "Look at this bar or restaurant menu image. Extract every beer you can see listed.\n"
    "For each beer, return the beer name and brewery name (if visible).\n"
    "Respond ONLY with a JSON array, no other text. Format:\n"
    '[{"name": "beer name", "brewery": "brewery name or null"}, ...]\n'
    "If no beers are visible, return []."
)


def _get_client() -> "genai.Client | None":
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.warning(
            "GOOGLE_API_KEY is not set — menu scanning is disabled. "
            "Copy .env.example to .env and fill in your key."
        )
        return None
    _CLIENT = genai.Client(api_key=api_key)
    logger.info("Gemini client initialised (primary model: %s)", _MODELS[0])
    return _CLIENT


def _detect_mime(image_bytes: bytes) -> str:
    if image_bytes[:4] == b"\x89PNG":
        return "image/png"
    if image_bytes[:3] == b"GIF":
        return "image/gif"
    if image_bytes[:4] == b"RIFF":
        return "image/webp"
    return "image/jpeg"


def _parse_response(text: str) -> list:
    """Strip optional markdown code fences and parse JSON."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening fence (```json or ```) and closing fence (```)
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    return json.loads(text)


def extract_beers_from_image(image_bytes: bytes) -> list[dict]:
    """
    Send a menu image to Gemini vision and extract beer names + breweries.
    Returns [{"name": str, "brewery": str | None}, ...], or [] on any error.
    Retries once on 503 (transient server overload) before giving up.
    """
    client = _get_client()
    if client is None:
        return []

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=_detect_mime(image_bytes),
    )

    for model in _MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=[image_part, _PROMPT],
            )
            text = response.text.strip()

            if not text:
                logger.warning("Gemini returned an empty response.")
                return []

            beers = _parse_response(text)

            if not isinstance(beers, list):
                logger.warning("Gemini response was not a JSON array: %r", text)
                return []

            logger.warning("Menu scan succeeded with model: %s", model)
            return [
                {"name": item["name"], "brewery": item.get("brewery")}
                for item in beers
                if isinstance(item, dict) and "name" in item
            ]

        except json.JSONDecodeError as exc:
            logger.warning("Could not parse Gemini response as JSON: %s", exc)
            return []

        except Exception as exc:
            err = str(exc)
            if "503" in err:
                logger.warning("Gemini 503 on model %s — trying next fallback.", model)
                time.sleep(2)
                continue
            if "429" in err and "limit: 0" in err:
                logger.warning("Gemini quota unavailable for model %s — trying next.", model)
                continue
            logger.warning("Gemini API error on model %s: %s", model, exc)
            return []

    logger.warning("All Gemini models failed — returning empty extraction.")
    return []
