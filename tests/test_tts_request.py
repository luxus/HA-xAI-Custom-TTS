"""Unit tests for xAI TTS request helpers and voice list parsers (no API key, no HA)."""

from __future__ import annotations

from spacexai.const import (
    CODEC_CONTENT_TYPES,
    MAX_TTS_TEXT_CHARS,
    SUPPORT_LANGUAGES,
    XAI_CUSTOM_VOICES_URL,
    XAI_TTS_URL,
    XAI_TTS_WS_URL,
    XAI_VOICES_URL,
)
from spacexai.tts_request import (
    build_tts_payload,
    coerce_bool,
    describe_http_error,
    normalize_voice_id,
    parse_replace,
    resolve_codec,
    resolve_speed,
    validate_text,
)
from spacexai.voices import (
    fallback_voices,
    fetch_all_voices,
    format_voice_label,
    parse_builtin_voices,
    parse_custom_voices,
)

from .fakes import FakeHttpxClient, FakeHttpxResponse


def test_unary_and_voice_urls() -> None:
    assert XAI_TTS_URL == "https://api.x.ai/v1/tts"
    assert XAI_VOICES_URL == "https://api.x.ai/v1/tts/voices"
    assert XAI_CUSTOM_VOICES_URL == "https://api.x.ai/v1/custom-voices"
    assert XAI_TTS_WS_URL == "wss://api.x.ai/v1/tts"
    assert XAI_TTS_WS_URL != "wss://api.x.ai/v1/realtime"


def test_alaw_content_type() -> None:
    assert CODEC_CONTENT_TYPES["alaw"] == "audio/alaw"
    assert CODEC_CONTENT_TYPES["mulaw"] == "audio/basic"


def test_language_list_matches_docs() -> None:
    assert SUPPORT_LANGUAGES == [
        "auto",
        "en",
        "ar-EG",
        "ar-SA",
        "ar-AE",
        "bn",
        "zh",
        "fr",
        "de",
        "hi",
        "id",
        "it",
        "ja",
        "ko",
        "pt-BR",
        "pt-PT",
        "ru",
        "es-MX",
        "es-ES",
        "tr",
        "vi",
    ]


def test_text_limit_is_60k() -> None:
    assert MAX_TTS_TEXT_CHARS == 60_000


def test_nested_output_format_and_optional_fields() -> None:
    payload = build_tts_payload(
        text="Hello",
        voice_id="nlbqfwie",
        language="en",
        codec="mp3",
        sample_rate=24000,
        bit_rate=128000,
        speed=1.2,
        text_normalization=True,
        replace={"Acme Mobile": "Acme Mobull"},
    )
    assert payload["output_format"] == {
        "codec": "mp3",
        "sample_rate": 24000,
        "bit_rate": 128000,
    }
    assert payload["voice_id"] == "nlbqfwie"
    assert payload["speed"] == 1.2
    assert payload["text_normalization"] is True
    assert payload["replace"]["Acme Mobile"] == "Acme Mobull"
    assert "optimize_streaming_latency" not in payload
    assert "with_timestamps" not in payload


def test_non_mp3_omits_bit_rate() -> None:
    payload = build_tts_payload(
        text="Hello",
        voice_id="eve",
        language="en",
        codec="alaw",
        sample_rate=8000,
        bit_rate=128000,
    )
    assert payload["output_format"] == {"codec": "alaw", "sample_rate": 8000}


def test_unknown_voice_is_passed_through() -> None:
    assert normalize_voice_id("nlbqfwie") == "nlbqfwie"
    assert normalize_voice_id("carina") == "carina"
    assert normalize_voice_id("  ") == "eve"


def test_speed_range() -> None:
    assert resolve_speed(1.2) == 1.2
    assert resolve_speed("0.7") == 0.7
    assert resolve_speed(1.5) == 1.5
    assert resolve_speed(0.5) == 1.0
    assert resolve_speed(2.0) == 1.0


def test_bool_coercion() -> None:
    assert coerce_bool("true") is True
    assert coerce_bool("on") is True
    assert coerce_bool("false") is False
    assert coerce_bool(None, False) is False


def test_codec_fallback() -> None:
    assert resolve_codec("alaw") == "alaw"
    assert resolve_codec("ogg") == "mp3"


def test_replace_json_and_limits() -> None:
    assert parse_replace('{"nginx": "/ˈɛndʒɪn ˈɛks/"}') == {"nginx": "/ˈɛndʒɪn ˈɛks/"}
    assert parse_replace({}) is None
    try:
        parse_replace("[]")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        parse_replace({"": "x"})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_text_validation() -> None:
    assert validate_text("hi") == "hi"
    try:
        validate_text("   ")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        validate_text("x" * (MAX_TTS_TEXT_CHARS + 1))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_documented_status_codes() -> None:
    assert "400" in describe_http_error(400)
    assert "401" in describe_http_error(401)
    assert "404" in describe_http_error(404)
    assert "custom-voices" in describe_http_error(404)
    assert "429" in describe_http_error(429)
    assert "503" in describe_http_error(503)


def test_builtin_shape() -> None:
    parsed = parse_builtin_voices(
        {
            "voices": [
                {"voice_id": "eve", "name": "Eve", "language": "en"},
                {"voice_id": "carina", "name": "Carina", "language": "en"},
            ]
        }
    )
    assert parsed["eve"]["name"] == "Eve"
    assert parsed["eve"]["source"] == "builtin"
    assert parsed["carina"]["name"] == "Carina"
    assert "Eve" not in parsed


def test_does_not_lowercase_custom_ids() -> None:
    parsed = parse_custom_voices(
        {
            "voices": [
                {
                    "voice_id": "nlbqfwie",
                    "name": "Friendly Narrator",
                    "gender": "female",
                    "tone": "warm",
                    "language": "en",
                }
            ]
        }
    )
    assert "nlbqfwie" in parsed
    assert parsed["nlbqfwie"]["source"] == "custom"
    assert "custom" in format_voice_label("nlbqfwie", parsed["nlbqfwie"])


def test_fallback_includes_additional_voices() -> None:
    voices = fallback_voices()
    assert "eve" in voices
    assert "carina" in voices
    assert voices["eve"]["source"] == "builtin"


async def test_fetch_all_voices_uses_bearer_headers() -> None:
    client = FakeHttpxClient(
        responses=[
            FakeHttpxResponse(200, {"voices": [{"voice_id": "eve", "name": "Eve"}]}),
            FakeHttpxResponse(403, {"error": "forbidden"}),
        ]
    )
    headers = {"Authorization": "Bearer oauth-access"}
    voices = await fetch_all_voices(client, headers)
    assert voices["eve"]["name"] == "Eve"
    assert client.calls[0]["url"] == XAI_VOICES_URL
    assert client.calls[0]["headers"] == headers
    assert client.calls[1]["url"] == XAI_CUSTOM_VOICES_URL
    assert "Bearer oauth-access" in client.calls[0]["headers"]["Authorization"]
    assert not any(
        "api_key" in str(call.get("headers", {})).lower() for call in client.calls
    )
