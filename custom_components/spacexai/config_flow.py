"""Config flow: Grok OAuth (device code) first, API-key fallback, TTS voice profiles."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
import voluptuous as vol
from ha_spacexai_auth import (
    DeviceAuthorization,
    SpaceXaiAuthError,
    TokenSet,
    poll_device_token,
    request_device_code,
    token_data_updates,
)

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .auth import authorization_headers_for_entry
from .const import (
    AUTH_API_KEY,
    AUTH_OAUTH,
    CODEC_NAMES,
    CONF_API_KEY,
    CONF_AUTH_METHOD,
    CONF_OAUTH_RECOVERY,
    CONFIG_VERSION,
    DEFAULT_BIT_RATE,
    DEFAULT_CODEC,
    DEFAULT_LANGUAGE,
    DEFAULT_NAME,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_VOICE,
    DOMAIN,
    LANGUAGE_NAMES,
    OAUTH_RECOVERY_ABORT,
    OAUTH_RECOVERY_API_KEY,
    OAUTH_RECOVERY_RETRY,
    SUPPORT_CODECS,
    SUPPORT_LANGUAGES,
    XAI_VOICES,
    XAI_VOICES_URL,
)

_LOGGER = logging.getLogger(__name__)

try:
    from aiohttp import ClientError as _AiohttpClientError
except ImportError:  # pragma: no cover
    _AiohttpClientError = None

OAUTH_TRANSPORT_ERRORS: tuple[type[BaseException], ...]
if _AiohttpClientError is not None:
    OAUTH_TRANSPORT_ERRORS = (_AiohttpClientError, TimeoutError)
else:
    OAUTH_TRANSPORT_ERRORS = (TimeoutError, ConnectionError, OSError)

PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

AUTH_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[AUTH_OAUTH, AUTH_API_KEY],
        mode=SelectSelectorMode.LIST,
        translation_key="grok_auth_method",
    )
)

OAUTH_RECOVERY_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[OAUTH_RECOVERY_RETRY, OAUTH_RECOVERY_API_KEY, OAUTH_RECOVERY_ABORT],
        mode=SelectSelectorMode.LIST,
        translation_key="oauth_recovery",
    )
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AUTH_METHOD, default=AUTH_OAUTH): AUTH_SELECTOR,
    }
)

REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AUTH_METHOD, default=AUTH_OAUTH): AUTH_SELECTOR,
    }
)

API_KEY_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): PASSWORD})

OAUTH_FAILED_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_OAUTH_RECOVERY, default=OAUTH_RECOVERY_RETRY): OAUTH_RECOVERY_SELECTOR,
    }
)

PROFILE_NAME_KEY = "Profile Name"
VOICE_ID_KEY = "Voice"
LANGUAGE_KEY = "Language"
CODEC_KEY = "Audio Codec"
SAMPLE_RATE_KEY = "Sample Rate (Hz)"
BIT_RATE_KEY = "Bit Rate (bps, MP3 only)"


def _map_form_data_to_profile(user_input: dict[str, Any]) -> dict[str, Any]:
    """Map form data with friendly keys back to profile data with standard keys."""
    sample_rate = user_input.get(SAMPLE_RATE_KEY, str(DEFAULT_SAMPLE_RATE))
    bit_rate = user_input.get(BIT_RATE_KEY, str(DEFAULT_BIT_RATE))
    try:
        sample_rate = int(sample_rate)
    except (ValueError, TypeError):
        sample_rate = DEFAULT_SAMPLE_RATE
    try:
        bit_rate = int(bit_rate)
    except (ValueError, TypeError):
        bit_rate = DEFAULT_BIT_RATE
    return {
        "voice": user_input.get(VOICE_ID_KEY, DEFAULT_VOICE),
        "language": user_input.get(LANGUAGE_KEY, DEFAULT_LANGUAGE),
        "codec": user_input.get(CODEC_KEY, DEFAULT_CODEC),
        "sample_rate": sample_rate,
        "bit_rate": bit_rate,
    }


def _map_profile_to_form_data(profile_name: str, profile_data: dict[str, Any]) -> dict[str, Any]:
    """Map profile data with standard keys to form data with friendly keys."""
    sample_rate = profile_data.get("sample_rate", DEFAULT_SAMPLE_RATE)
    bit_rate = profile_data.get("bit_rate", DEFAULT_BIT_RATE)
    if isinstance(sample_rate, (int, float)):
        sample_rate = str(int(sample_rate))
    elif isinstance(sample_rate, str):
        sample_rate = str(int(sample_rate))
    if isinstance(bit_rate, (int, float)):
        bit_rate = str(int(bit_rate))
    elif isinstance(bit_rate, str):
        bit_rate = str(int(bit_rate))
    return {
        PROFILE_NAME_KEY: profile_name,
        VOICE_ID_KEY: profile_data.get("voice", DEFAULT_VOICE),
        LANGUAGE_KEY: profile_data.get("language", DEFAULT_LANGUAGE),
        CODEC_KEY: profile_data.get("codec", DEFAULT_CODEC),
        SAMPLE_RATE_KEY: sample_rate,
        BIT_RATE_KEY: bit_rate,
    }


async def validate_api_key(hass: HomeAssistant, api_key: str) -> bool:
    """Validate an xAI API key by listing TTS voices."""
    httpx_client = get_async_client(hass)
    try:
        response = await httpx_client.get(
            XAI_VOICES_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        return response.status_code == 200
    except httpx.HTTPStatusError as err:
        _LOGGER.debug("API key validation failed with status %s", err.response.status_code)
        return False
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("API key validation failed: %s", err)
        return False


async def fetch_xai_voices(hass: HomeAssistant, entry_data: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Fetch available voices from xAI API using stored auth."""
    httpx_client = get_async_client(hass)
    try:
        headers = authorization_headers_for_entry(entry_data)
        response = await httpx_client.get(XAI_VOICES_URL, headers=headers, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        voices: dict[str, dict[str, str]] = {}
        for voice in data.get("voices", []):
            voice_id = str(voice.get("voice_id", "")).lower()
            name = voice.get("name", voice_id)
            voices[voice_id] = {
                "name": name,
                "type": "Unknown",
                "tone": "",
                "description": f"xAI voice: {name}",
            }
        for voice_id, info in XAI_VOICES.items():
            if voice_id in voices:
                voices[voice_id].update(info)
        return voices or dict(XAI_VOICES)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Failed to fetch voices from xAI API: %s. Using cached defaults.", err)
        return dict(XAI_VOICES)


class SpaceXAIConfigFlow(ConfigFlow, domain=DOMAIN):
    """OAuth-first setup. Not Application Credentials. API key is fallback only."""

    VERSION = CONFIG_VERSION

    def __init__(self) -> None:
        self._device: DeviceAuthorization | None = None
        self._oauth_task: asyncio.Task[TokenSet] | None = None
        self._tokens: TokenSet | None = None
        self._oauth_error: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get options flow for TTS voice profiles."""
        return SpaceXAIOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose Grok OAuth (default) or API-key fallback."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            method = user_input.get(CONF_AUTH_METHOD, AUTH_OAUTH)
            if method == AUTH_API_KEY:
                return await self.async_step_api_key()
            return await self.async_step_oauth()

        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            description_placeholders={"api_url": "https://api.x.ai"},
        )

    async def async_step_oauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show Grok device-code URL + user code and poll the token endpoint."""
        session = async_get_clientsession(self.hass)

        if self._oauth_task is None:
            try:
                self._device = await request_device_code(session)
            except SpaceXaiAuthError as err:
                _LOGGER.warning("Grok device-code start failed: %s", err)
                self._oauth_error = err.error or "oauth_failed"
                return await self.async_step_oauth_failed()
            except OAUTH_TRANSPORT_ERRORS as err:
                _LOGGER.warning("Grok device-code start cannot connect: %s", err)
                self._oauth_error = "cannot_connect"
                return await self.async_step_oauth_failed()
            self._oauth_task = self.hass.async_create_task(
                poll_device_token(session, self._device)
            )
            return self._show_oauth_progress()

        if not self._oauth_task.done():
            return self._show_oauth_progress()

        try:
            self._tokens = self._oauth_task.result()
        except SpaceXaiAuthError as err:
            _LOGGER.warning("Grok OAuth poll failed: %s", err)
            self._oauth_error = err.error or "oauth_failed"
            return self.async_show_progress_done(next_step_id="oauth_failed")
        except OAUTH_TRANSPORT_ERRORS as err:
            _LOGGER.warning("Grok OAuth poll cannot connect: %s", err)
            self._oauth_error = "cannot_connect"
            return self.async_show_progress_done(next_step_id="oauth_failed")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Grok OAuth poll crashed")
            self._oauth_error = "oauth_failed"
            return self.async_show_progress_done(next_step_id="oauth_failed")
        return self.async_show_progress_done(next_step_id="oauth_done")

    def _show_oauth_progress(self) -> ConfigFlowResult:
        device = self._device
        assert device is not None
        return self.async_show_progress(
            step_id="oauth",
            progress_action="oauth_wait",
            description_placeholders={
                "url": device.verification_uri,
                "user_code": device.user_code,
            },
            progress_task=self._oauth_task,
        )

    async def async_step_oauth_done(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Persist access + refresh tokens in the config entry."""
        assert self._tokens is not None
        return self._create(
            {
                CONF_AUTH_METHOD: AUTH_OAUTH,
                **token_data_updates(self._tokens),
            }
        )

    def _reset_oauth(self) -> None:
        task = self._oauth_task
        if task is not None and not task.done():
            task.cancel()
        self._oauth_task = None
        self._device = None
        self._tokens = None
        self._oauth_error = None

    async def async_step_oauth_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """OAuth failed: retry OAuth, fall back to API key, or abort."""
        if user_input is not None:
            action = user_input.get(CONF_OAUTH_RECOVERY, OAUTH_RECOVERY_RETRY)
            if action == OAUTH_RECOVERY_API_KEY:
                return await self.async_step_api_key()
            if action == OAUTH_RECOVERY_ABORT:
                return self.async_abort(reason="oauth_failed")
            self._reset_oauth()
            return await self.async_step_oauth()
        errors: dict[str, str] = {}
        if self._oauth_error == "cannot_connect":
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="oauth_failed",
            data_schema=OAUTH_FAILED_SCHEMA,
            errors=errors,
            description_placeholders={"error": self._oauth_error or "oauth_failed"},
        )

    async def async_step_api_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Optional xAI API key when OAuth is unavailable (console.x.ai billing)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = str(user_input[CONF_API_KEY]).strip()
            if not api_key:
                errors[CONF_API_KEY] = "invalid_api_key"
            elif await validate_api_key(self.hass, api_key):
                return self._create(
                    {
                        CONF_AUTH_METHOD: AUTH_API_KEY,
                        CONF_API_KEY: api_key,
                    }
                )
            else:
                errors["base"] = "invalid_api_key"
        return self.async_show_form(
            step_id="api_key",
            data_schema=API_KEY_SCHEMA,
            errors=errors,
            description_placeholders={"api_url": "https://api.x.ai"},
        )

    def _create(self, data: dict[str, Any]) -> ConfigFlowResult:
        if self.source == "reauth":
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates=data,
            )
        return self.async_create_entry(
            title=DEFAULT_NAME,
            data=data,
            options={"voice_profiles": {}},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Re-run Grok OAuth (or API-key fallback) when tokens fail."""
        await self.async_set_unique_id(DOMAIN)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=REAUTH_SCHEMA,
            )
        method = user_input.get(CONF_AUTH_METHOD, AUTH_OAUTH)
        if method == AUTH_API_KEY:
            return await self.async_step_api_key()
        self._reset_oauth()
        return await self.async_step_oauth()


class SpaceXAIOptionsFlow(OptionsFlow):
    """Handle options flow for TTS voice profiles."""

    def __init__(self, config_entry: ConfigEntry | None = None) -> None:
        """Store the entry for HA versions that do not inject ``config_entry``."""
        super().__init__()
        if config_entry is not None:
            self._config_entry = config_entry

    def _entry(self) -> ConfigEntry:
        stored = getattr(self, "_config_entry", None)
        if stored is not None:
            return stored
        return self.config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage voice profiles."""
        if user_input is not None:
            if user_input.get("action") == "add_profile":
                return await self.async_step_add_profile()
            if user_input.get("action") == "modify_profile":
                return await self.async_step_modify_profile()
            if user_input.get("action") == "delete_profile":
                return await self.async_step_delete_profile()
            if user_input.get("action") == "done":
                return self.async_create_entry(title="", data=self._entry().options)

        current_profiles = self._entry().options.get("voice_profiles", {})
        profile_list = list(current_profiles.keys()) if current_profiles else ["No profiles configured"]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional("action"): vol.In(
                        {
                            "add_profile": "Add New Voice Profile",
                            "modify_profile": "Modify Existing Profile",
                            "delete_profile": "Delete Voice Profile",
                            "done": "Finish Configuration",
                        }
                    )
                }
            ),
            description_placeholders={
                "current_profiles": "\n".join(f"• {profile}" for profile in profile_list)
            },
        )

    def _voice_form_schema(
        self,
        voices: dict[str, dict[str, str]],
        defaults: dict[str, Any] | None = None,
        *,
        include_name: bool = True,
    ) -> vol.Schema:
        voice_options = {
            voice_id: f"{info['name']} ({info['type']}) - {info['tone']}"
            for voice_id, info in voices.items()
        }
        language_options = {lang: LANGUAGE_NAMES.get(lang, lang) for lang in SUPPORT_LANGUAGES}
        codec_options = {codec: CODEC_NAMES.get(codec, codec) for codec in SUPPORT_CODECS}
        defaults = defaults or {}
        fields: dict[Any, Any] = {}
        if include_name:
            name_default = defaults.get(PROFILE_NAME_KEY)
            if name_default is None:
                fields[vol.Required(PROFILE_NAME_KEY)] = str
            else:
                fields[vol.Required(PROFILE_NAME_KEY, default=name_default)] = str
        fields[vol.Required(VOICE_ID_KEY, default=defaults.get(VOICE_ID_KEY, DEFAULT_VOICE))] = vol.In(
            voice_options
        )
        fields[
            vol.Optional(LANGUAGE_KEY, default=defaults.get(LANGUAGE_KEY, DEFAULT_LANGUAGE))
        ] = vol.In(language_options)
        fields[vol.Optional(CODEC_KEY, default=defaults.get(CODEC_KEY, DEFAULT_CODEC))] = vol.In(
            codec_options
        )
        fields[
            vol.Optional(
                SAMPLE_RATE_KEY,
                default=str(defaults.get(SAMPLE_RATE_KEY, DEFAULT_SAMPLE_RATE)),
            )
        ] = vol.In(
            {
                "8000": "8000 Hz (Telephone quality)",
                "16000": "16000 Hz (Wideband)",
                "22050": "22050 Hz (Radio quality)",
                "24000": "24000 Hz (xAI default)",
                "44100": "44100 Hz (CD quality)",
                "48000": "48000 Hz (Professional)",
            }
        )
        fields[
            vol.Optional(BIT_RATE_KEY, default=str(defaults.get(BIT_RATE_KEY, DEFAULT_BIT_RATE)))
        ] = vol.In(
            {
                "32000": "32 kbps",
                "64000": "64 kbps",
                "96000": "96 kbps",
                "128000": "128 kbps (Default)",
                "192000": "192 kbps",
            }
        )
        return vol.Schema(fields)

    async def async_step_add_profile(self, user_input: dict[str, Any] | None = None):
        """Add a new voice profile."""
        errors: dict[str, str] = {}
        if user_input is not None:
            profile_name = user_input[PROFILE_NAME_KEY]
            current_profiles = self._entry().options.get("voice_profiles", {})
            if profile_name in current_profiles:
                errors["profile_name"] = "profile_exists"
            else:
                new_profile = _map_form_data_to_profile(user_input)
                updated_profiles = current_profiles.copy()
                updated_profiles[profile_name] = new_profile
                new_options = dict(self._entry().options)
                new_options["voice_profiles"] = updated_profiles
                return self.async_create_entry(title="", data=new_options)

        voices = await fetch_xai_voices(self.hass, dict(self._entry().data))
        return self.async_show_form(
            step_id="add_profile",
            data_schema=self._voice_form_schema(voices),
            errors=errors,
        )

    async def async_step_modify_profile(self, user_input: dict[str, Any] | None = None):
        """Modify an existing voice profile."""
        current_profiles = self._entry().options.get("voice_profiles", {})
        if not current_profiles:
            return await self.async_step_init()

        if user_input is not None and "selected_profile" in user_input:
            profile_name = user_input["selected_profile"]
            profile_data = current_profiles[profile_name]
            form_data = _map_profile_to_form_data(profile_name, profile_data)
            voices = await fetch_xai_voices(self.hass, dict(self._entry().data))
            return self.async_show_form(
                step_id="edit_profile",
                data_schema=self._voice_form_schema(voices, form_data),
            )

        return self.async_show_form(
            step_id="modify_profile",
            data_schema=vol.Schema(
                {vol.Required("selected_profile"): vol.In(list(current_profiles.keys()))}
            ),
        )

    async def async_step_edit_profile(self, user_input: dict[str, Any] | None = None):
        """Edit the selected profile."""
        errors: dict[str, str] = {}
        if user_input is not None:
            current_profiles = self._entry().options.get("voice_profiles", {})
            new_profile_name = user_input[PROFILE_NAME_KEY]
            new_voice_id = user_input[VOICE_ID_KEY]
            old_profile_name = None
            for name, data in current_profiles.items():
                if data.get("voice") == new_voice_id and name != new_profile_name:
                    old_profile_name = name
                    break
            if old_profile_name is None and new_profile_name in current_profiles:
                old_profile_name = new_profile_name
            if new_profile_name != old_profile_name and new_profile_name in current_profiles:
                errors["profile_name"] = "profile_exists"
            if not errors:
                updated_profile = _map_form_data_to_profile(user_input)
                updated_profiles = current_profiles.copy()
                if old_profile_name and old_profile_name != new_profile_name:
                    updated_profiles.pop(old_profile_name, None)
                updated_profiles[new_profile_name] = updated_profile
                new_options = dict(self._entry().options)
                new_options["voice_profiles"] = updated_profiles
                return self.async_create_entry(title="", data=new_options)
        return await self.async_step_modify_profile()

    async def async_step_delete_profile(self, user_input: dict[str, Any] | None = None):
        """Delete a voice profile."""
        current_profiles = self._entry().options.get("voice_profiles", {})
        if not current_profiles:
            return await self.async_step_init()
        if user_input is not None:
            profile_to_delete = user_input["profile_name"]
            updated_profiles = current_profiles.copy()
            updated_profiles.pop(profile_to_delete, None)
            new_options = dict(self._entry().options)
            new_options["voice_profiles"] = updated_profiles
            return self.async_create_entry(title="", data=new_options)
        return self.async_show_form(
            step_id="delete_profile",
            data_schema=vol.Schema(
                {vol.Required("profile_name"): vol.In(list(current_profiles.keys()))}
            ),
        )
