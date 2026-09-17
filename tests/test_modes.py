"""Interaction mode + live search + model picker routing (no Home Assistant)."""

from __future__ import annotations

from spacexai.api_helpers import (
    build_live_search_tools,
    filter_chat_model_ids,
    format_citations,
    inject_search_brief,
    looks_like_simple_query,
    parse_models_list,
    plan_turn,
    should_use_live_search,
)
from spacexai.const import (
    CONF_AUTO_MODEL_ROUTING,
    CONF_CHAT_MODEL,
    CONF_FAST_MODEL,
    CONF_INTERACTION_MODE,
    CONF_LIVE_SEARCH,
    CONF_LLM_HASS_API,
    LIVE_SEARCH_FULL,
    LIVE_SEARCH_WEB,
    MODE_CHAT_ONLY,
    MODE_PIPELINE,
    MODE_TOOLS,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_FAST_MODEL,
    XAI_VOICES,
)
from spacexai.grok import responses_payload
from spacexai.voices import fallback_voices


def test_voice_catalog_has_twenty_five_plus() -> None:
    assert len(XAI_VOICES) >= 25
    voices = fallback_voices()
    assert len(voices) >= 25
    for vid in ("eve", "ara", "rex", "luna", "zagan", "kepler"):
        assert vid in voices


def test_tools_mode_enables_hass_api_by_default() -> None:
    plan = plan_turn(
        "turn on the kitchen light",
        {
            CONF_INTERACTION_MODE: MODE_TOOLS,
            CONF_LLM_HASS_API: ["assist"],
            CONF_LIVE_SEARCH: "off",
        },
    )
    assert plan["mode"] == MODE_TOOLS
    assert plan["tools_enabled"] is True
    assert plan["try_pipeline"] is False
    assert plan["use_search"] is False
    assert plan["llm_hass_api"] == ["assist"]


def test_chat_only_disables_tools_even_with_assist_api() -> None:
    plan = plan_turn(
        "turn on the kitchen light",
        {
            CONF_INTERACTION_MODE: MODE_CHAT_ONLY,
            CONF_LLM_HASS_API: ["assist"],
            CONF_LIVE_SEARCH: "off",
        },
    )
    assert plan["tools_enabled"] is False
    assert plan["llm_hass_api"] == []
    assert plan["try_pipeline"] is False


def test_pipeline_tries_ha_intent_first() -> None:
    plan = plan_turn(
        "turn on the kitchen light",
        {CONF_INTERACTION_MODE: MODE_PIPELINE, CONF_LLM_HASS_API: ["assist"]},
    )
    assert plan["try_pipeline"] is True
    assert plan["tools_enabled"] is True


def test_none_sentinel_disables_tools() -> None:
    plan = plan_turn(
        "hello",
        {CONF_INTERACTION_MODE: MODE_TOOLS, CONF_LLM_HASS_API: ["none"]},
    )
    assert plan["tools_enabled"] is False


def test_live_search_tools_mode_allow_list_only() -> None:
    assert (
        should_use_live_search(
            "turn on the lights",
            interaction_mode=MODE_TOOLS,
            live_search=LIVE_SEARCH_WEB,
        )
        is False
    )
    assert (
        should_use_live_search(
            "what's the news today",
            interaction_mode=MODE_TOOLS,
            live_search=LIVE_SEARCH_WEB,
        )
        is True
    )


def test_live_search_chat_only_always_when_enabled() -> None:
    assert (
        should_use_live_search(
            "tell me a joke",
            interaction_mode=MODE_CHAT_ONLY,
            live_search=LIVE_SEARCH_WEB,
        )
        is True
    )
    assert (
        should_use_live_search(
            "tell me a joke",
            interaction_mode=MODE_CHAT_ONLY,
            live_search="off",
        )
        is False
    )


def test_live_search_pipeline_deny_list() -> None:
    assert (
        should_use_live_search(
            "hello there",
            interaction_mode=MODE_PIPELINE,
            live_search=LIVE_SEARCH_FULL,
        )
        is False
    )
    assert (
        should_use_live_search(
            "who won the game",
            interaction_mode=MODE_PIPELINE,
            live_search=LIVE_SEARCH_FULL,
        )
        is True
    )
    # Non-deny, non-allow in pipeline defaults True
    assert (
        should_use_live_search(
            "explain photosynthesis",
            interaction_mode=MODE_PIPELINE,
            live_search=LIVE_SEARCH_WEB,
        )
        is True
    )


def test_auto_routing_picks_fast_model_for_short_commands() -> None:
    plan = plan_turn(
        "turn on the kitchen light",
        {
            CONF_INTERACTION_MODE: MODE_TOOLS,
            CONF_LLM_HASS_API: ["assist"],
            CONF_AUTO_MODEL_ROUTING: True,
            CONF_CHAT_MODEL: RECOMMENDED_CHAT_MODEL,
            CONF_FAST_MODEL: RECOMMENDED_FAST_MODEL,
        },
    )
    assert looks_like_simple_query("turn on the kitchen light")
    assert plan["model"] == RECOMMENDED_FAST_MODEL


def test_search_query_stays_on_primary_model() -> None:
    plan = plan_turn(
        "what's the news today",
        {
            CONF_AUTO_MODEL_ROUTING: True,
            CONF_CHAT_MODEL: "grok-primary",
            CONF_FAST_MODEL: "grok-fast",
            CONF_LIVE_SEARCH: LIVE_SEARCH_WEB,
            CONF_INTERACTION_MODE: MODE_TOOLS,
        },
    )
    assert plan["model"] == "grok-primary"
    assert plan["use_search"] is True


def test_build_live_search_tools_web_x_full() -> None:
    assert build_live_search_tools("off") == []
    assert build_live_search_tools("web") == [{"type": "web_search"}]
    assert build_live_search_tools("x") == [{"type": "x_search"}]
    assert build_live_search_tools("full") == [
        {"type": "web_search"},
        {"type": "x_search"},
    ]


def test_responses_payload_includes_search_tools() -> None:
    payload = responses_payload(
        [{"role": "user", "content": "news today"}],
        model="grok-4",
        live_search=LIVE_SEARCH_FULL,
        system_prompt="search well",
    )
    assert payload["tools"] == [{"type": "web_search"}, {"type": "x_search"}]
    assert payload["instructions"] == "search well"


def test_citations_footer() -> None:
    footer = format_citations(["https://example.com/a", {"url": "https://example.com/a"}])
    assert "Sources:" in footer
    assert footer.count("https://example.com/a") == 1


def test_inject_search_brief_into_system() -> None:
    messages = [
        {"role": "system", "content": "You are Grok."},
        {"role": "user", "content": "score?"},
    ]
    out = inject_search_brief(messages, "Final: 3-1")
    assert "Live search results" in out[0]["content"]
    assert "Final: 3-1" in out[0]["content"]
    assert out[1]["content"] == "score?"


def test_parse_models_list_filters_non_chat() -> None:
    models = parse_models_list(
        {
            "data": [
                {"id": "grok-4"},
                {"id": "grok-imagine-image"},
                {"id": "grok-tts"},
                {"id": "grok-4.3-latest"},
            ]
        }
    )
    assert "grok-4" in models
    assert "grok-4.3-latest" in models
    assert "grok-imagine-image" not in models
    assert "grok-tts" not in models
    assert filter_chat_model_ids(["grok-stt", "grok-3-mini"]) == ["grok-3-mini"]
