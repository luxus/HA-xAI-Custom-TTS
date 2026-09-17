"""Manifest / HACS / strings checks (no Home Assistant import)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "spacexai"
MANIFEST = json.loads((INTEGRATION / "manifest.json").read_text())
STRINGS = json.loads((INTEGRATION / "strings.json").read_text())
EN = json.loads((INTEGRATION / "translations" / "en.json").read_text())
HACS = json.loads((ROOT / "hacs.json").read_text())

# hassfest TRANSLATIONS: reject http(s) and www. in string values.
_BARE_URL = re.compile(r"https?://|www\.", re.IGNORECASE)


def test_manifest_requires_ha_spacexai_auth() -> None:
    reqs = MANIFEST["requirements"]
    assert any("ha-spacexai-auth" in item for item in reqs)
    assert any(
        "git+https://github.com/luxus/ha-spacexai-auth.git@main" in item for item in reqs
    )
    assert any("voluptuous-openapi" in item for item in reqs)
    assert all("openai" not in item for item in reqs)
    assert all(" " not in item for item in reqs)


def test_manifest_domain_and_platforms() -> None:
    assert MANIFEST["domain"] == "spacexai"
    assert MANIFEST["name"] == "SpaceXAI"
    assert MANIFEST["config_flow"] is True
    assert "conversation" in MANIFEST["dependencies"]
    assert "tts" in MANIFEST["dependencies"]
    assert "stt" in MANIFEST["dependencies"]
    assert "application_credentials" not in MANIFEST.get("dependencies", [])


def test_manifest_points_at_ha_spacexai_repo() -> None:
    assert MANIFEST["documentation"] == "https://github.com/luxus/ha-spacexai"
    assert MANIFEST["issue_tracker"] == "https://github.com/luxus/ha-spacexai/issues"


def test_manifest_keys_sorted_domain_name_then_alpha() -> None:
    keys = list(MANIFEST)
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])


def _assert_no_bare_urls(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _assert_no_bare_urls(nested, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_no_bare_urls(nested, f"{path}[{index}]")
        return
    if isinstance(value, str):
        assert _BARE_URL.search(value) is None, f"bare URL in {path}: {value!r}"


def test_strings_and_en_have_no_bare_urls() -> None:
    _assert_no_bare_urls(STRINGS, "strings.json")
    _assert_no_bare_urls(EN, "translations/en.json")
    description = STRINGS["options"]["step"]["conversation"]["description"]
    assert "xAI models API" in description
    assert description == EN["options"]["step"]["conversation"]["description"]


def test_hacs_keeps_repo_layout() -> None:
    assert HACS["name"] == "SpaceXAI"
    assert HACS["filename"] == "spacexai.zip"
    assert HACS["content_in_root"] is False


def test_oauth_failed_exposes_retry_api_key_and_abort() -> None:
    options = STRINGS["selector"]["oauth_recovery"]["options"]
    assert "retry_oauth" in options
    assert "api_key" in options
    assert "abort" in options
    assert "oauth_recovery" in STRINGS["config"]["step"]["oauth_failed"]["data"]


def test_reauth_confirm_has_auth_method_selector() -> None:
    assert "auth_method" in STRINGS["config"]["step"]["reauth_confirm"]["data"]


def test_reauth_abort_reason_is_translated() -> None:
    assert "reauth_successful" in STRINGS["config"]["abort"]
    assert "oauth_failed" in STRINGS["config"]["abort"]


def test_conversation_options_and_services_are_translated() -> None:
    conv = STRINGS["options"]["step"]["conversation"]["data"]
    assert "llm_hass_api" in conv
    assert "interaction_mode" in conv
    assert "live_search" in conv
    assert "chat_model" in conv
    assert "fast_model" in conv
    assert "fallback_model" in conv
    for svc in (
        "ask",
        "photo_analysis",
        "home_briefing",
        "generate_image",
        "generate_content",
    ):
        assert svc in STRINGS["services"]
