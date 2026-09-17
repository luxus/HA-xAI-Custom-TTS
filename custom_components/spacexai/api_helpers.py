"""Shared xAI helpers: live search, model filtering, routing (no Home Assistant).

Ported from braytonstafford/grok_conversation ``api_helpers.py``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .const import (
    CONF_AUTO_MODEL_ROUTING,
    CONF_CHAT_MODEL,
    CONF_FALLBACK_MODEL,
    CONF_FAST_MODEL,
    CONF_INTERACTION_MODE,
    CONF_LIVE_SEARCH,
    CONF_LLM_HASS_API,
    LIVE_SEARCH_FULL,
    LIVE_SEARCH_OFF,
    LIVE_SEARCH_WEB,
    LIVE_SEARCH_X,
    MODE_CHAT_ONLY,
    MODE_PIPELINE,
    RECOMMENDED_AUTO_MODEL_ROUTING,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_FALLBACK_MODEL,
    RECOMMENDED_FAST_MODEL,
    RECOMMENDED_INTERACTION_MODE,
    RECOMMENDED_LIVE_SEARCH,
)

_NON_CHAT_MODEL_MARKERS: tuple[str, ...] = (
    "imagine",
    "image",
    "video",
    "tts",
    "stt",
    "voice",
    "embedding",
    "embed",
    "whisper",
    "moderation",
    "realtime",
    "audio",
    "speech",
)

_FALLBACK_CHAT_MODELS: tuple[str, ...] = (
    RECOMMENDED_CHAT_MODEL,
    "grok-4.5",
    "grok-4.5-latest",
    "grok-4-latest",
    "grok-4",
    "grok-4-1-fast-non-reasoning",
    "grok-4-1-fast-reasoning",
    "grok-3-mini-fast",
    "grok-3-mini",
    "grok-3",
    "grok-2-latest",
    RECOMMENDED_FAST_MODEL,
    RECOMMENDED_FALLBACK_MODEL,
)


def is_chat_model_id(model_id: str) -> bool:
    """Return True if model_id looks like a text/chat LLM (not image/voice/etc.)."""
    mid = (model_id or "").strip().lower()
    if not mid:
        return False
    if any(marker in mid for marker in _NON_CHAT_MODEL_MARKERS):
        return False
    if mid.startswith("grok"):
        return True
    if mid.startswith(("ft:", "text-", "code-")):
        return True
    return False


def filter_chat_model_ids(model_ids: Sequence[str]) -> list[str]:
    """Filter + de-dupe + sort chat-capable model ids."""
    seen: set[str] = set()
    out: list[str] = []
    for mid in model_ids:
        if not isinstance(mid, str):
            continue
        name = mid.strip()
        if not name or name in seen or not is_chat_model_id(name):
            continue
        seen.add(name)
        out.append(name)

    def _sort_key(name: str) -> tuple:
        lower = name.lower()
        latest = 0 if "latest" in lower else 1
        return (latest, lower)

    out.sort(key=_sort_key)
    return out


def fallback_chat_models() -> list[str]:
    return filter_chat_model_ids(list(_FALLBACK_CHAT_MODELS))


def parse_models_list(payload: Any) -> list[str]:
    """Extract chat model ids from GET /v1/models JSON."""
    raw_ids: list[str] = []
    data = payload
    if isinstance(payload, Mapping):
        data = payload.get("data") or payload.get("models") or []
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
        return []
    for item in data:
        mid = None
        if isinstance(item, Mapping):
            mid = item.get("id") or item.get("model")
        elif isinstance(item, str):
            mid = item
        else:
            mid = getattr(item, "id", None)
        if mid:
            raw_ids.append(str(mid))
    return filter_chat_model_ids(raw_ids)


def build_live_search_tools(live_search: str) -> list[dict[str, Any]]:
    """Return Responses API server-side search tools for the given mode."""
    mode = (live_search or LIVE_SEARCH_OFF).lower().strip()
    tools: list[dict[str, Any]] = []
    if mode in (LIVE_SEARCH_WEB, LIVE_SEARCH_FULL, "web search", "on", "auto"):
        tools.append({"type": "web_search"})
    if mode in (LIVE_SEARCH_X, LIVE_SEARCH_FULL, "x search", "on", "auto"):
        tools.append({"type": "x_search"})
    return tools


def format_citations(citations: Any) -> str:
    """Format citation URLs into a readable footer."""
    if not citations:
        return ""
    urls: list[str] = []
    if isinstance(citations, (list, tuple)):
        for item in citations:
            if isinstance(item, str) and item.startswith("http"):
                urls.append(item)
            elif isinstance(item, dict):
                url = item.get("url") or item.get("uri") or item.get("id")
                if url:
                    urls.append(str(url))
            else:
                url = getattr(item, "url", None) or getattr(item, "uri", None)
                if url:
                    urls.append(str(url))
    elif isinstance(citations, str):
        urls = [citations]
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    if not unique:
        return ""
    lines = "\n".join(f"- {u}" for u in unique[:12])
    return f"\n\nSources:\n{lines}"


def extract_responses_citations(payload: Any) -> list[Any]:
    """Best-effort citation extraction from Responses API JSON."""
    if payload is None:
        return []
    citations = getattr(payload, "citations", None)
    if citations is None and isinstance(payload, Mapping):
        citations = payload.get("citations")
    if citations:
        return list(citations)
    found: list[Any] = []
    output = getattr(payload, "output", None)
    if output is None and isinstance(payload, Mapping):
        output = payload.get("output")
    for item in output or []:
        content = getattr(item, "content", None)
        if content is None and isinstance(item, dict):
            content = item.get("content")
        for part in content or []:
            anns = getattr(part, "annotations", None)
            if anns is None and isinstance(part, dict):
                anns = part.get("annotations")
            for ann in anns or []:
                url = getattr(ann, "url", None)
                if url is None and isinstance(ann, dict):
                    url = ann.get("url")
                if url:
                    found.append(url)
    return found


def looks_like_search_query(text: str) -> bool:
    """Allow-list heuristic: user clearly wants fresh/web/X info."""
    t = (text or "").lower()
    keywords = (
        "latest",
        "news",
        "headline",
        "today",
        "tonight",
        "tomorrow",
        "right now",
        "current",
        "score",
        "final score",
        "stock",
        "price of",
        "weather",
        "forecast",
        "who won",
        "who is winning",
        "box score",
        "standings",
        "trending",
        "on x",
        "on twitter",
        "search the web",
        "look up",
        "google",
        "what happened",
        "who is playing",
        "near me",
        "nearest",
        "closest",
        "open now",
        "around here",
        "in my area",
        "nearby",
    )
    return any(k in t for k in keywords)


def looks_like_non_search_query(text: str) -> bool:
    """Deny-list for pipeline mode: greetings, jokes, timers, recipes, devices."""
    t = (text or "").strip().lower()
    if not t:
        return True

    if t in ("hi", "hey", "hello", "thanks", "thank you", "bye", "goodbye"):
        return True

    greeting_prefixes = (
        "hello",
        "hi ",
        "hi,",
        "hey ",
        "hey,",
        "good morning",
        "good night",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",
        "bye",
        "goodbye",
        "how are you",
        "what's up",
        "whats up",
    )
    if any(t.startswith(p) for p in greeting_prefixes):
        return True

    device_prefixes = (
        "turn ",
        "set ",
        "play ",
        "lock ",
        "unlock ",
        "pause ",
        "stop ",
        "open ",
        "close ",
        "switch ",
        "dim ",
        "brighten ",
        "activate ",
        "deactivate ",
        "toggle ",
    )
    if any(t.startswith(p) for p in device_prefixes):
        return True
    if any(p in t for p in ("lights on", "lights off", "light on", "light off")):
        return True

    non_search_phrases = (
        "tell me a joke",
        "say a joke",
        "make me laugh",
        "set a timer",
        "start a timer",
        "timer for",
        "remind me",
        "set an alarm",
        "wake me",
        "recipe for",
        "how to cook",
        "how do i cook",
        "how do i make",
        "ingredients for",
    )
    return any(p in t for p in non_search_phrases)


def should_use_live_search(
    text: str, *, interaction_mode: str, live_search: str
) -> bool:
    """Decide whether to run the Responses live-search pass.

    - chat_only: always search when live search is enabled
    - pipeline: allow-list True; deny-list False; default True
    - tools: stricter allow-list only
    """
    if not live_search or live_search == LIVE_SEARCH_OFF:
        return False
    if interaction_mode == MODE_CHAT_ONLY:
        return True
    if looks_like_search_query(text):
        return True
    if interaction_mode == MODE_PIPELINE:
        return not looks_like_non_search_query(text)
    return False


def looks_like_simple_query(text: str) -> bool:
    """Heuristic for auto-routing to a fast model."""
    t = (text or "").strip()
    if len(t) > 160:
        return False
    simple_starts = (
        "turn ",
        "switch ",
        "set ",
        "open ",
        "close ",
        "lock ",
        "unlock ",
        "play ",
        "pause ",
        "stop ",
        "what's the",
        "what is the",
        "is the ",
        "are the ",
        "how warm",
        "how cold",
        "temperature",
        "lights",
        "good morning",
        "good night",
        "hello",
        "hi ",
        "thanks",
        "thank you",
    )
    lower = t.lower()
    if any(lower.startswith(s) for s in simple_starts):
        return True
    return len(t.split()) <= 8 and "?" not in t[20:]


def normalize_llm_hass_api(value: Any) -> list[str]:
    """Return Assist API ids, dropping the 'none' sentinel."""
    if not value:
        return []
    if isinstance(value, str):
        api_list = [value]
    elif isinstance(value, (list, tuple)):
        api_list = [str(item) for item in value]
    else:
        return []
    return [api_id for api_id in api_list if api_id and api_id != "none"]


def tools_enabled_for_mode(mode: str, llm_hass_api: Any) -> bool:
    """True when interaction mode should send HA LLM tools to Grok."""
    if mode == MODE_CHAT_ONLY:
        return False
    return bool(normalize_llm_hass_api(llm_hass_api))


def select_model(user_text: str, options: Mapping[str, Any] | None = None) -> str:
    """Pick chat/fast model based on auto-routing."""
    options = options or {}
    primary = options.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL)
    fast = options.get(CONF_FAST_MODEL, RECOMMENDED_FAST_MODEL)
    if options.get(CONF_AUTO_MODEL_ROUTING, RECOMMENDED_AUTO_MODEL_ROUTING):
        if looks_like_simple_query(user_text) and not looks_like_search_query(user_text):
            return fast or primary
    return primary


def plan_turn(user_text: str, options: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Mode / tools / search / model plan for one Assist turn (unit-testable)."""
    options = dict(options or {})
    mode = options.get(CONF_INTERACTION_MODE, RECOMMENDED_INTERACTION_MODE)
    live_search = options.get(CONF_LIVE_SEARCH, RECOMMENDED_LIVE_SEARCH)
    llm_hass_api = options.get(CONF_LLM_HASS_API)
    model = select_model(user_text, options)
    fallback = options.get(CONF_FALLBACK_MODEL, RECOMMENDED_FALLBACK_MODEL)
    tools_on = tools_enabled_for_mode(mode, llm_hass_api)
    return {
        "mode": mode,
        "try_pipeline": mode == MODE_PIPELINE,
        "tools_enabled": tools_on,
        "llm_hass_api": normalize_llm_hass_api(llm_hass_api) if tools_on else [],
        "use_search": should_use_live_search(
            user_text, interaction_mode=mode, live_search=live_search
        ),
        "live_search": live_search,
        "model": model,
        "fallback_model": fallback if fallback and fallback != model else None,
        "models_to_try": [model]
        + ([fallback] if fallback and fallback != model else []),
    }


def inject_search_brief(
    messages: Sequence[Mapping[str, Any]], brief: str
) -> list[dict[str, Any]]:
    """Two-pass (#26): inject live findings into the tool-loop system prompt."""
    text = (brief or "").strip()
    if len(text) > 4000:
        text = text[:4000] + "…"
    search_note = (
        "Live search results for this user question "
        "(use these facts; do not claim you lack real-time data):\n"
        f"{text}"
    )
    new_messages: list[dict[str, Any]] = []
    inserted = False
    for msg in messages:
        item = dict(msg)
        if (
            not inserted
            and item.get("role") == "system"
            and isinstance(item.get("content"), str)
        ):
            item["content"] = f"{item['content']}\n\n{search_note}"
            inserted = True
        new_messages.append(item)
    if not inserted:
        new_messages.insert(0, {"role": "system", "content": search_note})
    return new_messages


def pipeline_speech_is_fallback(speech: str) -> bool:
    """True when the built-in HA agent did not handle the intent."""
    if not speech or not speech.strip():
        return True
    lowered = speech.lower()
    markers = (
        "sorry",
        "i am not aware",
        "i'm not aware",
        "don't know",
        "do not know",
        "no intent",
        "not sure how",
        "can you rephrase",
    )
    return any(m in lowered for m in markers)


def strip_json_from_response(response: str) -> str:
    """Strip JSON objects from the end of LLM responses."""
    if not response:
        return response
    last_brace_index = response.rfind("{")
    if last_brace_index == -1:
        return response
    potential_json = response[last_brace_index:]
    try:
        import json

        json.loads(potential_json)
        return response[:last_brace_index].strip()
    except (json.JSONDecodeError, TypeError, ValueError):
        return response
