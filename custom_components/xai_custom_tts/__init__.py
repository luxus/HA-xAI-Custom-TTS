"""The xAI Custom TTS integration."""

from __future__ import annotations

import logging

import httpx

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    DOMAIN,
    SERVICE_GET_VOICES,
    XAI_VOICES,
    ATTR_SEARCH_TEXT,
    XAI_TTS_URL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up xAI Custom TTS from a config entry."""
    
    # Store the API key in hass.data for use by platforms
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api_key": entry.data[CONF_API_KEY],
    }
    
    # Set up TTS platform
    await hass.config_entries.async_forward_entry_setups(entry, ["tts"])
    
    # Register services
    await _async_register_services(hass, entry.data[CONF_API_KEY])
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload TTS platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["tts"])
    
    hass.data[DOMAIN].pop(entry.entry_id, None)
    
    # Unregister services if this is the last entry
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_GET_VOICES)
    
    return unload_ok


async def _async_register_services(hass: HomeAssistant, api_key: str) -> None:
    """Register the services."""
    
    async def get_voices_service(call: ServiceCall) -> ServiceResponse:
        """Service to get all available voices with optional filtering."""
        search_text = call.data.get(ATTR_SEARCH_TEXT, "").lower().strip()
        
        voices_list = []
        
        for voice_id, voice_info in XAI_VOICES.items():
            voice_data = {
                "voice_id": voice_id,
                "name": voice_info["name"],
                "type": voice_info["type"],
                "tone": voice_info["tone"],
                "description": voice_info["description"],
            }
            
            # Apply search text filter
            if search_text:
                searchable_text = f"{voice_info['name'].lower()} {voice_info['type'].lower()} {voice_info['tone'].lower()} {voice_info['description'].lower()}"
                
                if search_text not in searchable_text:
                    continue
            
            voices_list.append(voice_data)
        
        return {"voices": voices_list}

    # Register the services
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_VOICES,
        get_voices_service,
        supports_response=SupportsResponse.ONLY,
    )
