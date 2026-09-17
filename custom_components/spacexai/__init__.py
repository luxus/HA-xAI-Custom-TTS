"""SpaceXAI umbrella: Grok conversation + xAI TTS + STT on one config entry."""

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
    AUTH_OAUTH,
    CONF_API_KEY,
    DOMAIN,
    PLATFORMS,
    RECOMMENDED_OPTIONS,
)
from .migrate import migrate_entry_data
from .usage import UsageTracker
from .voice_probe import async_validate_voice_access

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


def fill_missing_options(options: Mapping[str, Any] | None) -> tuple[dict[str, Any], bool]:
    """Fill recommended conversation keys without clobbering existing options."""
    current = dict(options or {})
    changed = False
    for key, value in RECOMMENDED_OPTIONS.items():
        if key not in current:
            current[key] = list(value) if isinstance(value, list) else value
            changed = True
    if "voice_profiles" not in current:
        current["voice_profiles"] = {}
        changed = True
    return current, changed


@dataclass
class SpaceXAIRuntime:
    """Per-entry runtime: shared auth for conversation + TTS + STT."""

    hass: Any
    entry: Any
    usage: UsageTracker | None = None
    voice_ok: bool = True
    voice_detail: str = ""
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def async_authorization_headers(self) -> dict[str, str]:
        """Refresh OAuth if needed, then return Bearer headers."""
        async with self._lock:
            await _async_refresh_if_oauth(self.hass, self.entry)
            return authorization_headers_for_entry(self.entry.data)


async def async_setup_entry(hass: Any, entry: Any) -> bool:
    """Set up SpaceXAI from a config entry."""
    from homeassistant.exceptions import ConfigEntryAuthFailed
    from homeassistant.helpers.httpx_client import get_async_client

    if entry_auth_method(entry.data) == AUTH_OAUTH:
        await _async_refresh_if_oauth(hass, entry)
    elif not entry.data.get(CONF_API_KEY):
        raise ConfigEntryAuthFailed("API key missing")

    merged, options_changed = fill_missing_options(entry.options)
    if options_changed:
        hass.config_entries.async_update_entry(entry, options=merged)

    tracker = UsageTracker(hass, entry.entry_id)
    await tracker.async_load()

    runtime = SpaceXAIRuntime(hass=hass, entry=entry, usage=tracker)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = runtime

    try:
        headers = await runtime.async_authorization_headers()
        voice_ok, voice_detail = await async_validate_voice_access(
            get_async_client(hass), headers
        )
        runtime.voice_ok = voice_ok
        runtime.voice_detail = voice_detail
        if voice_ok:
            _LOGGER.info("xAI Voice API OK: %s", voice_detail)
        else:
            _LOGGER.warning(
                "xAI Voice API not available for this credential — TTS/STT engines "
                "may fail until voice is enabled. Detail: %s",
                voice_detail,
            )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Voice API probe skipped: %s", err)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    from .services import async_register_services

    await async_register_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: Any, entry: Any) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN):
            from .services import async_unregister_services

            async_unregister_services(hass)
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


def grok_authorization_headers(entry_data: Mapping[str, Any]) -> dict[str, str]:
    """Bearer headers for Grok / TTS / STT API calls from stored entry data."""
    return authorization_headers_for_entry(entry_data)
