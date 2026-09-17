"""xAI STT request helpers (POST /v1/stt) — no live keys, no Home Assistant."""

from __future__ import annotations

from pathlib import Path

from spacexai.const import (
    GROK_CONVERSATION_ENTITY_ID,
    PLATFORMS,
    STT_ENTITY_ID,
    STT_LANGUAGE_CODES,
    STT_SUPPORTED_LANGUAGES,
    STT_UNIQUE_ID,
    TTS_ENTITY_ID,
    XAI_STT_URL,
    XAI_STT_WS_URL,
)
from spacexai.stt_request import (
    STTError,
    async_stt_transcribe,
    describe_stt_http_error,
    extract_stt_text,
    map_stt_language,
    pcm_to_wav,
    prepare_stt_audio,
    stt_form_fields,
)

from .fakes import FakeHttpxClient, FakeHttpxResponse

_ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "spacexai"


def test_stt_is_xai_not_whisper() -> None:
    assert XAI_STT_URL == "https://api.x.ai/v1/stt"
    assert XAI_STT_WS_URL == "wss://api.x.ai/v1/stt"
    assert "/audio/transcriptions" not in XAI_STT_URL
    assert PLATFORMS == ("conversation", "tts", "stt")
    src = (_ROOT / "stt_request.py").read_text()
    assert "file" in src
    assert "Whisper" in src or "whisper" in src.lower()


def test_stable_entity_ids() -> None:
    assert GROK_CONVERSATION_ENTITY_ID == "conversation.spacexai_grok"
    assert TTS_ENTITY_ID == "tts.spacexai_tts"
    assert STT_ENTITY_ID == "stt.spacexai_stt"
    assert STT_UNIQUE_ID == "spacexai_stt"
    conversation_src = (_ROOT / "conversation.py").read_text()
    tts_src = (_ROOT / "tts.py").read_text()
    stt_src = (_ROOT / "stt.py").read_text()
    assert "GROK_CONVERSATION_ENTITY_ID" in conversation_src
    assert "entity_id = GROK_CONVERSATION_ENTITY_ID" in conversation_src
    assert "entry.entry_id}-grok" not in conversation_src
    assert "TTS_ENTITY_ID" in tts_src
    assert "entity_id = TTS_ENTITY_ID" in tts_src
    assert "STT_ENTITY_ID" in stt_src
    assert "entity_id = STT_ENTITY_ID" in stt_src


def test_language_map_assist_bcp47() -> None:
    assert map_stt_language("en") == "en"
    assert map_stt_language("en-US") == "en"
    assert map_stt_language("en-GB") == "en"
    assert map_stt_language("de-DE") == "de"
    assert map_stt_language("pt-BR") == "pt"
    assert map_stt_language("fil-PH") == "fil"
    assert map_stt_language("ja-JP") == "ja"
    assert map_stt_language("zh-CN") is None  # not an xAI STT formatting code
    assert map_stt_language("xx-YY") is None
    assert map_stt_language("") is None
    assert "en-US" in STT_SUPPORTED_LANGUAGES
    assert "en" in STT_LANGUAGE_CODES


def test_form_fields_language_and_format() -> None:
    fields = stt_form_fields(language="en-US")
    assert fields["language"] == "en"
    assert fields["format"] == "true"
    assert "file" not in fields
    raw = stt_form_fields(language=None, audio_format="pcm", sample_rate=16000)
    assert raw["audio_format"] == "pcm"
    assert raw["sample_rate"] == "16000"
    assert "language" not in raw


def test_extract_stt_text() -> None:
    assert extract_stt_text({"text": "  Hello Grok.  ", "duration": 1.2}) == "Hello Grok."
    merged = extract_stt_text(
        {
            "text": "",
            "channels": [
                {"index": 0, "text": "Left"},
                {"index": 1, "text": "Right"},
            ],
        }
    )
    assert merged == "Left Right"
    try:
        extract_stt_text({"text": "  "})
        raise AssertionError("expected STTError")
    except STTError:
        pass


def test_prepare_wraps_pcm_as_wav() -> None:
    pcm = b"\x00\x01" * 80
    body, filename, content_type = prepare_stt_audio(
        pcm,
        container="wav",
        codec="pcm",
        sample_rate=16000,
        bit_rate=16,
        channels=1,
    )
    assert filename == "audio.wav"
    assert content_type == "audio/wav"
    assert body[:4] == b"RIFF"
    already = pcm_to_wav(pcm, sample_rate=16000, sample_width=2, channels=1)
    body2, _, _ = prepare_stt_audio(
        already,
        container="wav",
        codec="pcm",
        sample_rate=16000,
        bit_rate=16,
        channels=1,
    )
    assert body2[:4] == b"RIFF"
    ogg, ogg_name, ogg_type = prepare_stt_audio(
        b"OggSxxxx",
        container="ogg",
        codec="opus",
        sample_rate=16000,
        bit_rate=16,
        channels=1,
    )
    assert ogg_name == "audio.ogg"
    assert ogg_type == "audio/ogg"
    assert ogg.startswith(b"OggS")


def test_describe_stt_errors() -> None:
    assert "400" in describe_stt_http_error(400)
    assert "401" in describe_stt_http_error(401)
    assert "Bearer" in describe_stt_http_error(401)


async def test_async_stt_transcribe_posts_multipart_file_last() -> None:
    client = FakeHttpxClient(
        FakeHttpxResponse(200, {"text": "Turn on the lights.", "language": "en", "duration": 1.0}),
        expected_url=XAI_STT_URL,
    )
    audio = pcm_to_wav(b"\x00\x01" * 40, sample_rate=16000, sample_width=2, channels=1)
    text = await async_stt_transcribe(
        client,
        {"Authorization": "Bearer test-token", "Content-Type": "application/json"},
        audio,
        language="en-US",
        filename="audio.wav",
        content_type="audio/wav",
    )
    assert text == "Turn on the lights."
    call = client.calls[0]
    assert call["url"] == XAI_STT_URL
    assert call["headers"] == {"Authorization": "Bearer test-token"}
    assert "Content-Type" not in call["headers"]
    data = call["data"]
    assert data["language"] == "en"
    assert data["format"] == "true"
    assert "file" not in data
    files = call["files"]
    assert "file" in files
    filename, body, content_type = files["file"]
    assert filename == "audio.wav"
    assert content_type == "audio/wav"
    assert body[:4] == b"RIFF"


async def test_async_stt_transcribe_rejects_http_error() -> None:
    client = FakeHttpxClient(FakeHttpxResponse(401, {"error": "unauthorized"}))
    try:
        await async_stt_transcribe(
            client,
            {"Authorization": "Bearer x"},
            b"RIFF....",
        )
        raise AssertionError("expected STTError")
    except STTError as err:
        assert "401" in str(err)
