"""SpaceXAI TTS platform (xAI Voice paths, shared umbrella auth)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import async_timeout
import httpx

from homeassistant.components.tts import TextToSpeechEntity, TtsAudioType, Voice
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    ATTR_BIT_RATE,
    ATTR_CODEC,
    ATTR_LANGUAGE,
    ATTR_REPLACE,
    ATTR_SAMPLE_RATE,
    ATTR_SPEED,
    ATTR_TEXT_NORMALIZATION,
    ATTR_VOICE,
    CODEC_EXTENSIONS,
    DEFAULT_BIT_RATE,
    DEFAULT_CODEC,
    DEFAULT_LANGUAGE,
    DEFAULT_NAME,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_SPEED,
    DEFAULT_TEXT_NORMALIZATION,
    DEFAULT_VOICE,
    DOMAIN,
    SUPPORT_LANGUAGES,
    TTS_ENTITY_ID,
    TTS_ENTITY_NAME,
    TTS_MAX_RETRIES,
    TTS_REQUEST_TIMEOUT,
    TTS_RETRY_STATUS_CODES,
    TTS_UNIQUE_ID,
    XAI_TTS_URL,
)
from .tts_request import (
    build_tts_payload,
    coerce_bool,
    describe_http_error,
    normalize_voice_id,
    parse_replace,
    resolve_bit_rate,
    resolve_codec,
    resolve_sample_rate,
    resolve_speed,
    validate_text,
)
from .voices import fallback_voices, fetch_all_voices

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpaceXAI TTS platform via config entry."""
    if DOMAIN not in hass.data or config_entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("SpaceXAI integration not loaded")
        return

    runtime = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SpaceXAITTSEntity(hass, runtime, config_entry)])


class SpaceXAITTSEntity(TextToSpeechEntity):
    """xAI TTS provider sharing the umbrella config entry's auth."""

    _attr_has_entity_name = True
    _attr_name = TTS_ENTITY_NAME

    def __init__(self, hass: HomeAssistant, runtime: Any, config_entry: ConfigEntry) -> None:
        """Initialize SpaceXAI TTS provider."""
        self.hass = hass
        self._runtime = runtime
        self._config_entry = config_entry
        self._httpx_client = get_async_client(hass)
        self._available_voices = fallback_voices()
        self.entity_id = TTS_ENTITY_ID
        self._attr_unique_id = TTS_UNIQUE_ID
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title or DEFAULT_NAME,
            manufacturer="xAI",
            model="Grok",
        )

    async def async_added_to_hass(self) -> None:
        """Cache built-in + custom voices for Assist voice pickers."""
        await super().async_added_to_hass()
        try:
            headers = await self._runtime.async_authorization_headers()
            self._available_voices = await fetch_all_voices(self._httpx_client, headers)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Voice list refresh failed; using fallback", exc_info=True)

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
        """Return list of supported options (HA names mapping 1:1 to API fields)."""
        return [
            "voice_profile",
            ATTR_VOICE,
            ATTR_LANGUAGE,
            ATTR_CODEC,
            ATTR_SAMPLE_RATE,
            ATTR_BIT_RATE,
            ATTR_SPEED,
            ATTR_TEXT_NORMALIZATION,
            ATTR_REPLACE,
        ]

    @property
    def default_options(self) -> dict[str, Any]:
        """Return dict of default options."""
        return {
            ATTR_VOICE: DEFAULT_VOICE,
            ATTR_LANGUAGE: DEFAULT_LANGUAGE,
            ATTR_CODEC: DEFAULT_CODEC,
            ATTR_SAMPLE_RATE: DEFAULT_SAMPLE_RATE,
            ATTR_BIT_RATE: DEFAULT_BIT_RATE,
            ATTR_SPEED: DEFAULT_SPEED,
            ATTR_TEXT_NORMALIZATION: DEFAULT_TEXT_NORMALIZATION,
        }

    @callback
    def async_get_supported_voices(self, language: str) -> list[Voice]:
        """Return voice profiles plus API-listed built-in/custom voices."""
        voices: list[Voice] = []
        seen: set[str] = set()

        voice_profiles = self._config_entry.options.get("voice_profiles", {})
        for profile_name, profile_data in voice_profiles.items():
            xai_voice = profile_data.get("voice", DEFAULT_VOICE)
            voices.append(Voice(voice_id=profile_name, name=profile_name))
            seen.add(profile_name)
            _LOGGER.debug(
                "Added voice profile '%s' (xAI voice: %s) to supported voices",
                profile_name,
                xai_voice,
            )

        for voice_id, info in self._available_voices.items():
            if voice_id in seen:
                continue
            label = info.get("name") or voice_id
            if info.get("source") == "custom":
                label = f"{label} (custom)"
            voices.append(Voice(voice_id=voice_id, name=label))

        return voices

    def _merge_options(
        self, options: dict[str, Any]
    ) -> tuple[dict[str, Any], str | None]:
        """Merge defaults, optional voice profile, and per-call options."""
        voice_profiles = self._config_entry.options.get("voice_profiles", {})
        voice_profile_name = options.get("voice_profile")
        profile_selected_via_voice = False

        if not voice_profile_name and ATTR_VOICE in options:
            potential_profile = options[ATTR_VOICE]
            if potential_profile in voice_profiles:
                voice_profile_name = potential_profile
                profile_selected_via_voice = True
                _LOGGER.debug(
                    "Voice '%s' matches a voice profile, using profile settings",
                    potential_profile,
                )

        overlay = {
            key: value
            for key, value in options.items()
            if key != "voice_profile"
        }
        if profile_selected_via_voice:
            overlay.pop(ATTR_VOICE, None)

        if voice_profile_name:
            if voice_profile_name in voice_profiles:
                profile_options = voice_profiles[voice_profile_name].copy()
                _LOGGER.debug(
                    "Using voice profile '%s' with settings: %s",
                    voice_profile_name,
                    profile_options,
                )
                return (
                    {**self.default_options, **profile_options, **overlay},
                    voice_profile_name,
                )
            _LOGGER.warning(
                "Voice profile '%s' not found in profiles %s, using default options",
                voice_profile_name,
                list(voice_profiles.keys()),
            )

        return {**self.default_options, **overlay}, voice_profile_name

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> TtsAudioType:
        """Load TTS audio file from xAI."""
        if options is None:
            options = {}

        _LOGGER.debug(
            "TTS request received for message length: %d language=%s options=%s",
            len(message),
            language,
            options,
        )

        try:
            validate_text(message)
        except ValueError as err:
            _LOGGER.error("Invalid TTS text: %s", err)
            return None

        merged_options, voice_profile_name = self._merge_options(options)

        voice_id = normalize_voice_id(
            merged_options.get(ATTR_VOICE, DEFAULT_VOICE), DEFAULT_VOICE
        )
        lang = merged_options.get(ATTR_LANGUAGE, language) or language
        codec = resolve_codec(merged_options.get(ATTR_CODEC, DEFAULT_CODEC))
        sample_rate = resolve_sample_rate(
            merged_options.get(ATTR_SAMPLE_RATE, DEFAULT_SAMPLE_RATE)
        )
        bit_rate = resolve_bit_rate(
            merged_options.get(ATTR_BIT_RATE, DEFAULT_BIT_RATE), codec
        )
        speed = resolve_speed(merged_options.get(ATTR_SPEED, DEFAULT_SPEED))
        text_normalization = coerce_bool(
            merged_options.get(ATTR_TEXT_NORMALIZATION, DEFAULT_TEXT_NORMALIZATION),
            DEFAULT_TEXT_NORMALIZATION,
        )

        try:
            replace = parse_replace(merged_options.get(ATTR_REPLACE))
        except ValueError as err:
            _LOGGER.error("Invalid replace map: %s", err)
            return None

        payload = build_tts_payload(
            text=message,
            voice_id=voice_id,
            language=lang,
            codec=codec,
            sample_rate=sample_rate,
            bit_rate=bit_rate,
            speed=speed,
            text_normalization=text_normalization,
            replace=replace,
        )

        try:
            headers = {
                **await self._runtime.async_authorization_headers(),
                "Content-Type": "application/json",
            }
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("SpaceXAI auth headers failed: %s", err)
            return None

        try:
            with async_timeout.timeout(TTS_REQUEST_TIMEOUT * TTS_MAX_RETRIES + 8):
                audio_bytes = await self._post_tts(headers, payload, voice_id)
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout generating TTS audio")
            return None
        except httpx.RequestError as err:
            _LOGGER.error("Error connecting to xAI API: %s", err)
            return None
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error generating TTS audio: %s", err)
            return None

        if not audio_bytes:
            return None

        _LOGGER.info(
            "Successfully generated %d bytes of audio for voice %s (codec: %s)%s",
            len(audio_bytes),
            voice_id,
            codec,
            f" using profile '{voice_profile_name}'" if voice_profile_name else "",
        )
        return (CODEC_EXTENSIONS.get(codec, "mp3"), audio_bytes)

    async def _post_tts(
        self, headers: dict[str, str], payload: dict[str, Any], voice_id: str
    ) -> bytes | None:
        """POST /v1/tts with retries on 429/500/503."""
        last_error = "Max retries exceeded"
        for attempt in range(TTS_MAX_RETRIES):
            _LOGGER.debug(
                "Sending TTS request to xAI: voice=%s language=%s codec=%s "
                "sample_rate=%s speed=%s text_normalization=%s attempt=%s",
                voice_id,
                payload.get("language"),
                payload.get("output_format", {}).get("codec"),
                payload.get("output_format", {}).get("sample_rate"),
                payload.get("speed"),
                payload.get("text_normalization"),
                attempt + 1,
            )
            response = await self._httpx_client.post(
                XAI_TTS_URL,
                headers=headers,
                json=payload,
                timeout=TTS_REQUEST_TIMEOUT,
            )
            if response.status_code == 200:
                audio_bytes = response.content
                if not audio_bytes:
                    _LOGGER.error("No audio data received from xAI")
                    return None
                return audio_bytes

            last_error = describe_http_error(response.status_code, response.text)
            if (
                response.status_code in TTS_RETRY_STATUS_CODES
                and attempt < TTS_MAX_RETRIES - 1
            ):
                wait = 2**attempt
                _LOGGER.warning("%s; retrying in %ss", last_error, wait)
                await asyncio.sleep(wait)
                continue

            _LOGGER.error("%s", last_error)
            return None

        _LOGGER.error("%s", last_error)
        return None
