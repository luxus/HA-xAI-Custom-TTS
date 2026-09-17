"""Unit tests for xAI TTS request helpers and voice list parsers (no API key, no HA)."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "xai_custom_tts"

# Load the integration as a package without executing Home Assistant __init__.py
_pkg = types.ModuleType("xai_custom_tts")
_pkg.__path__ = [str(COMPONENT)]
_pkg.__package__ = "xai_custom_tts"
sys.modules.setdefault("xai_custom_tts", _pkg)

from xai_custom_tts.const import (
    CODEC_CONTENT_TYPES,
    MAX_TTS_TEXT_CHARS,
    SUPPORT_LANGUAGES,
    XAI_CUSTOM_VOICES_URL,
    XAI_TTS_URL,
    XAI_TTS_WS_URL,
    XAI_VOICES_URL,
)
from xai_custom_tts.tts_request import (  # noqa: E402
    build_tts_payload,
    coerce_bool,
    describe_http_error,
    normalize_voice_id,
    parse_replace,
    resolve_codec,
    resolve_speed,
    validate_text,
)
from xai_custom_tts.voices import (  # noqa: E402
    format_voice_label,
    parse_builtin_voices,
    parse_custom_voices,
)


class ConstAlignmentTests(unittest.TestCase):
    def test_unary_and_voice_urls(self) -> None:
        self.assertEqual(XAI_TTS_URL, "https://api.x.ai/v1/tts")
        self.assertEqual(XAI_VOICES_URL, "https://api.x.ai/v1/tts/voices")
        self.assertEqual(XAI_CUSTOM_VOICES_URL, "https://api.x.ai/v1/custom-voices")
        self.assertEqual(XAI_TTS_WS_URL, "wss://api.x.ai/v1/tts")
        self.assertNotEqual(XAI_TTS_WS_URL, "wss://api.x.ai/v1/realtime")

    def test_alaw_content_type(self) -> None:
        self.assertEqual(CODEC_CONTENT_TYPES["alaw"], "audio/alaw")
        self.assertEqual(CODEC_CONTENT_TYPES["mulaw"], "audio/basic")

    def test_language_list_matches_docs(self) -> None:
        self.assertEqual(
            SUPPORT_LANGUAGES,
            [
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
            ],
        )

    def test_text_limit_is_60k(self) -> None:
        self.assertEqual(MAX_TTS_TEXT_CHARS, 60_000)


class PayloadTests(unittest.TestCase):
    def test_nested_output_format_and_optional_fields(self) -> None:
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
        self.assertEqual(
            payload["output_format"],
            {"codec": "mp3", "sample_rate": 24000, "bit_rate": 128000},
        )
        self.assertEqual(payload["voice_id"], "nlbqfwie")
        self.assertEqual(payload["speed"], 1.2)
        self.assertTrue(payload["text_normalization"])
        self.assertEqual(payload["replace"]["Acme Mobile"], "Acme Mobull")
        self.assertNotIn("optimize_streaming_latency", payload)
        self.assertNotIn("with_timestamps", payload)

    def test_non_mp3_omits_bit_rate(self) -> None:
        payload = build_tts_payload(
            text="Hello",
            voice_id="eve",
            language="en",
            codec="alaw",
            sample_rate=8000,
            bit_rate=128000,
        )
        self.assertEqual(payload["output_format"], {"codec": "alaw", "sample_rate": 8000})

    def test_unknown_voice_is_passed_through(self) -> None:
        self.assertEqual(normalize_voice_id("nlbqfwie"), "nlbqfwie")
        self.assertEqual(normalize_voice_id("carina"), "carina")
        self.assertEqual(normalize_voice_id("  "), "eve")


class OptionCoercionTests(unittest.TestCase):
    def test_speed_range(self) -> None:
        self.assertEqual(resolve_speed(1.2), 1.2)
        self.assertEqual(resolve_speed("0.7"), 0.7)
        self.assertEqual(resolve_speed(1.5), 1.5)
        self.assertEqual(resolve_speed(0.5), 1.0)
        self.assertEqual(resolve_speed(2.0), 1.0)

    def test_bool_coercion(self) -> None:
        self.assertTrue(coerce_bool("true"))
        self.assertTrue(coerce_bool("on"))
        self.assertFalse(coerce_bool("false"))
        self.assertFalse(coerce_bool(None, False))

    def test_codec_fallback(self) -> None:
        self.assertEqual(resolve_codec("alaw"), "alaw")
        self.assertEqual(resolve_codec("ogg"), "mp3")

    def test_replace_json_and_limits(self) -> None:
        self.assertEqual(parse_replace('{"nginx": "/ˈɛndʒɪn ˈɛks/"}'), {"nginx": "/ˈɛndʒɪn ˈɛks/"})
        self.assertIsNone(parse_replace({}))
        with self.assertRaises(ValueError):
            parse_replace("[]")
        with self.assertRaises(ValueError):
            parse_replace({"": "x"})

    def test_text_validation(self) -> None:
        self.assertEqual(validate_text("hi"), "hi")
        with self.assertRaises(ValueError):
            validate_text("   ")
        with self.assertRaises(ValueError):
            validate_text("x" * (MAX_TTS_TEXT_CHARS + 1))


class ErrorMappingTests(unittest.TestCase):
    def test_documented_status_codes(self) -> None:
        self.assertIn("400", describe_http_error(400))
        self.assertIn("401", describe_http_error(401))
        self.assertIn("404", describe_http_error(404))
        self.assertIn("custom-voices", describe_http_error(404))
        self.assertIn("429", describe_http_error(429))
        self.assertIn("503", describe_http_error(503))


class VoiceParseTests(unittest.TestCase):
    def test_builtin_shape(self) -> None:
        parsed = parse_builtin_voices(
            {
                "voices": [
                    {"voice_id": "eve", "name": "Eve", "language": "en"},
                    {"voice_id": "carina", "name": "Carina", "language": "en"},
                ]
            }
        )
        self.assertEqual(parsed["eve"]["name"], "Eve")
        self.assertEqual(parsed["eve"]["source"], "builtin")
        self.assertEqual(parsed["carina"]["name"], "Carina")
        self.assertNotIn("Eve", parsed)  # IDs are not lowercased from display names

    def test_does_not_lowercase_custom_ids(self) -> None:
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
        self.assertIn("nlbqfwie", parsed)
        self.assertEqual(parsed["nlbqfwie"]["source"], "custom")
        self.assertIn("custom", format_voice_label("nlbqfwie", parsed["nlbqfwie"]))


if __name__ == "__main__":
    unittest.main()
