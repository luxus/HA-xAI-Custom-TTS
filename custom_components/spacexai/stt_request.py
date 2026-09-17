"""Pure helpers for xAI unary STT (POST /v1/stt). No Home Assistant imports.

xAI speech-to-text is **not** OpenAI Whisper-compatible: there is no
``/v1/audio/transcriptions`` path. Batch transcription is multipart
``POST https://api.x.ai/v1/stt`` (``file`` last). Streaming is
``wss://api.x.ai/v1/stt`` and is not used on the HA Assist STT entity
(HA collects the PCM/WAV stream, then this module posts the file).
"""

from __future__ import annotations

import io
import logging
import wave
from collections.abc import Mapping
from typing import Any

from .const import STT_LANGUAGE_ALIASES, STT_LANGUAGE_CODES, STT_REQUEST_TIMEOUT, XAI_STT_URL

_LOGGER = logging.getLogger(__name__)

_CODES = {code.lower(): code for code in STT_LANGUAGE_CODES}
_ALIASES = {alias.lower(): code for alias, code in STT_LANGUAGE_ALIASES.items()}


class STTError(Exception):
    """xAI STT request or response failed."""


def map_stt_language(language: str | None) -> str | None:
    """Map HA Assist BCP-47 tags to xAI 2-letter (or ``fil``) STT codes.

    Unknown tags are omitted: the model still transcribes; ``language`` is
    only required for Inverse Text Normalization when ``format=true``.
    """
    if language is None:
        return None
    raw = str(language).strip()
    if not raw:
        return None
    lowered = raw.lower()
    if lowered in _CODES:
        return _CODES[lowered]
    if lowered in _ALIASES:
        mapped = _ALIASES[lowered]
        return _CODES.get(mapped.lower())
    primary = lowered.split("-", 1)[0]
    if primary in _CODES:
        return _CODES[primary]
    return None


def stt_form_fields(
    *,
    language: str | None = None,
    enable_format: bool = True,
    audio_format: str | None = None,
    sample_rate: int | None = None,
) -> dict[str, str]:
    """Build multipart *data* fields. ``file`` must be sent separately and last."""
    fields: dict[str, str] = {}
    mapped = map_stt_language(language)
    if mapped:
        fields["language"] = mapped
        if enable_format:
            fields["format"] = "true"
    if audio_format in {"pcm", "mulaw", "alaw"}:
        fields["audio_format"] = audio_format
        if sample_rate:
            fields["sample_rate"] = str(int(sample_rate))
    return fields


def pcm_to_wav(
    pcm: bytes,
    *,
    sample_rate: int,
    sample_width: int,
    channels: int,
) -> bytes:
    """Wrap headerless PCM as a WAV container so xAI can auto-detect it."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buf.getvalue()


def prepare_stt_audio(
    audio: bytes,
    *,
    container: str,
    codec: str,
    sample_rate: int,
    bit_rate: int,
    channels: int,
) -> tuple[bytes, str, str]:
    """Return ``(body, filename, content_type)`` for the multipart ``file`` field.

    Assist typically sends headerless 16-bit PCM even when the metadata format
    is WAV. Wrap that as WAV so we do not have to send raw ``audio_format=pcm``.
    OGG/Opus is passed through.
    """
    if audio[:4] == b"RIFF":
        return audio, "audio.wav", "audio/wav"
    container_l = str(container).lower()
    codec_l = str(codec).lower()
    if container_l in {"ogg", "oga"} or codec_l == "opus":
        return audio, "audio.ogg", "audio/ogg"
    sample_width = max(1, int(bit_rate) // 8)
    wav = pcm_to_wav(
        audio,
        sample_rate=int(sample_rate),
        sample_width=sample_width,
        channels=max(1, int(channels)),
    )
    return wav, "audio.wav", "audio/wav"


def extract_stt_text(payload: Any) -> str:
    """Read ``text`` from POST /v1/stt JSON (or merge ``channels``)."""
    if not isinstance(payload, dict):
        raise STTError("STT response is not a JSON object")
    text = payload.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    channels = payload.get("channels")
    if isinstance(channels, list):
        parts: list[str] = []
        for channel in channels:
            if not isinstance(channel, dict):
                continue
            channel_text = channel.get("text")
            if isinstance(channel_text, str) and channel_text.strip():
                parts.append(channel_text.strip())
        if parts:
            return " ".join(parts)
    raise STTError("STT returned no transcript text")


def describe_stt_http_error(status_code: int, body: str = "") -> str:
    """Map STT HTTP statuses to a log line."""
    snippet = (body or "").strip()
    if len(snippet) > 500:
        snippet = snippet[:500] + "…"
    detail = f" — {snippet}" if snippet else ""
    if status_code == 400:
        return (
            "Bad request (400): check audio is a supported container or raw "
            f"pcm/mulaw/alaw with sample_rate, and that file is last{detail}"
        )
    if status_code == 401:
        return f"Unauthorized (401): Bearer token missing or invalid{detail}"
    if status_code == 413:
        return f"Payload too large (413): STT max file size is 500 MB{detail}"
    if status_code == 429:
        return f"Rate limited (429){detail}"
    if status_code == 503:
        return f"STT service unavailable (503){detail}"
    if status_code == 500:
        return f"Server error (500){detail}"
    return f"xAI STT HTTP {status_code}{detail}"


async def async_stt_transcribe(
    client: Any,
    headers: Mapping[str, str],
    audio: bytes,
    *,
    language: str | None = None,
    filename: str = "audio.wav",
    content_type: str = "audio/wav",
    audio_format: str | None = None,
    sample_rate: int | None = None,
    enable_format: bool = True,
    timeout: float = STT_REQUEST_TIMEOUT,
) -> str:
    """POST multipart /v1/stt. Data fields first; ``file`` last. No Content-Type header."""
    if not audio:
        raise STTError("audio is empty")
    fields = stt_form_fields(
        language=language,
        enable_format=enable_format,
        audio_format=audio_format,
        sample_rate=sample_rate,
    )
    # Do not forward Content-Type — httpx must set multipart boundaries.
    auth_headers = {key: value for key, value in headers.items() if key.lower() != "content-type"}
    response = await client.post(
        XAI_STT_URL,
        headers=auth_headers,
        data=fields or None,
        files={"file": (filename, audio, content_type)},
        timeout=timeout,
    )
    status = getattr(response, "status_code", 0)
    if status != 200:
        body = getattr(response, "text", "") or ""
        raise STTError(describe_stt_http_error(int(status), str(body)))
    try:
        payload = response.json()
    except Exception as err:  # noqa: BLE001
        raise STTError("STT response is not JSON") from err
    return extract_stt_text(payload)
