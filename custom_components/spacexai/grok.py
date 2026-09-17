"""Grok chat client for https://api.x.ai/v1 (no Home Assistant imports)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .const import (
    DEFAULT_GROK_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    XAI_RESPONSES_URL,
)


class GrokChatError(Exception):
    """Grok inference failed or returned empty prose."""


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, Mapping):
                text = part.get("text") or part.get("content") or ""
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def extract_grok_text(payload: Mapping[str, Any]) -> str:
    """Pull assistant prose from Responses or Chat Completions JSON."""
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = payload.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, Mapping):
                continue
            item_type = item.get("type")
            if item_type in {None, "message"} and item.get("role") in {
                None,
                "assistant",
            }:
                parts.append(_content_to_text(item.get("content")))
            elif item_type == "output_text":
                parts.append(str(item.get("text") or ""))
        text = "".join(parts).strip()
        if text:
            return text

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0] if isinstance(choices[0], Mapping) else {}
        message = first.get("message") if isinstance(first, Mapping) else None
        if isinstance(message, Mapping):
            text = _content_to_text(message.get("content")).strip()
            if text:
                return text
        text = _content_to_text(first.get("text") if isinstance(first, Mapping) else None)
        if text.strip():
            return text.strip()

    raise GrokChatError("Grok returned empty content")


def build_messages(
    user_text: str,
    *,
    history: Sequence[Mapping[str, str]] | None = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> list[dict[str, str]]:
    """Build OpenAI-style messages, always including the latest user turn."""
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history:
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content})
    if not any(m["role"] == "user" for m in messages):
        messages.append({"role": "user", "content": user_text})
    elif user_text and messages[-1]["role"] != "user":
        if not any(m["content"] == user_text for m in messages if m["role"] == "user"):
            messages.append({"role": "user", "content": user_text})
    return messages


def messages_from_chat_log(
    user_text: str,
    chat_log: Any | None,
    *,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> list[dict[str, str]]:
    """Convert a Home Assistant ChatLog (or similar) into messages."""
    history: list[dict[str, str]] = []
    content_list = getattr(chat_log, "content", None) if chat_log is not None else None
    if content_list:
        for item in content_list:
            role = getattr(item, "role", None)
            content = getattr(item, "content", None)
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                history.append({"role": role, "content": content})
    return build_messages(user_text, history=history, system_prompt=system_prompt)


def responses_payload(
    messages: Sequence[Mapping[str, str]],
    *,
    model: str = DEFAULT_GROK_MODEL,
) -> dict[str, Any]:
    """JSON body for POST /v1/responses."""
    instructions = DEFAULT_SYSTEM_PROMPT
    inputs: list[dict[str, str]] = []
    for item in messages:
        role = item.get("role")
        content = item.get("content")
        if not isinstance(content, str):
            continue
        if role == "system":
            instructions = content
            continue
        if role in {"user", "assistant"}:
            inputs.append({"role": role, "content": content})
    if not inputs:
        raise GrokChatError("no user input for Grok")
    return {
        "model": model,
        "input": inputs,
        "instructions": instructions,
        "store": False,
        "stream": False,
    }


async def async_chat_complete(
    client: Any,
    headers: Mapping[str, str],
    messages: Sequence[Mapping[str, str]],
    *,
    model: str = DEFAULT_GROK_MODEL,
    timeout: float = 60.0,
) -> str:
    """Call xAI Responses and return Grok's assistant text."""
    request_headers = {**dict(headers), "Content-Type": "application/json"}
    response = await client.post(
        XAI_RESPONSES_URL,
        headers=request_headers,
        json=responses_payload(messages, model=model),
        timeout=timeout,
    )
    if getattr(response, "status_code", 200) >= 400:
        raise_for_status = getattr(response, "raise_for_status", None)
        if callable(raise_for_status):
            raise_for_status()
    payload = response.json()
    if not isinstance(payload, Mapping):
        raise GrokChatError("Grok response was not JSON")
    return extract_grok_text(payload)
