"""Convert ChatLog items to OpenAI-style messages (no Home Assistant).

Home Assistant ``ToolInput`` objects are unhashable (they carry a dict of
``tool_args``). Never use ``hash(tool_call)`` as a fallback id — Python
evaluates ``getattr`` defaults before the call, so that would raise even when
``.id`` exists.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from .tool_loop import tool_result_payload


def json_safe_tool_call_id(tool_call: Any, index: int = 0) -> str:
    """Return a JSON-safe tool-call id. Never hashes the object."""
    raw: Any
    if isinstance(tool_call, dict):
        raw = tool_call.get("id") or tool_call.get("tool_call_id")
    else:
        raw = getattr(tool_call, "id", None) or getattr(tool_call, "tool_call_id", None)
    if raw is not None:
        text = str(raw).strip()
        if text:
            return text
    return f"call_{index}_{uuid.uuid4().hex[:12]}"


def _arguments_json(args: Any) -> str:
    if isinstance(args, str):
        return args
    try:
        return json.dumps(args if args is not None else {})
    except TypeError:
        return json.dumps({"value": str(args)})


def _function_payload(name: str, arguments: Any, call_id: str) -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": _arguments_json(arguments),
        },
    }


def _convert_tool_call(tool_call: Any, index: int) -> dict[str, Any] | None:
    call_id = json_safe_tool_call_id(tool_call, index)

    if not isinstance(tool_call, dict):
        # Home Assistant ToolInput / ToolCall: tool_name + tool_args, often no id.
        tool_name = getattr(tool_call, "tool_name", None)
        if tool_name:
            return _function_payload(
                tool_name,
                getattr(tool_call, "tool_args", {}),
                call_id,
            )
        function = getattr(tool_call, "function", None)
        if function is not None:
            return _function_payload(
                getattr(function, "name", "") or "",
                getattr(function, "arguments", "{}"),
                call_id,
            )
        return None

    function = tool_call.get("function")
    if isinstance(function, dict):
        name = function.get("name") or tool_call.get("tool_name") or tool_call.get("name") or ""
        args = function.get("arguments", tool_call.get("tool_args", tool_call.get("arguments", {})))
        return _function_payload(name, args, call_id)

    name = tool_call.get("tool_name") or tool_call.get("name") or ""
    args = tool_call.get("tool_args", tool_call.get("arguments", {}))
    return _function_payload(name, args, call_id)


def convert_content_to_param(content: Any) -> list[dict[str, Any]]:
    """Convert a ChatLog item to OpenAI-style messages."""
    messages: list[dict[str, Any]] = []
    role = getattr(content, "role", None)
    tool_result = getattr(content, "tool_result", None)
    tool_call_id = getattr(content, "tool_call_id", None)
    if tool_call_id and tool_result is not None and role in {None, "tool"}:
        messages.append(
            {
                "role": "tool",
                "content": tool_result_payload(tool_result),
                "tool_call_id": tool_call_id,
            }
        )
        return messages

    tool_calls = getattr(content, "tool_calls", None)
    if tool_calls:
        tool_calls_list: list[dict[str, Any]] = []
        for index, tool_call in enumerate(tool_calls):
            converted = _convert_tool_call(tool_call, index)
            if converted is not None:
                tool_calls_list.append(converted)
        messages.append(
            {
                "role": "assistant",
                "content": getattr(content, "content", None) or "",
                "tool_calls": tool_calls_list,
            }
        )
        return messages

    text = getattr(content, "content", None)
    if text:
        role_name = role or "user"
        if role_name == "developer":
            role_name = "system"
        messages.append({"role": role_name, "content": text})
    return messages
