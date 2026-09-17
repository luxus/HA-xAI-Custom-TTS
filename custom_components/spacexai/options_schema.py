"""Options schema for conversation settings (models, tools, live search)."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
)
from homeassistant.helpers.typing import VolDictType

from .api_helpers import is_chat_model_id
from .const import (
    CONF_AUTO_MODEL_ROUTING,
    CONF_BUDGET_WARN_USD,
    CONF_CHAT_MODEL,
    CONF_FALLBACK_MODEL,
    CONF_FAST_MODEL,
    CONF_HOME_CONTEXT,
    CONF_INTERACTION_MODE,
    CONF_LIVE_SEARCH,
    CONF_LLM_HASS_API,
    CONF_LOCATION_CONTEXT,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_REASONING_EFFORT,
    CONF_RECOMMENDED,
    CONF_SEND_USER_NAME,
    CONF_SHOW_CITATIONS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_VOICE_OPTIMIZED,
    GROK_SYSTEM_PROMPT,
    MODE_CHAT_ONLY,
    MODE_PIPELINE,
    MODE_TOOLS,
    RECOMMENDED_AUTO_MODEL_ROUTING,
    RECOMMENDED_BUDGET_WARN_USD,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_FALLBACK_MODEL,
    RECOMMENDED_FAST_MODEL,
    RECOMMENDED_HOME_CONTEXT,
    RECOMMENDED_INTERACTION_MODE,
    RECOMMENDED_LIVE_SEARCH,
    RECOMMENDED_LLM_HASS_API,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_OPTIONS,
    RECOMMENDED_REASONING_EFFORT,
    RECOMMENDED_SEND_USER_NAME,
    RECOMMENDED_SHOW_CITATIONS,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_P,
    RECOMMENDED_VOICE_OPTIMIZED,
)

_LOGGER = logging.getLogger(__name__)


def fill_missing_options(options: Mapping[str, Any] | None) -> tuple[dict[str, Any], bool]:
    """Fill recommended conversation keys without clobbering existing options."""
    from .const import RECOMMENDED_OPTIONS

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


def resolve_llm_hass_api(hass: HomeAssistant, llm_hass_api: Any) -> tuple[list[str] | None, str | None]:
    """Normalize Assist API selection. Returns (list or None, error_key)."""
    if not llm_hass_api:
        return None, None
    try:
        from homeassistant.helpers import llm

        available_apis = list(llm.async_get_apis(hass))
        available_api_ids = {api.id for api in available_apis}
        available_by_name = {
            (api.name or "").strip().lower(): api.id for api in available_apis
        }
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Error getting available LLM APIs: %s", err)
        available_apis = []
        available_api_ids = set()
        available_by_name = {}

    if isinstance(llm_hass_api, str):
        api_list = [llm_hass_api]
    elif isinstance(llm_hass_api, list):
        api_list = list(llm_hass_api)
    else:
        api_list = []

    api_list = [a for a in api_list if a != "none"]
    resolved: list[str] = []
    for api_id in api_list:
        if api_id in available_api_ids:
            resolved.append(api_id)
            continue
        by_name = available_by_name.get(str(api_id).strip().lower())
        if by_name:
            resolved.append(by_name)
            continue
        key = str(api_id).strip().lower()
        if key in {"assist", "home assistant", "homeassistant"} and available_apis:
            pick = next(
                (
                    a.id
                    for a in available_apis
                    if "assist" in a.id.lower()
                    or "assist" in (a.name or "").lower()
                    or a.id == "homeassistant"
                ),
                available_apis[0].id,
            )
            resolved.append(pick)
            continue
        resolved.append(api_id)

    seen: set[str] = set()
    api_list = []
    for item in resolved:
        if item not in seen:
            seen.add(item)
            api_list.append(item)

    if not api_list:
        return None, None

    invalid = [api_id for api_id in api_list if api_id not in available_api_ids]
    if invalid and available_api_ids:
        api_list = [a for a in api_list if a in available_api_ids]
        if not api_list:
            return None, "llm_api_not_found"
    return api_list, None


def _model_select(
    models: list[str],
    current: str | None,
    default: str,
) -> SelectSelector:
    opts = list(models)
    cur = current or default
    if cur and cur not in opts:
        opts = [cur, *opts]
    if default not in opts:
        opts = [default, *opts]
    return SelectSelector(
        SelectSelectorConfig(
            options=[SelectOptionDict(value=m, label=m) for m in opts],
            mode=SelectSelectorMode.DROPDOWN,
            custom_value=True,
        )
    )


def conversation_option_schema(
    hass: HomeAssistant,
    options: dict[str, Any] | Mapping[str, Any],
    chat_models: list[str] | None = None,
) -> VolDictType:
    """Return a schema for Grok conversation options."""
    models = chat_models or [
        RECOMMENDED_CHAT_MODEL,
        RECOMMENDED_FAST_MODEL,
        RECOMMENDED_FALLBACK_MODEL,
    ]
    hass_apis: list[SelectOptionDict] = [
        SelectOptionDict(label="No control", value="none")
    ]
    try:
        from homeassistant.helpers import llm

        hass_apis.extend(
            SelectOptionDict(label=api.name, value=api.id) for api in llm.async_get_apis(hass)
        )
    except Exception:  # noqa: BLE001
        hass_apis.extend(
            [
                SelectOptionDict(label="Assist", value="assist"),
                SelectOptionDict(label="Home Assistant", value="homeassistant"),
            ]
        )

    live_search_opts = [
        SelectOptionDict(value="off", label="Off"),
        SelectOptionDict(value="web", label="Web Search"),
        SelectOptionDict(value="x", label="X Search"),
        SelectOptionDict(value="full", label="Full (Web + X)"),
    ]
    mode_opts = [
        SelectOptionDict(value=MODE_TOOLS, label="Tool Control (default)"),
        SelectOptionDict(
            value=MODE_PIPELINE, label="Intelligent Pipeline (HA intent → Grok)"
        ),
        SelectOptionDict(value=MODE_CHAT_ONLY, label="Chat Only (no device control)"),
    ]
    chat_default = options.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL)
    fast_default = options.get(CONF_FAST_MODEL, RECOMMENDED_FAST_MODEL)
    fallback_default = options.get(CONF_FALLBACK_MODEL, RECOMMENDED_FALLBACK_MODEL)
    llm_default = options.get(CONF_LLM_HASS_API, RECOMMENDED_LLM_HASS_API)

    schema: VolDictType = {
        vol.Optional(
            CONF_PROMPT,
            description={"suggested_value": options.get(CONF_PROMPT, GROK_SYSTEM_PROMPT)},
        ): TemplateSelector(),
        vol.Optional(
            CONF_CHAT_MODEL,
            description={"suggested_value": chat_default},
            default=chat_default,
        ): _model_select(models, chat_default, RECOMMENDED_CHAT_MODEL),
        vol.Optional(
            CONF_FAST_MODEL,
            description={"suggested_value": fast_default},
            default=fast_default,
        ): _model_select(models, fast_default, RECOMMENDED_FAST_MODEL),
        vol.Optional(
            CONF_FALLBACK_MODEL,
            description={"suggested_value": fallback_default},
            default=fallback_default,
        ): _model_select(models, fallback_default, RECOMMENDED_FALLBACK_MODEL),
        vol.Optional(
            CONF_LLM_HASS_API,
            description={"suggested_value": llm_default},
            default=llm_default,
        ): SelectSelector(SelectSelectorConfig(options=hass_apis, multiple=True)),
        vol.Optional(
            CONF_INTERACTION_MODE,
            description={
                "suggested_value": options.get(
                    CONF_INTERACTION_MODE, RECOMMENDED_INTERACTION_MODE
                )
            },
            default=options.get(CONF_INTERACTION_MODE, RECOMMENDED_INTERACTION_MODE),
        ): SelectSelector(
            SelectSelectorConfig(options=mode_opts, mode=SelectSelectorMode.DROPDOWN)
        ),
        vol.Optional(
            CONF_LIVE_SEARCH,
            description={
                "suggested_value": options.get(CONF_LIVE_SEARCH, RECOMMENDED_LIVE_SEARCH)
            },
            default=options.get(CONF_LIVE_SEARCH, RECOMMENDED_LIVE_SEARCH),
        ): SelectSelector(
            SelectSelectorConfig(options=live_search_opts, mode=SelectSelectorMode.DROPDOWN)
        ),
        vol.Optional(
            CONF_SHOW_CITATIONS,
            description={
                "suggested_value": options.get(
                    CONF_SHOW_CITATIONS, RECOMMENDED_SHOW_CITATIONS
                )
            },
            default=options.get(CONF_SHOW_CITATIONS, RECOMMENDED_SHOW_CITATIONS),
        ): bool,
        vol.Optional(
            CONF_SEND_USER_NAME,
            description={
                "suggested_value": options.get(
                    CONF_SEND_USER_NAME, RECOMMENDED_SEND_USER_NAME
                )
            },
            default=options.get(CONF_SEND_USER_NAME, RECOMMENDED_SEND_USER_NAME),
        ): bool,
        vol.Optional(
            CONF_LOCATION_CONTEXT,
            description={"suggested_value": options.get(CONF_LOCATION_CONTEXT, "")},
            default=options.get(CONF_LOCATION_CONTEXT, ""),
        ): TextSelector(TextSelectorConfig(type="text")),
        vol.Optional(
            CONF_VOICE_OPTIMIZED,
            description={
                "suggested_value": options.get(
                    CONF_VOICE_OPTIMIZED, RECOMMENDED_VOICE_OPTIMIZED
                )
            },
            default=options.get(CONF_VOICE_OPTIMIZED, RECOMMENDED_VOICE_OPTIMIZED),
        ): bool,
        vol.Optional(
            CONF_HOME_CONTEXT,
            description={
                "suggested_value": options.get(CONF_HOME_CONTEXT, RECOMMENDED_HOME_CONTEXT)
            },
            default=options.get(CONF_HOME_CONTEXT, RECOMMENDED_HOME_CONTEXT),
        ): bool,
        vol.Optional(
            CONF_AUTO_MODEL_ROUTING,
            description={
                "suggested_value": options.get(
                    CONF_AUTO_MODEL_ROUTING, RECOMMENDED_AUTO_MODEL_ROUTING
                )
            },
            default=options.get(CONF_AUTO_MODEL_ROUTING, RECOMMENDED_AUTO_MODEL_ROUTING),
        ): bool,
        vol.Required(
            CONF_RECOMMENDED, default=options.get(CONF_RECOMMENDED, True)
        ): bool,
    }

    if options.get(CONF_RECOMMENDED, True):
        return schema

    schema.update(
        {
            vol.Optional(
                CONF_MAX_TOKENS,
                description={"suggested_value": options.get(CONF_MAX_TOKENS)},
                default=options.get(CONF_MAX_TOKENS, RECOMMENDED_MAX_TOKENS),
            ): int,
            vol.Optional(
                CONF_TOP_P,
                description={"suggested_value": options.get(CONF_TOP_P)},
                default=options.get(CONF_TOP_P, RECOMMENDED_TOP_P),
            ): NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05)),
            vol.Optional(
                CONF_TEMPERATURE,
                description={"suggested_value": options.get(CONF_TEMPERATURE)},
                default=options.get(CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE),
            ): NumberSelector(NumberSelectorConfig(min=0, max=2, step=0.05)),
            vol.Optional(
                CONF_REASONING_EFFORT,
                description={"suggested_value": options.get(CONF_REASONING_EFFORT)},
                default=options.get(CONF_REASONING_EFFORT, RECOMMENDED_REASONING_EFFORT),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value="low", label="Low"),
                        SelectOptionDict(value="medium", label="Medium"),
                        SelectOptionDict(value="high", label="High"),
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_BUDGET_WARN_USD,
                description={
                    "suggested_value": options.get(
                        CONF_BUDGET_WARN_USD, RECOMMENDED_BUDGET_WARN_USD
                    )
                },
                default=options.get(CONF_BUDGET_WARN_USD, RECOMMENDED_BUDGET_WARN_USD),
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=10000, step=0.5, unit_of_measurement="USD")
            ),
        }
    )
    return schema


def validate_model_picks(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    for model_key in (CONF_CHAT_MODEL, CONF_FAST_MODEL, CONF_FALLBACK_MODEL):
        model_val = user_input.get(model_key)
        if not model_val:
            continue
        if not is_chat_model_id(str(model_val)):
            errors[model_key] = "model_not_supported"
    return errors
