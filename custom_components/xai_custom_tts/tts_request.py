"""Pure helpers for xAI unary TTS requests (no Home Assistant imports)."""

from __future__ import annotations

import json
import logging
from typing import Any

from .const import (
    DEFAULT_BIT_RATE,
    DEFAULT_CODEC,
    DEFAULT_LANGUAGE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_SPEED,
    DEFAULT_VOICE,
    MAX_TTS_TEXT_CHARS,
    SPEED_MAX,
    SPEED_MIN,
    SUPPORT_BIT_RATES,
    SUPPORT_CODECS,
    SUPPORT_SAMPLE_RATES,
)

_LOGGER = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}

# replace map limits from TTS docs
_REPLACE_MAX_ENTRIES = 200
_REPLACE_MAX_KEY_CHARS = 100
_REPLACE_MAX_VALUE_CHARS = 128


def coerce_bool(value: Any, default: bool = False) -> bool:
    """Coerce HA/YAML option values to bool."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _TRUE_VALUES:
            return True
        if lowered in _FALSE_VALUES:
            return False
    return default


def coerce_float(value: Any) -> float | None:
    """Coerce a numeric option; return None if missing/invalid."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def coerce_int(value: Any) -> int | None:
    """Coerce an integer option; return None if missing/invalid."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def normalize_voice_id(voice_id: Any, default: str = DEFAULT_VOICE) -> str:
    """Return a non-empty voice_id. Unknown IDs are passed through (custom voices)."""
    if voice_id is None:
        return default
    text = str(voice_id).strip()
    return text or default


def resolve_codec(codec: Any) -> str:
    """Validate codec against the documented set."""
    if codec is None or str(codec).strip() not in SUPPORT_CODECS:
        if codec is not None and str(codec).strip() not in SUPPORT_CODECS:
            _LOGGER.warning("Invalid codec '%s', using default '%s'", codec, DEFAULT_CODEC)
        return DEFAULT_CODEC
    return str(codec).strip()


def resolve_sample_rate(sample_rate: Any) -> int:
    """Validate sample rate against the documented set."""
    value = coerce_int(sample_rate)
    if value not in SUPPORT_SAMPLE_RATES:
        _LOGGER.warning(
            "Invalid sample_rate '%s', using default '%s'", sample_rate, DEFAULT_SAMPLE_RATE
        )
        return DEFAULT_SAMPLE_RATE
    return value


def resolve_bit_rate(bit_rate: Any, codec: str) -> int:
    """Validate MP3 bit rate; ignored by caller for non-MP3 codecs."""
    value = coerce_int(bit_rate)
    if codec == "mp3" and value not in SUPPORT_BIT_RATES:
        _LOGGER.warning("Invalid bit_rate '%s', using default '%s'", bit_rate, DEFAULT_BIT_RATE)
        return DEFAULT_BIT_RATE
    return value if value is not None else DEFAULT_BIT_RATE


def resolve_speed(speed: Any) -> float:
    """Clamp/default speech speed to the documented 0.7–1.5 range."""
    value = coerce_float(speed)
    if value is None:
        return DEFAULT_SPEED
    if value < SPEED_MIN or value > SPEED_MAX:
        _LOGGER.warning(
            "Invalid speed '%s' (allowed %.1f–%.1f), using default '%s'",
            speed,
            SPEED_MIN,
            SPEED_MAX,
            DEFAULT_SPEED,
        )
        return DEFAULT_SPEED
    return value


def parse_replace(value: Any) -> dict[str, str] | None:
    """Parse a pronunciation `replace` map from a dict or JSON object string."""
    if value is None or value == "" or value == {}:
        return None
    parsed: Any = value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as err:
            raise ValueError(f"replace must be a JSON object: {err}") from err
    if not isinstance(parsed, dict):
        raise ValueError("replace must be a mapping of phrase -> pronunciation")
    if len(parsed) > _REPLACE_MAX_ENTRIES:
        raise ValueError(f"replace has too many entries (max {_REPLACE_MAX_ENTRIES})")

    result: dict[str, str] = {}
    for key, replacement in parsed.items():
        key_text = str(key)
        value_text = str(replacement)
        if not key_text.strip():
            raise ValueError("replace keys must not be blank")
        if len(key_text) > _REPLACE_MAX_KEY_CHARS:
            raise ValueError(f'replace key "{key_text}" is too long')
        if len(value_text) > _REPLACE_MAX_VALUE_CHARS:
            raise ValueError(f'replace value for "{key_text}" is too long')
        result[key_text] = value_text
    return result or None


def validate_text(text: str) -> str:
    """Validate unary TTS text length (60,000 characters)."""
    if not text or not str(text).strip():
        raise ValueError("text is empty")
    if len(text) > MAX_TTS_TEXT_CHARS:
        raise ValueError(
            f"text is {len(text)} characters; unary TTS limit is {MAX_TTS_TEXT_CHARS}"
        )
    return text


def build_tts_payload(
    *,
    text: str,
    voice_id: str,
    language: str,
    codec: str,
    sample_rate: int,
    bit_rate: int | None = None,
    speed: float | None = None,
    text_normalization: bool | None = None,
    replace: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a POST /v1/tts JSON body matching current xAI docs."""
    payload: dict[str, Any] = {
        "text": text,
        "voice_id": voice_id,
        "language": language or DEFAULT_LANGUAGE,
        "output_format": {
            "codec": codec,
            "sample_rate": sample_rate,
        },
    }
    if codec == "mp3" and bit_rate is not None:
        payload["output_format"]["bit_rate"] = bit_rate
    if speed is not None:
        payload["speed"] = speed
    if text_normalization is not None:
        payload["text_normalization"] = bool(text_normalization)
    if replace:
        payload["replace"] = replace
    return payload


def describe_http_error(status_code: int, body: str = "") -> str:
    """Map documented TTS HTTP statuses to a log line."""
    snippet = (body or "").strip()
    if len(snippet) > 500:
        snippet = snippet[:500] + "…"
    detail = f" — {snippet}" if snippet else ""

    if status_code == 400:
        return (
            "Bad request (400): check text is non-empty and under "
            f"{MAX_TTS_TEXT_CHARS} characters, and that codec/sample rate/"
            f"replace are valid{detail}"
        )
    if status_code == 401:
        return f"Unauthorized (401): API key is missing or invalid{detail}"
    if status_code == 404:
        return (
            "Unknown voice_id (404): verify via GET /v1/tts/voices (built-in) "
            f"or GET /v1/custom-voices (custom){detail}"
        )
    if status_code == 429:
        return f"Rate limited (429): backing off before retry{detail}"
    if status_code == 503:
        return f"TTS service unavailable (503): backing off before retry{detail}"
    if status_code == 500:
        return f"Server error (500): backing off before retry{detail}"
    return f"xAI TTS HTTP {status_code}{detail}"
