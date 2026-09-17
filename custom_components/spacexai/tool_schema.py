"""Sanitize HA LLM tool JSON schemas for xAI function calling (no Home Assistant).

Ported from braytonstafford/grok_conversation ``conversation._sanitize_tool_schema``.
xAI rejects roots that are anyOf/oneOf unions (e.g. HA HassStartTimer).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

_LOGGER = logging.getLogger(__name__)


def sanitize_tool_schema(schema: Any) -> dict[str, Any]:
    """Normalize tool JSON schema for xAI function calling."""
    if not isinstance(schema, dict):
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
        }

    def _merge_union_branches(branches: list[Any]) -> dict[str, Any] | None:
        props: dict[str, Any] = {}
        objectish = 0
        for branch in branches:
            if not isinstance(branch, dict):
                continue
            branch = _clean(branch)
            if not isinstance(branch, dict):
                continue
            if branch.get("type") == "object" or "properties" in branch:
                objectish += 1
                nested = branch.get("properties")
                if isinstance(nested, dict):
                    props.update(nested)
        if objectish:
            return {
                "type": "object",
                "properties": props,
                "additionalProperties": True,
            }
        for branch in branches:
            if isinstance(branch, dict):
                return _clean(branch)
        return None

    def _clean(node: Any) -> Any:
        if not isinstance(node, dict):
            return node
        node = dict(node)

        for union_key in ("anyOf", "oneOf", "allOf"):
            if union_key not in node or not isinstance(node[union_key], list):
                continue
            branches = node[union_key]
            merged = _merge_union_branches(branches)
            rest = {k: v for k, v in node.items() if k not in (union_key, "required")}
            if isinstance(merged, dict):
                node = {**rest, **merged}
            else:
                node = rest
            break

        t = node.get("type")
        if isinstance(t, list):
            if "object" in t:
                node["type"] = "object"
            elif "array" in t:
                node["type"] = "array"
            elif t:
                node["type"] = t[0]

        if "properties" in node and isinstance(node["properties"], dict):
            node["properties"] = {
                key: _clean(value) for key, value in node["properties"].items()
            }
        if "items" in node:
            node["items"] = _clean(node["items"])
        if "additionalProperties" in node and isinstance(
            node["additionalProperties"], dict
        ):
            node["additionalProperties"] = _clean(node["additionalProperties"])

        node.pop("not", None)
        return node

    cleaned = _clean(schema)

    if not isinstance(cleaned, dict):
        cleaned = {}
    if cleaned.get("type") != "object" and "properties" not in cleaned:
        cleaned = {
            "type": "object",
            "properties": {"value": cleaned} if cleaned else {},
            "additionalProperties": True,
        }
    cleaned.setdefault("type", "object")
    if cleaned["type"] != "object":
        cleaned = {
            "type": "object",
            "properties": {"value": cleaned},
            "additionalProperties": True,
        }
    cleaned.setdefault("properties", {})
    if not isinstance(cleaned["properties"], dict):
        cleaned["properties"] = {}

    for bad in ("oneOf", "anyOf", "allOf", "not", "enum"):
        cleaned.pop(bad, None)
    if "required" in cleaned and not cleaned.get("properties"):
        cleaned.pop("required", None)

    return cleaned


def format_function_tool(
    name: str,
    description: str,
    parameters: Any,
) -> dict[str, Any]:
    """OpenAI-compatible function tool payload for xAI chat completions."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description or "",
            "parameters": sanitize_tool_schema(parameters),
        },
    }


def convert_voluptuous_parameters(
    parameters: Any,
    custom_serializer: Callable[[Any], Any] | None = None,
) -> dict[str, Any]:
    """Convert a voluptuous schema to JSON Schema; empty object on failure."""
    try:
        from voluptuous_openapi import convert
    except ImportError:
        return {"type": "object", "properties": {}}

    serializer = custom_serializer
    if serializer is None:
        try:
            from homeassistant.helpers import llm

            serializer = llm.selector_serializer
        except Exception:  # noqa: BLE001
            serializer = None
    try:
        raw = convert(parameters, custom_serializer=serializer)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Failed to convert tool schema (%s); using empty object", err)
        raw = {"type": "object", "properties": {}}
    return sanitize_tool_schema(raw)


def format_llm_tool(tool: Any, custom_serializer: Callable[[Any], Any] | None = None) -> dict[str, Any]:
    """Format a Home Assistant ``llm.Tool`` for xAI function calling."""
    name = getattr(tool, "name", "") or ""
    description = getattr(tool, "description", None) or ""
    parameters = getattr(tool, "parameters", None)
    schema = convert_voluptuous_parameters(parameters, custom_serializer)
    return format_function_tool(name, description, schema)
