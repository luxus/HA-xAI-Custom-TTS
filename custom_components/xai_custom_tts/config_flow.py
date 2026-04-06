"""Config flow for xAI Custom TTS integration."""

from __future__ import annotations

import logging
from typing import Any

import httpx
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    DOMAIN,
    XAI_VOICES,
    XAI_VOICES_URL,
    XAI_TTS_URL,
    DEFAULT_VOICE,
    DEFAULT_LANGUAGE,
    DEFAULT_CODEC,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_BIT_RATE,
    SUPPORT_LANGUAGES,
    SUPPORT_CODECS,
    SUPPORT_SAMPLE_RATES,
    SUPPORT_BIT_RATES,
    LANGUAGE_NAMES,
    CODEC_NAMES,
)

# Schema field mappings for user-friendly labels
PROFILE_NAME_KEY = "Profile Name"
VOICE_ID_KEY = "Voice"
LANGUAGE_KEY = "Language"
CODEC_KEY = "Audio Codec"
SAMPLE_RATE_KEY = "Sample Rate (Hz)"
BIT_RATE_KEY = "Bit Rate (bps, MP3 only)"

_LOGGER = logging.getLogger(__name__)


def _map_form_data_to_profile(user_input: dict[str, Any]) -> dict[str, Any]:
    """Map form data with friendly keys back to profile data with standard keys."""
    return {
        "voice": user_input.get(VOICE_ID_KEY, DEFAULT_VOICE),
        "language": user_input.get(LANGUAGE_KEY, DEFAULT_LANGUAGE),
        "codec": user_input.get(CODEC_KEY, DEFAULT_CODEC),
        "sample_rate": user_input.get(SAMPLE_RATE_KEY, DEFAULT_SAMPLE_RATE),
        "bit_rate": user_input.get(BIT_RATE_KEY, DEFAULT_BIT_RATE),
    }


def _map_profile_to_form_data(profile_name: str, profile_data: dict[str, Any]) -> dict[str, Any]:
    """Map profile data with standard keys to form data with friendly keys."""
    return {
        PROFILE_NAME_KEY: profile_name,
        VOICE_ID_KEY: profile_data.get("voice", DEFAULT_VOICE),
        LANGUAGE_KEY: profile_data.get("language", DEFAULT_LANGUAGE),
        CODEC_KEY: profile_data.get("codec", DEFAULT_CODEC),
        SAMPLE_RATE_KEY: profile_data.get("sample_rate", DEFAULT_SAMPLE_RATE),
        BIT_RATE_KEY: profile_data.get("bit_rate", DEFAULT_BIT_RATE),
    }


USER_STEP_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


async def validate_api_key(hass: HomeAssistant, api_key: str) -> bool:
    """Validate the API key by testing it with xAI API."""
    httpx_client = get_async_client(hass)
    
    try:
        # Test by fetching voices list
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        response = await httpx_client.get(
            XAI_VOICES_URL,
            headers=headers,
            timeout=10.0,
        )
        
        # 200 OK means the key is valid
        return response.status_code == 200
    except httpx.HTTPStatusError as err:
        _LOGGER.debug("API key validation failed with status %s", err.response.status_code)
        return False
    except Exception as err:
        _LOGGER.debug("API key validation failed: %s", err)
        return False


async def fetch_xai_voices(hass: HomeAssistant, api_key: str) -> dict[str, dict[str, str]]:
    """Fetch available voices from xAI API."""
    httpx_client = get_async_client(hass)
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        response = await httpx_client.get(
            XAI_VOICES_URL,
            headers=headers,
            timeout=10.0,
        )
        
        response.raise_for_status()
        data = response.json()
        
        voices = {}
        for voice in data.get("voices", []):
            voice_id = voice.get("voice_id", "").lower()
            name = voice.get("name", voice_id)
            voices[voice_id] = {
                "name": name,
                "type": "Unknown",
                "tone": "",
                "description": f"xAI voice: {name}",
            }
        
        # Merge with cached defaults for known voices
        for voice_id, info in XAI_VOICES.items():
            if voice_id in voices:
                voices[voice_id].update(info)
        
        return voices
        
    except Exception as err:
        _LOGGER.warning("Failed to fetch voices from xAI API: %s. Using cached defaults.", err)
        return XAI_VOICES


class XAICustomTTSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for xAI Custom TTS."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow."""
        return XAIOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            
            # Check if API key is already configured
            await self.async_set_unique_id(api_key)
            self._abort_if_unique_id_configured()
            
            # Validate API key
            if await validate_api_key(self.hass, api_key):
                return self.async_create_entry(
                    title="xAI Custom TTS",
                    data=user_input,
                    options={"voice_profiles": {}},  # Initialize empty voice profiles
                )
            else:
                errors["base"] = "invalid_api_key"
                
        return self.async_show_form(
            step_id="user",
            data_schema=USER_STEP_SCHEMA,
            errors=errors,
        )


class XAIOptionsFlow(OptionsFlow):
    """Handle options flow for xAI Custom TTS."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        super().__init__()
        self._config_entry = config_entry

    @property
    def config_entry(self) -> ConfigEntry:
        """Return the config entry."""
        return self._config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage voice profiles."""
        if user_input is not None:
            if user_input.get("action") == "add_profile":
                return await self.async_step_add_profile()
            elif user_input.get("action") == "modify_profile":
                return await self.async_step_modify_profile()
            elif user_input.get("action") == "delete_profile":
                return await self.async_step_delete_profile()
            elif user_input.get("action") == "done":
                return self.async_create_entry(title="", data=self._config_entry.options)
        
        # Get current voice profiles
        current_profiles = self._config_entry.options.get("voice_profiles", {})
        profile_list = list(current_profiles.keys()) if current_profiles else ["No profiles configured"]
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("action"): vol.In({
                    "add_profile": "Add New Voice Profile",
                    "modify_profile": "Modify Existing Profile", 
                    "delete_profile": "Delete Voice Profile",
                    "done": "Finish Configuration"
                })
            }),
            description_placeholders={
                "current_profiles": "\n".join(f"• {profile}" for profile in profile_list)
            }
        )

    async def async_step_add_profile(self, user_input: dict[str, Any] | None = None):
        """Add a new voice profile."""
        errors = {}
        
        if user_input is not None:
            profile_name = user_input[PROFILE_NAME_KEY]
            
            # Check if profile already exists
            current_profiles = self._config_entry.options.get("voice_profiles", {})
            if profile_name in current_profiles:
                errors["profile_name"] = "profile_exists"
            else:
                # Create new profile from form data
                new_profile = _map_form_data_to_profile(user_input)
                
                # Update options
                updated_profiles = current_profiles.copy()
                updated_profiles[profile_name] = new_profile
                
                new_options = self._config_entry.options.copy()
                new_options["voice_profiles"] = updated_profiles
                
                return self.async_create_entry(title="", data=new_options)
        
        # Fetch voices from API for up-to-date list
        api_key = self._config_entry.data.get(CONF_API_KEY)
        voices = await fetch_xai_voices(self.hass, api_key)
        
        # Build voice options
        voice_options = {voice_id: f"{info['name']} ({info['type']}) - {info['tone']}" 
                        for voice_id, info in voices.items()}
        
        # Build language options with display names
        language_options = {lang: LANGUAGE_NAMES.get(lang, lang) for lang in SUPPORT_LANGUAGES}
        
        # Build codec options with display names
        codec_options = {codec: CODEC_NAMES.get(codec, codec) for codec in SUPPORT_CODECS}
        
        return self.async_show_form(
            step_id="add_profile",
            data_schema=vol.Schema({
                vol.Required(PROFILE_NAME_KEY): str,
                vol.Required(VOICE_ID_KEY, default=DEFAULT_VOICE): vol.In(voice_options),
                vol.Optional(LANGUAGE_KEY, default=DEFAULT_LANGUAGE): vol.In(language_options),
                vol.Optional(CODEC_KEY, default=DEFAULT_CODEC): vol.In(codec_options),
                vol.Optional(SAMPLE_RATE_KEY, default=DEFAULT_SAMPLE_RATE): vol.In({
                    8000: "8000 Hz (Telephone quality)",
                    16000: "16000 Hz (Wideband)",
                    22050: "22050 Hz (Radio quality)",
                    24000: "24000 Hz (xAI default)",
                    44100: "44100 Hz (CD quality)",
                    48000: "48000 Hz (Professional)",
                }),
                vol.Optional(BIT_RATE_KEY, default=DEFAULT_BIT_RATE): vol.In({
                    32000: "32 kbps",
                    64000: "64 kbps",
                    96000: "96 kbps",
                    128000: "128 kbps (Default)",
                    192000: "192 kbps",
                }),
            }),
            errors=errors,
        )

    async def async_step_modify_profile(self, user_input: dict[str, Any] | None = None):
        """Modify an existing voice profile."""
        current_profiles = self._config_entry.options.get("voice_profiles", {})
        
        if not current_profiles:
            # No profiles to modify, go back to main menu
            return await self.async_step_init()
        
        if user_input is not None:
            if "selected_profile" in user_input:
                # Profile selected, now show editing form
                profile_name = user_input["selected_profile"]
                profile_data = current_profiles[profile_name]
                form_data = _map_profile_to_form_data(profile_name, profile_data)
                
                # Fetch voices from API
                api_key = self._config_entry.data.get(CONF_API_KEY)
                voices = await fetch_xai_voices(self.hass, api_key)
                
                # Build options
                voice_options = {voice_id: f"{info['name']} ({info['type']}) - {info['tone']}" 
                                for voice_id, info in voices.items()}
                language_options = {lang: LANGUAGE_NAMES.get(lang, lang) for lang in SUPPORT_LANGUAGES}
                codec_options = {codec: CODEC_NAMES.get(codec, codec) for codec in SUPPORT_CODECS}
                
                return self.async_show_form(
                    step_id="edit_profile",
                    data_schema=vol.Schema({
                        vol.Required(PROFILE_NAME_KEY, default=form_data[PROFILE_NAME_KEY]): str,
                        vol.Required(VOICE_ID_KEY, default=form_data[VOICE_ID_KEY]): vol.In(voice_options),
                        vol.Optional(LANGUAGE_KEY, default=form_data[LANGUAGE_KEY]): vol.In(language_options),
                        vol.Optional(CODEC_KEY, default=form_data[CODEC_KEY]): vol.In(codec_options),
                        vol.Optional(SAMPLE_RATE_KEY, default=form_data[SAMPLE_RATE_KEY]): vol.In({
                            8000: "8000 Hz (Telephone quality)",
                            16000: "16000 Hz (Wideband)",
                            22050: "22050 Hz (Radio quality)",
                            24000: "24000 Hz (xAI default)",
                            44100: "44100 Hz (CD quality)",
                            48000: "48000 Hz (Professional)",
                        }),
                        vol.Optional(BIT_RATE_KEY, default=form_data[BIT_RATE_KEY]): vol.In({
                            32000: "32 kbps",
                            64000: "64 kbps",
                            96000: "96 kbps",
                            128000: "128 kbps (Default)",
                            192000: "192 kbps",
                        }),
                    })
                )
        
        return self.async_show_form(
            step_id="modify_profile",
            data_schema=vol.Schema({
                vol.Required("selected_profile"): vol.In(list(current_profiles.keys()))
            })
        )

    async def async_step_edit_profile(self, user_input: dict[str, Any] | None = None):
        """Edit the selected profile."""
        errors = {}
        
        if user_input is not None:
            current_profiles = self._config_entry.options.get("voice_profiles", {})
            new_profile_name = user_input[PROFILE_NAME_KEY]
            new_voice_id = user_input[VOICE_ID_KEY]
            
            # Find the original profile being edited
            # We need to match by finding a profile that had this voice before editing
            old_profile_name = None
            for name, data in current_profiles.items():
                # Check if this profile was likely the one being edited
                # by comparing the submitted voice with existing profiles
                if data.get("voice") == new_voice_id and name != new_profile_name:
                    old_profile_name = name
                    break
            
            # If we can't find by voice, check if new_profile_name exists and is different
            if old_profile_name is None and new_profile_name in current_profiles:
                # The user is editing an existing profile with the same name
                old_profile_name = new_profile_name
            
            # Check if renaming to a name that already exists (and it's a different profile)
            if new_profile_name != old_profile_name and new_profile_name in current_profiles:
                errors["profile_name"] = "profile_exists"
            
            if not errors:
                # Create updated profile from form data
                updated_profile = _map_form_data_to_profile(user_input)
                
                # Update options
                updated_profiles = current_profiles.copy()
                
                # Remove old profile if name changed
                if old_profile_name and old_profile_name != new_profile_name:
                    if old_profile_name in updated_profiles:
                        del updated_profiles[old_profile_name]
                
                # Add/update profile with new name
                updated_profiles[new_profile_name] = updated_profile
                
                new_options = self._config_entry.options.copy()
                new_options["voice_profiles"] = updated_profiles
                
                return self.async_create_entry(title="", data=new_options)
        
        # If we get here, there were errors, show form again
        return await self.async_step_modify_profile()

    async def async_step_delete_profile(self, user_input: dict[str, Any] | None = None):
        """Delete a voice profile."""
        current_profiles = self._config_entry.options.get("voice_profiles", {})
        
        if not current_profiles:
            # No profiles to delete, go back to main menu
            return await self.async_step_init()
        
        if user_input is not None:
            profile_to_delete = user_input["profile_name"]
            
            # Remove profile
            updated_profiles = current_profiles.copy()
            if profile_to_delete in updated_profiles:
                del updated_profiles[profile_to_delete]
            
            new_options = self._config_entry.options.copy()
            new_options["voice_profiles"] = updated_profiles
            
            return self.async_create_entry(title="", data=new_options)
        
        return self.async_show_form(
            step_id="delete_profile",
            data_schema=vol.Schema({
                vol.Required("profile_name"): vol.In(list(current_profiles.keys()))
            })
        )
