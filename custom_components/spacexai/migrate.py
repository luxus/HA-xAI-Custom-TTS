"""Config-entry version migration (domain ``spacexai``)."""

from __future__ import annotations

from typing import Any, Mapping

from .const import (
    AUTH_API_KEY,
    AUTH_OAUTH,
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_AUTH_METHOD,
    CONFIG_VERSION,
)


def migrate_entry_data(
    data: Mapping[str, Any], version: int
) -> tuple[dict[str, Any], int]:
    """Upgrade stored entry data to ``CONFIG_VERSION``.

    v1 (legacy TTS-only / API key) → v2 (``auth_method`` + TokenSet keys).
    """
    new_data = dict(data)
    if version < 2:
        if CONF_AUTH_METHOD not in new_data:
            if new_data.get(CONF_API_KEY) and not new_data.get(CONF_ACCESS_TOKEN):
                new_data[CONF_AUTH_METHOD] = AUTH_API_KEY
            else:
                new_data[CONF_AUTH_METHOD] = AUTH_OAUTH
        version = CONFIG_VERSION
    return new_data, version
