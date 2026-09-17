"""Assist LLM HASS API tools routing (mocked HTTP, no live keys)."""

from __future__ import annotations

import json

import pytest

from spacexai.const import XAI_CHAT_COMPLETIONS_URL
from spacexai.grok import chat_completions_payload, parse_chat_completion
from spacexai.tool_loop import run_tool_loop, run_tool_loop_with_fallback, tool_result_payload
from spacexai.tool_schema import format_function_tool, sanitize_tool_schema

from .fakes import FakeHttpxClient, FakeHttpxResponse


def _turn_on_response() -> dict:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_light_1",
                            "type": "function",
                            "function": {
                                "name": "HassTurnOn",
                                "arguments": json.dumps(
                                    {"name": "kitchen light", "domain": "light"}
                                ),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 40, "completion_tokens": 12},
    }


def _final_speech_response(text: str = "The kitchen light is on.") -> dict:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 80, "completion_tokens": 16},
    }


def test_sanitize_timer_anyof_merges_object_branches() -> None:
    """HassStartTimer-style anyOf must become a single object for xAI."""
    raw = {
        "anyOf": [
            {"type": "object", "properties": {"name": {"type": "string"}}},
            {
                "type": "object",
                "properties": {
                    "hours": {"type": "integer"},
                    "minutes": {"type": "integer"},
                    "seconds": {"type": "integer"},
                },
            },
        ]
    }
    cleaned = sanitize_tool_schema(raw)
    assert cleaned["type"] == "object"
    assert "name" in cleaned["properties"]
    assert "hours" in cleaned["properties"]
    assert "anyOf" not in cleaned


def test_format_function_tool_is_openai_shape() -> None:
    tool = format_function_tool(
        "HassTurnOff",
        "Turn off a device",
        {"type": "object", "properties": {"name": {"type": "string"}}},
    )
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "HassTurnOff"
    assert tool["function"]["parameters"]["type"] == "object"


def test_chat_completions_payload_includes_hass_tools() -> None:
    tools = [
        format_function_tool(
            "HassTurnOn",
            "Turn on a device",
            {"type": "object", "properties": {"name": {"type": "string"}}},
        )
    ]
    payload = chat_completions_payload(
        [{"role": "user", "content": "turn on the kitchen light"}],
        model="grok-4",
        tools=tools,
    )
    assert payload["tools"] == tools
    assert payload["tool_choice"] == "auto"
    assert payload["stream"] is False


def test_parse_chat_completion_tool_calls() -> None:
    turn = parse_chat_completion(_turn_on_response())
    assert turn.tool_calls[0].name == "HassTurnOn"
    assert json.loads(turn.tool_calls[0].arguments_json)["name"] == "kitchen light"


def test_tool_result_payload_is_real_json_not_stub() -> None:
    payload = tool_result_payload({"success": True, "states": ["light.kitchen=on"]})
    parsed = json.loads(payload)
    assert parsed["success"] is True
    assert "kitchen" in parsed["states"][0]


@pytest.mark.asyncio
async def test_tool_loop_executes_hass_turn_on_then_speaks() -> None:
    recorded: list[tuple[str, dict]] = []

    async def execute_tool(name: str, args: dict) -> dict:
        recorded.append((name, args))
        return {"success": True, "entity_id": "light.kitchen", "state": "on"}

    client = FakeHttpxClient(
        responses=[
            FakeHttpxResponse(200, _turn_on_response()),
            FakeHttpxResponse(200, _final_speech_response()),
        ]
    )
    tools = [
        format_function_tool(
            "HassTurnOn",
            "Turns on a light or other entity exposed to Assist",
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "domain": {"type": "string"},
                },
            },
        )
    ]
    result = await run_tool_loop(
        client,
        {"Authorization": "Bearer test-token"},
        model="grok-4",
        messages=[{"role": "user", "content": "turn on the kitchen light"}],
        execute_tool=execute_tool,
        tools=tools,
    )
    assert recorded == [("HassTurnOn", {"name": "kitchen light", "domain": "light"})]
    assert result.speech == "The kitchen light is on."
    assert result.tool_invocations[0]["name"] == "HassTurnOn"
    assert result.tool_invocations[0]["result"]["state"] == "on"

    first = client.calls[0]
    assert first["url"] == XAI_CHAT_COMPLETIONS_URL
    assert first["headers"]["Authorization"] == "Bearer test-token"
    assert first["json"]["tools"][0]["function"]["name"] == "HassTurnOn"

    second = client.calls[1]
    roles = [m["role"] for m in second["json"]["messages"]]
    assert "tool" in roles
    tool_msg = next(m for m in second["json"]["messages"] if m["role"] == "tool")
    body = json.loads(tool_msg["content"])
    assert body["success"] is True
    assert body["entity_id"] == "light.kitchen"
    assert "stub" not in tool_msg["content"].lower()


@pytest.mark.asyncio
async def test_chat_only_sends_no_tools() -> None:
    client = FakeHttpxClient(
        FakeHttpxResponse(200, _final_speech_response("Hello there."))
    )

    async def execute_tool(name: str, args: dict) -> dict:
        raise AssertionError("chat_only must not execute HA tools")

    result = await run_tool_loop(
        client,
        {"Authorization": "Bearer x"},
        model="grok-4",
        messages=[{"role": "user", "content": "turn on the lights"}],
        execute_tool=None,
        tools=None,
    )
    assert result.speech == "Hello there."
    assert result.tool_invocations == []
    assert "tools" not in client.calls[0]["json"]


@pytest.mark.asyncio
async def test_fallback_model_used_when_primary_fails() -> None:
    client = FakeHttpxClient(
        responses=[
            FakeHttpxResponse(500, {"error": "boom"}),
            FakeHttpxResponse(200, _final_speech_response("Fallback ok.")),
        ]
    )
    result = await run_tool_loop_with_fallback(
        client,
        {"Authorization": "Bearer x"},
        models=["grok-primary", "grok-fallback"],
        messages=[{"role": "user", "content": "hi"}],
        execute_tool=None,
        tools=None,
    )
    assert result.speech == "Fallback ok."
    assert result.model == "grok-fallback"
    assert client.calls[0]["json"]["model"] == "grok-primary"
    assert client.calls[1]["json"]["model"] == "grok-fallback"
