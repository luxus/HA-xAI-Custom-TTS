"""Grok HTTP client for https://api.x.ai/v1 (no Home Assistant imports)."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .api_helpers import (
    build_live_search_tools,
    extract_responses_citations,
    fallback_chat_models,
    format_citations,
    parse_models_list,
)
from .const import (
    DEFAULT_GROK_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    GROK_REQUEST_TIMEOUT,
    LIVE_SEARCH_OFF,
    RECOMMENDED_IMAGE_GENERATION_MODEL,
    XAI_CHAT_COMPLETIONS_URL,
    XAI_IMAGES_GENERATIONS_URL,
    XAI_MODELS_URL,
    XAI_RESPONSES_URL,
)

_LOGGER = logging.getLogger(__name__)


class GrokChatError(Exception):
    """Grok inference failed or returned empty prose."""


@dataclass
class RawToolCall:
    """One function tool call from chat.completions."""

    id: str
    name: str
    arguments_json: str


@dataclass
class ChatTurn:
    """One non-streaming chat.completions turn."""

    content: str | None
    tool_calls: list[RawToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: Mapping[str, Any] | None = None


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


def extract_usage(payload: Any) -> tuple[int, int]:
    """Return (prompt_tokens, completion_tokens) from chat or responses JSON."""
    usage = getattr(payload, "usage", None)
    if usage is None and isinstance(payload, Mapping):
        usage = payload.get("usage")
    if not usage:
        return 0, 0
    if isinstance(usage, Mapping):
        prompt = usage.get("prompt_tokens")
        if prompt is None:
            prompt = usage.get("input_tokens", 0) or 0
        completion = usage.get("completion_tokens")
        if completion is None:
            completion = usage.get("output_tokens", 0) or 0
        return int(prompt or 0), int(completion or 0)
    prompt = getattr(usage, "prompt_tokens", None)
    if prompt is None:
        prompt = getattr(usage, "input_tokens", 0) or 0
    completion = getattr(usage, "completion_tokens", None)
    if completion is None:
        completion = getattr(usage, "output_tokens", 0) or 0
    return int(prompt or 0), int(completion or 0)


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
    messages: Sequence[Mapping[str, Any]],
    *,
    model: str = DEFAULT_GROK_MODEL,
    live_search: str = LIVE_SEARCH_OFF,
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    reasoning_effort: str | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """JSON body for POST /v1/responses (optional live search server tools)."""
    instructions = system_prompt or DEFAULT_SYSTEM_PROMPT
    inputs: list[dict[str, Any]] = []
    sys_parts: list[str] = []
    if system_prompt:
        sys_parts.append(system_prompt)
    for item in messages:
        role = item.get("role")
        content = item.get("content")
        if role == "system":
            if isinstance(content, str) and content:
                if system_prompt:
                    sys_parts.append(content)
                else:
                    instructions = content
            continue
        if role not in {"user", "assistant"}:
            continue
        if isinstance(content, list):
            inputs.append({"role": role, "content": content})
        elif isinstance(content, str):
            inputs.append({"role": role, "content": content})
    if sys_parts:
        instructions = "\n\n".join(sys_parts)
    if not inputs:
        raise GrokChatError("no user input for Grok")
    payload: dict[str, Any] = {
        "model": model,
        "input": inputs,
        "instructions": instructions,
        "store": False,
        "stream": False,
    }
    tools = build_live_search_tools(live_search)
    if tools:
        payload["tools"] = tools
    if max_tokens is not None:
        payload["max_output_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if (
        reasoning_effort
        and reasoning_effort != "none"
        and "reasoning" in model.lower()
    ):
        payload["reasoning"] = {"effort": reasoning_effort}
    return payload


def chat_completions_payload(
    messages: Sequence[Mapping[str, Any]],
    *,
    model: str = DEFAULT_GROK_MODEL,
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    reasoning_effort: str | None = None,
    user: str | None = None,
) -> dict[str, Any]:
    """JSON body for POST /v1/chat/completions with optional HA function tools."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": list(messages),
        "stream": False,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if user:
        payload["user"] = user
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice or "auto"
    if (
        reasoning_effort
        and reasoning_effort != "none"
        and "reasoning" in model.lower()
    ):
        payload["reasoning_effort"] = reasoning_effort
    return payload


def parse_chat_completion(payload: Mapping[str, Any]) -> ChatTurn:
    """Parse one chat.completions JSON body into a ChatTurn."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise GrokChatError("Grok chat completions returned no choices")
    first = choices[0] if isinstance(choices[0], Mapping) else {}
    message = first.get("message") if isinstance(first, Mapping) else None
    if not isinstance(message, Mapping):
        message = {}
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        content = _content_to_text(content)
    tool_calls: list[RawToolCall] = []
    raw_tcs = message.get("tool_calls") or []
    if isinstance(raw_tcs, list):
        for tc in raw_tcs:
            if not isinstance(tc, Mapping):
                continue
            fn = tc.get("function") if isinstance(tc.get("function"), Mapping) else {}
            args = fn.get("arguments") if isinstance(fn, Mapping) else "{}"
            if not isinstance(args, str):
                args = json.dumps(args or {})
            tool_calls.append(
                RawToolCall(
                    id=str(tc.get("id") or ""),
                    name=str((fn or {}).get("name") or ""),
                    arguments_json=args,
                )
            )
    p_tok, c_tok = extract_usage(payload)
    return ChatTurn(
        content=content if isinstance(content, str) else (str(content) if content else None),
        tool_calls=tool_calls,
        finish_reason=str(first.get("finish_reason") or "") or None,
        prompt_tokens=p_tok,
        completion_tokens=c_tok,
        raw=payload,
    )


def _raise_http(response: Any) -> None:
    status = getattr(response, "status_code", 200)
    if status >= 400:
        raise_for_status = getattr(response, "raise_for_status", None)
        if callable(raise_for_status):
            raise_for_status()
        text = getattr(response, "text", "") or ""
        raise GrokChatError(f"xAI HTTP {status}: {text[:240]}")


def _json_payload(response: Any) -> Mapping[str, Any]:
    payload = response.json()
    if not isinstance(payload, Mapping):
        raise GrokChatError("Grok response was not JSON")
    return payload


async def async_chat_complete(
    client: Any,
    headers: Mapping[str, str],
    messages: Sequence[Mapping[str, str]],
    *,
    model: str = DEFAULT_GROK_MODEL,
    timeout: float = GROK_REQUEST_TIMEOUT,
) -> str:
    """Call xAI Responses and return Grok's assistant text (no tools)."""
    request_headers = {**dict(headers), "Content-Type": "application/json"}
    response = await client.post(
        XAI_RESPONSES_URL,
        headers=request_headers,
        json=responses_payload(messages, model=model),
        timeout=timeout,
    )
    _raise_http(response)
    return extract_grok_text(_json_payload(response))


async def async_responses_completion(
    client: Any,
    headers: Mapping[str, str],
    *,
    model: str,
    messages: Sequence[Mapping[str, Any]],
    system_prompt: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    live_search: str = LIVE_SEARCH_OFF,
    show_citations: bool = True,
    reasoning_effort: str | None = None,
    timeout: float = GROK_REQUEST_TIMEOUT,
) -> tuple[str, int, int]:
    """Call Responses API (xAI live web/X search). Returns text, prompt_tok, completion_tok."""
    request_headers = {**dict(headers), "Content-Type": "application/json"}
    body = responses_payload(
        messages,
        model=model,
        live_search=live_search,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        reasoning_effort=reasoning_effort,
        system_prompt=system_prompt,
    )
    _LOGGER.debug(
        "responses.create model=%s live_search=%s tools=%s",
        model,
        live_search,
        [t.get("type") for t in body.get("tools") or []],
    )
    response = await client.post(
        XAI_RESPONSES_URL,
        headers=request_headers,
        json=body,
        timeout=timeout,
    )
    _raise_http(response)
    payload = _json_payload(response)
    try:
        text = extract_grok_text(payload)
    except GrokChatError:
        text = ""
    if show_citations:
        text = text + format_citations(extract_responses_citations(payload))
    p_tok, c_tok = extract_usage(payload)
    return text, p_tok, c_tok


async def async_chat_completions(
    client: Any,
    headers: Mapping[str, str],
    *,
    model: str,
    messages: Sequence[Mapping[str, Any]],
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    reasoning_effort: str | None = None,
    user: str | None = None,
    timeout: float = GROK_REQUEST_TIMEOUT,
) -> ChatTurn:
    """Call chat.completions (HA function tools live here)."""
    request_headers = {**dict(headers), "Content-Type": "application/json"}
    body = chat_completions_payload(
        messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        tools=tools,
        tool_choice=tool_choice,
        reasoning_effort=reasoning_effort,
        user=user,
    )
    _LOGGER.debug("chat.completions.create model=%s tools=%s", model, bool(tools))
    response = await client.post(
        XAI_CHAT_COMPLETIONS_URL,
        headers=request_headers,
        json=body,
        timeout=timeout,
    )
    _raise_http(response)
    return parse_chat_completion(_json_payload(response))


async def async_list_chat_models(
    client: Any,
    headers: Mapping[str, str],
    *,
    timeout: float = 15.0,
) -> list[str]:
    """Fetch chat-capable model ids from GET /v1/models."""
    try:
        response = await client.get(
            XAI_MODELS_URL, headers=dict(headers), timeout=timeout
        )
        _raise_http(response)
        models = parse_models_list(_json_payload(response))
        if models:
            _LOGGER.debug("xAI chat models: %s", models)
            return models
        _LOGGER.warning("xAI models list returned no chat models; using fallbacks")
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Could not list xAI models (%s); using fallbacks", err)
    return fallback_chat_models()


async def async_generate_image(
    client: Any,
    headers: Mapping[str, str],
    *,
    prompt: str,
    model: str = RECOMMENDED_IMAGE_GENERATION_MODEL,
    size: str = "1024x1024",
    quality: str = "standard",
    style: str = "vivid",
    timeout: float = 120.0,
) -> dict[str, Any]:
    """POST /v1/images/generations. Returns url + optional revised_prompt."""
    request_headers = {**dict(headers), "Content-Type": "application/json"}
    response = await client.post(
        XAI_IMAGES_GENERATIONS_URL,
        headers=request_headers,
        json={
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "style": style,
            "response_format": "url",
            "n": 1,
        },
        timeout=timeout,
    )
    _raise_http(response)
    payload = _json_payload(response)
    data = payload.get("data") or []
    if not data or not isinstance(data, list):
        raise GrokChatError("Image generation returned no data")
    first = data[0] if isinstance(data[0], Mapping) else {}
    url = first.get("url") if isinstance(first, Mapping) else None
    result: dict[str, Any] = {"url": url, "model": model}
    if isinstance(first, Mapping) and first.get("revised_prompt"):
        result["revised_prompt"] = first["revised_prompt"]
    if isinstance(first, Mapping) and first.get("b64_json"):
        result["b64_json"] = first["b64_json"]
    return result
