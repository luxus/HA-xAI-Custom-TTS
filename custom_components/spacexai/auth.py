"""OAuth / API-key helpers. No Home Assistant imports (unit-testable)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ha_spacexai_auth import (
    SpaceXaiAuthError,
    TokenSet,
    authorization_headers,
    ensure_fresh,
    token_data_updates,
)

from .const import (
    AUTH_API_KEY,
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_AUTH_METHOD,
    TOKEN_EXPIRY_SKEW_SECONDS,
)

TimeFn = Callable[[], float]


def entry_auth_method(entry_data: Mapping[str, Any]) -> str:
    """Return ``oauth`` or ``api_key`` from config-entry data."""
    method = entry_data.get(CONF_AUTH_METHOD)
    if method in {AUTH_API_KEY, "oauth"}:
        return str(method)
    if entry_data.get(CONF_API_KEY) and not entry_data.get(CONF_ACCESS_TOKEN):
        return AUTH_API_KEY
    return "oauth"


def authorization_headers_for_entry(entry_data: Mapping[str, Any]) -> dict[str, str]:
    """Bearer headers from stored OAuth access token or API key."""
    if entry_auth_method(entry_data) == AUTH_API_KEY:
        key = entry_data.get(CONF_API_KEY)
        if not key:
            raise SpaceXaiAuthError("API key missing")
        return authorization_headers(str(key))
    token = entry_data.get(CONF_ACCESS_TOKEN)
    if not token:
        raise SpaceXaiAuthError("Grok OAuth tokens missing")
    return authorization_headers(str(token))


async def ensure_entry_tokens(
    session: Any,
    entry_data: Mapping[str, Any],
    *,
    time_fn: TimeFn | None = None,
) -> dict[str, Any] | None:
    """Run ``ensure_fresh``; return token-field updates or ``None``.

    Missing ``access_token`` is an auth failure. Missing/invalid
    ``expires_at`` skips refresh (package ``ensure_fresh`` contract).
    API-key entries are a no-op.
    """
    if entry_auth_method(entry_data) == AUTH_API_KEY:
        return None
    if not entry_data.get(CONF_ACCESS_TOKEN):
        raise SpaceXaiAuthError("Grok OAuth tokens missing")
    try:
        tokens = TokenSet.from_entry_data(entry_data)
    except SpaceXaiAuthError:
        return None
    fresh = await ensure_fresh(
        session,
        tokens,
        skew_seconds=TOKEN_EXPIRY_SKEW_SECONDS,
        time_fn=time_fn,
    )
    updates = token_data_updates(fresh)
    if all(entry_data.get(key) == value for key, value in updates.items()):
        return None
    return updates
