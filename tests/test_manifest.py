"""Manifest / HACS / strings checks (no Home Assistant import)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "custom_components" / "spacexai" / "manifest.json").read_text())
STRINGS = json.loads((ROOT / "custom_components" / "spacexai" / "strings.json").read_text())
HACS = json.loads((ROOT / "hacs.json").read_text())


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
