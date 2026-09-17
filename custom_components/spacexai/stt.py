"""SpaceXAI STT platform — xAI POST /v1/stt on the umbrella config entry."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterable
from typing import Any

from homeassistant.components import stt
from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechToTextEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    DEFAULT_NAME,
    DOMAIN,
    STT_ENTITY_ID,
    STT_ENTITY_NAME,
    STT_SUPPORTED_LANGUAGES,
    STT_UNIQUE_ID,
)
from .stt_request import STTError, async_stt_transcribe, prepare_stt_audio

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpaceXAI STT from the shared config entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SpaceXAISTTEntity(hass, entry, runtime)])


class SpaceXAISTTEntity(SpeechToTextEntity):
    """Assist STT entity posting collected audio to ``https://api.x.ai/v1/stt``."""

    _attr_has_entity_name = True
    _attr_name = STT_ENTITY_NAME

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, runtime: Any) -> None:
        self.hass = hass
        self.entry = entry
        self._runtime = runtime
        self._httpx_client = get_async_client(hass)
        self.entity_id = STT_ENTITY_ID
        self._attr_unique_id = STT_UNIQUE_ID
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or DEFAULT_NAME,
            manufacturer="xAI",
            model="Grok",
        )

    @property
    def supported_languages(self) -> list[str]:
        return list(STT_SUPPORTED_LANGUAGES)

    @property
    def supported_formats(self) -> list[AudioFormats]:
        return [AudioFormats.WAV, AudioFormats.OGG]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        return [AudioCodecs.PCM, AudioCodecs.OPUS]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        # HA's enum has no 24000; Assist typically uses 16 kHz mono PCM.
        return [
            AudioSampleRates.SAMPLERATE_8000,
            AudioSampleRates.SAMPLERATE_16000,
            AudioSampleRates.SAMPLERATE_22050,
            AudioSampleRates.SAMPLERATE_44100,
            AudioSampleRates.SAMPLERATE_48000,
        ]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        return [AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self, metadata: stt.SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> stt.SpeechResult:
        """Collect the Assist audio stream and transcribe via unary POST /v1/stt."""
        chunks: list[bytes] = []
        async for chunk in stream:
            if chunk:
                chunks.append(chunk)
        audio = b"".join(chunks)
        if not audio:
            _LOGGER.error("xAI STT received empty audio stream")
            return stt.SpeechResult("", stt.SpeechResultState.ERROR)

        body, filename, content_type = prepare_stt_audio(
            audio,
            container=str(metadata.format),
            codec=str(metadata.codec),
            sample_rate=int(metadata.sample_rate),
            bit_rate=int(metadata.bit_rate),
            channels=int(metadata.channel),
        )
        try:
            headers = await self._runtime.async_authorization_headers()
            text = await async_stt_transcribe(
                self._httpx_client,
                headers,
                body,
                language=metadata.language,
                filename=filename,
                content_type=content_type,
            )
        except STTError as err:
            _LOGGER.error("xAI STT failed: %s", err)
            return stt.SpeechResult("", stt.SpeechResultState.ERROR)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("xAI STT request failed")
            return stt.SpeechResult("", stt.SpeechResultState.ERROR)

        _LOGGER.debug("xAI STT transcribed %d bytes to %d chars", len(body), len(text))
        return stt.SpeechResult(text, stt.SpeechResultState.SUCCESS)
