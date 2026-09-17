"""SpaceXAI umbrella: Grok conversation + xAI TTS on one config entry."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ha_spacexai_auth import (
    SpaceXaiAuthError,
    SpaceXaiAuthExpired,
    SpaceXaiEntitlementError,
)

from .auth import (
    authorization_headers_for_entry,
    ensure_entry_tokens,
    entry_auth_method,
)
from .const import (
    ATTR_SEARCH_TEXT,
    AUTH_OAUTH,
    CONF_API_KEY,
    DOMAIN,
    PLATFORMS,
    SERVICE_GET_VOICES,
    XAI_VOICES,
)
from .migrate import migrate_entry_data

_LOGGER = logging.getLogger(__name__)

try:
    from aiohttp import ClientError as _AiohttpClientError
except ImportError:  # pragma: no cover - aiohttp is provided by Home Assistant
    _AiohttpClientError = None

OAUTH_TRANSPORT_ERRORS: tuple[type[BaseException], ...]
if _AiohttpClientError is not None:
    OAUTH_TRANSPORT_ERRORS = (_AiohttpClientError, TimeoutError)
else:
    OAUTH_TRANSPORT_ERRORS = (TimeoutError, ConnectionError, OSError)


@dataclass
class SpaceXAIRuntime:
    """Per-entry runtime: shared auth for conversation + TTS."""

    hass: Any
    entry: Any
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def async_authorization_headers(self) -> dict[str, str]:
        """Refresh OAuth if needed, then return Bearer headers."""
        async with self._lock:
            await _async_refresh_if_oauth(self.hass, self.entry)
            return authorization_headers_for_entry(self.entry.data)


async def async_setup_entry(hass: Any, entry: Any) -> bool:
    """Set up SpaceXAI from a config entry."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    if entry_auth_method(entry.data) == AUTH_OAUTH:
        await _async_refresh_if_oauth(hass, entry)
    elif not entry.data.get(CONF_API_KEY):
        raise ConfigEntryAuthFailed("API key missing")

    runtime = SpaceXAIRuntime(hass=hass, entry=entry)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = runtime

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_register_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: Any, entry: Any) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN) and hass.services.has_service(DOMAIN, SERVICE_GET_VOICES):
            hass.services.async_remove(DOMAIN, SERVICE_GET_VOICES)
    return unloaded


async def async_migrate_entry(hass: Any, entry: Any) -> bool:
    """Migrate config entry from older versions (API-key-only → auth_method)."""
    new_data, version = migrate_entry_data(entry.data, entry.version)
    if version != entry.version or dict(entry.data) != new_data:
        hass.config_entries.async_update_entry(entry, data=new_data, version=version)
        _LOGGER.info("Migrated SpaceXAI config entry to version %s", version)
    return True


async def _async_reload(hass: Any, entry: Any) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_refresh_if_oauth(hass: Any, entry: Any) -> None:
    """ensure_fresh on setup/reload/API call; persist rotated refresh tokens."""
    from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    if entry_auth_method(entry.data) != AUTH_OAUTH:
        return

    session = async_get_clientsession(hass)
    try:
        updates = await ensure_entry_tokens(session, entry.data)
    except SpaceXaiAuthExpired as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except SpaceXaiEntitlementError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except SpaceXaiAuthError as err:
        if not entry.data.get("access_token"):
            raise ConfigEntryAuthFailed(str(err)) from err
        raise ConfigEntryNotReady(str(err)) from err
    except OAUTH_TRANSPORT_ERRORS as err:
        raise ConfigEntryNotReady("Could not refresh Grok OAuth tokens") from err
    if updates:
        hass.config_entries.async_update_entry(entry, data={**entry.data, **updates})
        _LOGGER.debug("Persisted Grok token refresh")


async def _async_register_services(hass: Any) -> None:
    """Register domain services once."""
    if hass.services.has_service(DOMAIN, SERVICE_GET_VOICES):
        return

    from homeassistant.core import ServiceCall, ServiceResponse, SupportsResponse

    async def get_voices_service(call: ServiceCall) -> ServiceResponse:
        search_text = str(call.data.get(ATTR_SEARCH_TEXT, "")).lower().strip()
        voices_list = []
        for voice_id, voice_info in XAI_VOICES.items():
            voice_data = {
                "voice_id": voice_id,
                "name": voice_info["name"],
                "type": voice_info["type"],
                "tone": voice_info["tone"],
                "description": voice_info["description"],
            }
            if search_text:
                searchable_text = (
                    f"{voice_info['name'].lower()} {voice_info['type'].lower()} "
                    f"{voice_info['tone'].lower()} {voice_info['description'].lower()}"
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


def grok_authorization_headers(entry_data: Mapping[str, Any]) -> dict[str, str]:
    """Bearer headers for Grok / TTS API calls from stored entry data."""
    return authorization_headers_for_entry(entry_data)
