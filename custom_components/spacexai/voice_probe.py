"""Voice API probe at setup (TTS/STT entitlement). Ported from grok_conversation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from .const import DEFAULT_VOICE, XAI_TTS_URL, XAI_VOICES_URL

_LOGGER = logging.getLogger(__name__)

_TIMEOUT_SHORT = 20.0
_TIMEOUT_TTS = 60.0


async def async_validate_voice_access(
    client: Any, headers: Mapping[str, str]
) -> tuple[bool, str]:
    """Check whether the current Bearer token can use xAI voice endpoints.

    Returns (ok, detail_message). Conversation still works if voice is denied.
    """
    try:
        response = await client.get(
            XAI_VOICES_URL, headers=dict(headers), timeout=_TIMEOUT_SHORT
        )
        status = getattr(response, "status_code", 0)
        if status == 200:
            return True, "Voice API accessible (voices list OK)"
        if status in (401, 403):
            text = getattr(response, "text", "") or ""
            return False, f"API key rejected for voice ({status}): {text[:200]}"
        _LOGGER.debug("Voices list returned %s, probing TTS", status)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Voices list failed: %s", err)

    try:
        response = await client.post(
            XAI_TTS_URL,
            headers={**dict(headers), "Content-Type": "application/json"},
            json={
                "text": "Hi",
                "voice_id": DEFAULT_VOICE,
                "language": "en",
                "output_format": {
                    "codec": "mp3",
                    "sample_rate": 24000,
                    "bit_rate": 64000,
                },
            },
            timeout=_TIMEOUT_TTS,
        )
        status = getattr(response, "status_code", 0)
        if status == 200:
            return True, "Voice API accessible (TTS probe OK)"
        text = getattr(response, "text", "") or ""
        if status in (401, 403):
            return (
                False,
                "This credential cannot access xAI Voice (TTS/STT). "
                "Enable Voice in the xAI console or use a key with voice permissions. "
                f"({status})",
            )
        return False, f"Voice probe failed ({status}): {str(text)[:240]}"
    except Exception as err:  # noqa: BLE001
        return False, f"Could not reach xAI Voice API: {err}"
