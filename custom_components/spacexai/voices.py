"""Fetch and normalize xAI built-in + custom voice lists (no Home Assistant imports)."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Protocol

from .const import (
    XAI_ADDITIONAL_VOICES,
    XAI_CUSTOM_VOICES_URL,
    XAI_VOICES,
    XAI_VOICES_URL,
)

_LOGGER = logging.getLogger(__name__)

_VOICE_FETCH_TIMEOUT = 10.0


class _AsyncHttpClient(Protocol):
    """Subset of httpx.AsyncClient used to list voices."""

    async def get(self, *args: Any, **kwargs: Any) -> Any: ...


def fallback_voices() -> dict[str, dict[str, Any]]:
    """Offline fallback: original five plus documented extra built-in IDs."""
    voices: dict[str, dict[str, Any]] = {}
    for voice_id, info in XAI_VOICES.items():
        voices[voice_id] = {
            **info,
            "language": "en",
            "source": "builtin",
        }
    for voice_id, name in XAI_ADDITIONAL_VOICES.items():
        if voice_id in voices:
            continue
        voices[voice_id] = {
            "name": name,
            "type": "",
            "tone": "",
            "description": f"xAI voice: {name}",
            "language": "en",
            "source": "builtin",
        }
    return voices


def parse_builtin_voices(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Parse GET /v1/tts/voices `{voices: [{voice_id, name, language?}]}`."""
    voices: dict[str, dict[str, Any]] = {}
    for voice in data.get("voices") or []:
        if not isinstance(voice, dict):
            continue
        voice_id = str(voice.get("voice_id") or "").strip()
        if not voice_id:
            continue
        name = str(voice.get("name") or voice_id).strip() or voice_id
        cached = XAI_VOICES.get(voice_id.lower(), {})
        voices[voice_id] = {
            "name": name,
            "type": cached.get("type", ""),
            "tone": cached.get("tone", ""),
            "description": cached.get("description") or f"xAI voice: {name}",
            "language": voice.get("language") or "",
            "source": "builtin",
        }
    return voices


def parse_custom_voices(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Parse GET /v1/custom-voices `{voices: [{voice_id, name, ...}]}`."""
    voices: dict[str, dict[str, Any]] = {}
    for voice in data.get("voices") or []:
        if not isinstance(voice, dict):
            continue
        voice_id = str(voice.get("voice_id") or "").strip()
        if not voice_id:
            continue
        name = str(voice.get("name") or voice_id).strip() or voice_id
        gender = str(voice.get("gender") or "").strip()
        tone = str(voice.get("tone") or "").strip()
        description = str(voice.get("description") or "").strip()
        voices[voice_id] = {
            "name": name,
            "type": gender.title() if gender else "Custom",
            "tone": tone,
            "description": description or f"Custom voice: {name}",
            "language": voice.get("language") or "",
            "source": "custom",
        }
    return voices


def format_voice_label(voice_id: str, info: dict[str, Any]) -> str:
    """Human-readable dropdown label for a voice."""
    name = info.get("name") or voice_id
    extras: list[str] = []
    kind = info.get("type") or ""
    if kind and kind != "Unknown":
        extras.append(kind)
    if info.get("tone"):
        extras.append(str(info["tone"]))
    if info.get("source") == "custom":
        extras.append("custom")
    if extras:
        return f"{name} ({', '.join(extras)})"
    return str(name)


async def fetch_all_voices(
    client: _AsyncHttpClient, headers: Mapping[str, str]
) -> dict[str, dict[str, Any]]:
    """Fetch built-in voices, then custom voices. Fall back if the built-in list fails.

    ``headers`` must already be ``Authorization: Bearer …`` from
    ``runtime.async_authorization_headers`` / ``authorization_headers_for_entry``.
    """
    voices: dict[str, dict[str, Any]] = {}

    try:
        response = await client.get(
            XAI_VOICES_URL, headers=headers, timeout=_VOICE_FETCH_TIMEOUT
        )
        response.raise_for_status()
        voices.update(parse_builtin_voices(response.json()))
    except Exception as err:  # noqa: BLE001 — any failure should use the cache
        _LOGGER.warning(
            "Failed to fetch voices from xAI API: %s. Using cached defaults.", err
        )
        voices.update(fallback_voices())

    if not voices:
        voices.update(fallback_voices())

    try:
        response = await client.get(
            XAI_CUSTOM_VOICES_URL,
            headers=headers,
            params={"limit": 1000},
            timeout=_VOICE_FETCH_TIMEOUT,
        )
        if response.status_code == 403:
            _LOGGER.debug("Custom voices list not enabled for this API key/team")
        elif response.status_code == 401:
            _LOGGER.debug("Custom voices list unauthorized")
        else:
            response.raise_for_status()
            voices.update(parse_custom_voices(response.json()))
    except Exception as err:  # noqa: BLE001 — custom voices are optional
        _LOGGER.debug("Failed to fetch custom voices: %s", err)

    return voices
