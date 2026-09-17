"""Chat-completions tool loop (no Home Assistant imports).

Ported from braytonstafford/grok_conversation ``OpenAIConversationEntity._tool_loop``.
``execute_tool(name, args)`` is injected so tests can mock HassTurnOn without HA.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .api_helpers import strip_json_from_response
from .const import MAX_TOOL_ITERATIONS
from .grok import ChatTurn, GrokChatError, RawToolCall, async_chat_completions

_LOGGER = logging.getLogger(__name__)

ExecuteTool = Callable[[str, dict[str, Any]], Awaitable[Any]]


@dataclass
class ToolLoopResult:
    """Outcome of the tool-calling chat loop."""

    speech: str
    messages: list[dict[str, Any]]
    tool_invocations: list[dict[str, Any]] = field(default_factory=list)
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str | None = None
    length_exceeded: bool = False


def tool_result_payload(tool_result: Any) -> str:
    """Serialize tool results for the model. Always pass through real data."""
    try:
        return json.dumps(tool_result, default=str)
    except TypeError:
        return json.dumps({"result": str(tool_result)})


def parse_tool_arguments(raw: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (args, error_payload). error_payload is set when JSON is invalid."""
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError as err:
        return None, {
            "error": f"Invalid tool arguments JSON: {err}",
            "raw_arguments": raw,
        }
    if not isinstance(parsed, dict):
        return None, {
            "error": "Tool arguments must be a JSON object",
            "raw_arguments": raw,
        }
    return parsed, None


def assistant_tool_message(turn: ChatTurn) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": turn.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": tc.arguments_json,
                },
            }
            for tc in turn.tool_calls
        ],
    }


def tool_message(tool_call_id: str, payload: Any) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": tool_result_payload(payload),
    }


async def execute_raw_tool_call(
    tc: RawToolCall,
    execute_tool: ExecuteTool,
) -> dict[str, Any]:
    """Run one tool call; always return a JSON-serializable payload."""
    args, error = parse_tool_arguments(tc.arguments_json)
    if error is not None:
        return error
    assert args is not None
    try:
        return await execute_tool(tc.name, args)
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Error executing tool %s: %s", tc.name, err, exc_info=True)
        return {"error": str(err), "tool": tc.name}


async def run_tool_loop(
    client: Any,
    headers: Mapping[str, str],
    *,
    model: str,
    messages: Sequence[Mapping[str, Any]],
    execute_tool: ExecuteTool | None,
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    reasoning_effort: str | None = None,
    user: str | None = None,
    max_iterations: int = MAX_TOOL_ITERATIONS,
) -> ToolLoopResult:
    """Iterate chat.completions until the model stops requesting tools."""
    working: list[dict[str, Any]] = [dict(m) for m in messages]
    invocations: list[dict[str, Any]] = []
    prompt_tokens = 0
    completion_tokens = 0
    last_turn: ChatTurn | None = None
    formatted_tools = tools if tools else None
    tool_choice = "auto" if formatted_tools else None

    for _iteration in range(max_iterations):
        last_turn = await async_chat_completions(
            client,
            headers,
            model=model,
            messages=working,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            tools=formatted_tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
            user=user,
        )
        prompt_tokens += last_turn.prompt_tokens
        completion_tokens += last_turn.completion_tokens

        if last_turn.tool_calls:
            if execute_tool is None:
                working.append(assistant_tool_message(last_turn))
                for tc in last_turn.tool_calls:
                    payload = {
                        "error": (
                            "LLM HASS API not configured. Enable Home Assistant "
                            "LLM API / Assist control in SpaceXAI options."
                        )
                    }
                    working.append(tool_message(tc.id, payload))
                    invocations.append(
                        {"name": tc.name, "arguments": tc.arguments_json, "result": payload}
                    )
                continue

            working.append(assistant_tool_message(last_turn))
            for tc in last_turn.tool_calls:
                result = await execute_raw_tool_call(tc, execute_tool)
                args, _ = parse_tool_arguments(tc.arguments_json)
                invocations.append(
                    {
                        "name": tc.name,
                        "id": tc.id,
                        "arguments": args if args is not None else tc.arguments_json,
                        "result": result,
                    }
                )
                _LOGGER.debug("Tool %s result: %s", tc.name, result)
                working.append(tool_message(tc.id, result))
            continue

        speech = strip_json_from_response(last_turn.content or "")
        if speech:
            working.append({"role": "assistant", "content": speech})
        return ToolLoopResult(
            speech=speech,
            messages=working,
            tool_invocations=invocations,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=last_turn.finish_reason,
            length_exceeded=last_turn.finish_reason == "length",
        )

    speech = ""
    if last_turn and last_turn.content:
        speech = strip_json_from_response(last_turn.content)
    return ToolLoopResult(
        speech=speech,
        messages=working,
        tool_invocations=invocations,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        finish_reason=last_turn.finish_reason if last_turn else None,
        length_exceeded=True,
    )


async def run_tool_loop_with_fallback(
    client: Any,
    headers: Mapping[str, str],
    *,
    models: Sequence[str],
    messages: Sequence[Mapping[str, Any]],
    execute_tool: ExecuteTool | None,
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    reasoning_effort: str | None = None,
    user: str | None = None,
) -> ToolLoopResult:
    """Try primary then fallback model (skip fallback on HTTP 429)."""
    last_error: Exception | None = None
    seen: set[str] = set()
    for model in models:
        if not model or model in seen:
            continue
        seen.add(model)
        try:
            return await run_tool_loop(
                client,
                headers,
                model=model,
                messages=messages,
                execute_tool=execute_tool,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                reasoning_effort=reasoning_effort,
                user=user,
            )
        except GrokChatError as err:
            last_error = err
            err_text = str(err)
            if "429" in err_text:
                _LOGGER.error("Rate limited by xAI on %s: %s", model, err)
                break
            _LOGGER.warning("Model %s failed (%s); trying fallback if available", model, err)
            continue
        except Exception as err:  # noqa: BLE001
            last_error = err
            _LOGGER.warning("Unexpected error on %s: %s", model, err)
            continue
    raise GrokChatError(f"Error talking to xAI: {last_error}") from last_error
