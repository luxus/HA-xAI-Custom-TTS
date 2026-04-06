"""xAI TTS platform."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import async_timeout
import httpx

from homeassistant.components.tts import TextToSpeechEntity, TtsAudioType, Voice
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    DOMAIN,
    XAI_TTS_URL,
    XAI_VOICES,
    DEFAULT_VOICE,
    DEFAULT_LANGUAGE,
    DEFAULT_CODEC,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_BIT_RATE,
    SUPPORT_LANGUAGES,
    SUPPORT_CODECS,
    SUPPORT_SAMPLE_RATES,
    SUPPORT_BIT_RATES,
)

_LOGGER = logging.getLogger(__name__)

# Content type mapping for codecs
CODEC_CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
    "mulaw": "audio/basic",
    "alaw": "audio/basic",
}

# File extension mapping for codecs
CODEC_EXTENSIONS = {
    "mp3": "mp3",
    "wav": "wav",
    "pcm": "pcm",
    "mulaw": "au",
    "alaw": "au",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up xAI TTS platform via config entry."""
    # Get the API key from the integration data
    if DOMAIN not in hass.data or config_entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("xAI integration not loaded")
        return
    
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    api_key = entry_data["api_key"]
    
    async_add_entities([XAITTSProvider(hass, api_key, config_entry)])


class XAITTSProvider(TextToSpeechEntity):
    """xAI TTS provider."""

    def __init__(self, hass: HomeAssistant, api_key: str, config_entry: ConfigEntry) -> None:
        """Initialize xAI TTS provider."""
        self.hass = hass
        self._api_key = api_key
        self._config_entry = config_entry
        self._httpx_client = get_async_client(hass)
        # Set the entity name for entity ID generation
        self._name = "xai_custom_tts"
        # Set the friendly name that should appear in UI and registry
        self._attr_name = "xAI Custom TTS"
        self._friendly_name = "xAI Custom TTS"

    @property
    def name(self) -> str:
        """Return the name of the entity (for entity ID)."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this TTS entity."""
        return f"{DOMAIN}_tts"

    @property
    def default_language(self) -> str:
        """Return the default language."""
        return DEFAULT_LANGUAGE

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return SUPPORT_LANGUAGES

    @property
    def supported_options(self) -> list[str]:
        """Return list of supported options."""
        return [
            "voice_profile",
            "voice",
            "language",
            "codec",
            "sample_rate",
            "bit_rate",
        ]

    @property
    def default_options(self) -> dict[str, Any]:
        """Return dict of default options."""
        return {
            "voice": DEFAULT_VOICE,
            "language": DEFAULT_LANGUAGE,
            "codec": DEFAULT_CODEC,
            "sample_rate": DEFAULT_SAMPLE_RATE,
            "bit_rate": DEFAULT_BIT_RATE,
        }

    @callback
    def async_get_supported_voices(self, language: str) -> list[Voice]:
        """Return list of supported voices for Assist pipeline."""
        voices = []
        
        # Get voice profiles from config entry
        voice_profiles = self._config_entry.options.get("voice_profiles", {})
        
        _LOGGER.debug("Getting supported voices for language %s, found %d voice profiles", 
                     language, len(voice_profiles))
        
        # Add each configured voice profile as a selectable voice
        for profile_name, profile_data in voice_profiles.items():
            voice_id = profile_data.get("voice", DEFAULT_VOICE)
            
            # Create a Voice object for this profile
            # The voice_id in Voice() becomes the identifier used in the Assist pipeline
            # When selected, it will be passed as the "voice" option to async_get_tts_audio
            voices.append(
                Voice(
                    voice_id=profile_name,  # Use profile name as the voice identifier
                    name=profile_name,  # Display name in UI
                )
            )
            _LOGGER.debug("Added voice profile '%s' (xAI voice: %s) to supported voices", 
                         profile_name, voice_id)
        
        # If no profiles configured, return empty list to use default
        if not voices:
            _LOGGER.debug("No voice profiles configured, Assist will use default voice")
        
        return voices

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> TtsAudioType:
        """Load TTS audio file from xAI."""
        _LOGGER.debug("TTS request received for message length: %d", len(message))
        _LOGGER.debug("Language: %s", language) 
        _LOGGER.debug("Options: %s", options)
        
        if options is None:
            options = {}
        
        # Get voice profiles from config entry
        voice_profiles = self._config_entry.options.get("voice_profiles", {})
        
        # Check if voice_profile is explicitly provided
        voice_profile_name = options.get("voice_profile")
        
        # If no explicit voice_profile but "voice" is provided, check if it matches a profile name
        # This handles when Assist pipeline passes the selected voice
        if not voice_profile_name and "voice" in options:
            potential_profile = options["voice"]
            if potential_profile in voice_profiles:
                voice_profile_name = potential_profile
                _LOGGER.debug("Voice '%s' matches a voice profile, using profile settings", potential_profile)
        
        _LOGGER.debug("Voice profile requested: %s", voice_profile_name)
        
        if voice_profile_name:
            _LOGGER.debug("Available voice profiles: %s", list(voice_profiles.keys()))
            if voice_profile_name in voice_profiles:
                # Use voice profile settings directly - these are the user's intended settings
                profile_options = voice_profiles[voice_profile_name].copy()
                merged_options = {**self.default_options, **profile_options}
                _LOGGER.debug("Using voice profile '%s' with settings: %s", voice_profile_name, profile_options)
            else:
                _LOGGER.warning("Voice profile '%s' not found in profiles %s, using default options", 
                              voice_profile_name, list(voice_profiles.keys()))
                merged_options = {**self.default_options, **options}
        else:
            # Merge provided options with defaults
            merged_options = {**self.default_options, **options}
            _LOGGER.debug("No voice profile specified, using merged options")
        
        voice_id = merged_options.get("voice", DEFAULT_VOICE)
        lang = merged_options.get("language", language)
        codec = merged_options.get("codec", DEFAULT_CODEC)
        sample_rate = merged_options.get("sample_rate", DEFAULT_SAMPLE_RATE)
        bit_rate = merged_options.get("bit_rate", DEFAULT_BIT_RATE)
        
        # Validate voice_id
        if voice_id not in XAI_VOICES:
            _LOGGER.warning("Invalid voice_id '%s', using default '%s'", voice_id, DEFAULT_VOICE)
            voice_id = DEFAULT_VOICE
        
        # Validate codec
        if codec not in SUPPORT_CODECS:
            _LOGGER.warning("Invalid codec '%s', using default '%s'", codec, DEFAULT_CODEC)
            codec = DEFAULT_CODEC
        
        # Validate sample rate
        if sample_rate not in SUPPORT_SAMPLE_RATES:
            _LOGGER.warning("Invalid sample_rate '%s', using default '%s'", sample_rate, DEFAULT_SAMPLE_RATE)
            sample_rate = DEFAULT_SAMPLE_RATE
        
        # Validate bit rate (MP3 only)
        if codec == "mp3" and bit_rate not in SUPPORT_BIT_RATES:
            _LOGGER.warning("Invalid bit_rate '%s', using default '%s'", bit_rate, DEFAULT_BIT_RATE)
            bit_rate = DEFAULT_BIT_RATE
        
        try:
            with async_timeout.timeout(30):
                # Prepare request
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
                
                payload = {
                    "text": message,
                    "voice_id": voice_id,
                    "language": lang,
                    "output_format": {
                        "codec": codec,
                        "sample_rate": sample_rate,
                    },
                }
                
                # Add bit_rate for MP3 codec
                if codec == "mp3":
                    payload["output_format"]["bit_rate"] = bit_rate
                
                _LOGGER.debug("Sending TTS request to xAI: voice=%s, language=%s, codec=%s, sample_rate=%s", 
                             voice_id, lang, codec, sample_rate)
                
                # Make the API request
                response = await self._httpx_client.post(
                    XAI_TTS_URL,
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )
                
                response.raise_for_status()
                
                audio_bytes = response.content
                
                if not audio_bytes:
                    _LOGGER.error("No audio data received from xAI")
                    return None
                
                _LOGGER.info(
                    "Successfully generated %d bytes of audio for voice %s (codec: %s)%s",
                    len(audio_bytes),
                    voice_id,
                    codec,
                    f" using profile '{voice_profile_name}'" if voice_profile_name else ""
                )
                
                # Return with appropriate extension
                return (CODEC_EXTENSIONS.get(codec, "mp3"), audio_bytes)
                
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout generating TTS audio")
            return None
        except httpx.HTTPStatusError as err:
            _LOGGER.error("xAI API error: %s - %s", err.response.status_code, err.response.text)
            return None
        except httpx.RequestError as err:
            _LOGGER.error("Error connecting to xAI API: %s", err)
            return None
        except Exception as err:
            _LOGGER.error("Error generating TTS audio: %s", err)
            return None
