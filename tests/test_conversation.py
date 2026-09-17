"""Grok conversation client smoke tests (no live keys, no Home Assistant)."""

from __future__ import annotations

import pytest

from spacexai.const import (
    CONVERSATION_ENTITY_NAME,
    DEFAULT_GROK_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    PLATFORMS,
    XAI_RESPONSES_URL,
)
from spacexai.grok import (
    GrokChatError,
    async_chat_complete,
    build_messages,
    extract_grok_text,
    messages_from_chat_log,
    responses_payload,
)

from .fakes import FakeHttpxClient, FakeHttpxResponse


def test_platforms_load_conversation_and_tts() -> None:
    assert PLATFORMS == ("conversation", "tts")
    assert CONVERSATION_ENTITY_NAME == "Grok"


def test_extract_responses_api_prose() -> None:
    payload = {
        "object": "response",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": "Hello from Grok, living in HA."}
                ],
            }
        ],
    }
    assert extract_grok_text(payload) == "Hello from Grok, living in HA."


def test_extract_chat_completions_prose() -> None:
    payload = {
        "choices": [
            {"message": {"role": "assistant", "content": "Chat-completions Grok prose."}}
        ]
    }
    assert extract_grok_text(payload) == "Chat-completions Grok prose."


def test_extract_empty_raises() -> None:
    with pytest.raises(GrokChatError):
        extract_grok_text({"output": [], "choices": []})


def test_build_messages_includes_user() -> None:
    messages = build_messages("What is the weather?")
    assert messages[0]["role"] == "system"
    assert DEFAULT_SYSTEM_PROMPT in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "What is the weather?"}


class _Item:
    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content


class _Log:
    def __init__(self, content: list[_Item]) -> None:
        self.content = content


def test_messages_from_chat_log() -> None:
    log = _Log(
        [
            _Item("user", "Hi"),
            _Item("assistant", "Hello"),
            _Item("user", "Tell a joke"),
        ]
    )
    messages = messages_from_chat_log("Tell a joke", log)
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[-1]["content"] == "Tell a joke"


def test_responses_payload_uses_instructions() -> None:
    payload = responses_payload(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ],
        model=DEFAULT_GROK_MODEL,
    )
    assert payload["model"] == DEFAULT_GROK_MODEL
    assert payload["instructions"] == "sys"
    assert payload["input"] == [{"role": "user", "content": "hello"}]
    assert payload["store"] is False


@pytest.mark.asyncio
async def test_async_chat_complete_returns_real_prose() -> None:
    client = FakeHttpxClient(
        FakeHttpxResponse(
            200,
            {
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "The lights are already on."}],
                    }
                ]
            },
        ),
        expected_url=XAI_RESPONSES_URL,
    )
    text = await async_chat_complete(
        client,
        {"Authorization": "Bearer test-token"},
        build_messages("Are the lights on?"),
    )
    assert text == "The lights are already on."
    assert text.strip()  # not an empty stub
    assert client.calls[0]["url"] == XAI_RESPONSES_URL
    headers = client.calls[0]["headers"]
    assert headers["Authorization"] == "Bearer test-token"


@pytest.mark.asyncio
async def test_async_chat_complete_rejects_empty() -> None:
    client = FakeHttpxClient(FakeHttpxResponse(200, {"output": []}))
    with pytest.raises(GrokChatError):
        await async_chat_complete(
            client,
            {"Authorization": "Bearer x"},
            build_messages("hi"),
        )
