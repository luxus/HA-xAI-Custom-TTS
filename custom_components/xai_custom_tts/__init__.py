"""The xAI Custom TTS integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers.httpx_client import get_async_client

from .const import ATTR_SEARCH_TEXT, DOMAIN, SERVICE_GET_VOICES
from .voices import fetch_all_voices

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up xAI Custom TTS from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api_key": entry.data[CONF_API_KEY],
    }

    await hass.config_entries.async_forward_entry_setups(entry, ["tts"])
    await _async_register_services(hass, entry.data[CONF_API_KEY])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["tts"])

    hass.data[DOMAIN].pop(entry.entry_id, None)

    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_GET_VOICES)

    return unload_ok


async def _async_register_services(hass: HomeAssistant, api_key: str) -> None:
    """Register the services."""

    async def get_voices_service(call: ServiceCall) -> ServiceResponse:
        """Return built-in + custom voices from the xAI API, with optional search."""
        search_text = call.data.get(ATTR_SEARCH_TEXT, "").lower().strip()
        client = get_async_client(hass)
        voices = await fetch_all_voices(client, api_key)

        voices_list = []
        for voice_id, voice_info in voices.items():
            voice_data = {
                "voice_id": voice_id,
                "name": voice_info.get("name", voice_id),
                "type": voice_info.get("type", ""),
                "tone": voice_info.get("tone", ""),
                "description": voice_info.get("description", ""),
                "language": voice_info.get("language", ""),
                "source": voice_info.get("source", "builtin"),
            }
            if search_text:
                searchable_text = " ".join(
                    str(voice_data[key]).lower()
                    for key in ("voice_id", "name", "type", "tone", "description", "source")
                )
                if search_text not in searchable_text:
                    continue
            voices_list.append(voice_data)

        return {"voices": voices_list}

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_VOICES,
        get_voices_service,
        supports_response=SupportsResponse.ONLY,
    )
