"""Conversation platform: Grok Assist agent with HA LLM tools + live search.

Tool-calling, interaction modes, and live-search two-pass are ported from
braytonstafford/grok_conversation. Auth stays ha_spacexai_auth Bearer headers.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client

from .api_helpers import (
    inject_search_brief,
    pipeline_speech_is_fallback,
    plan_turn,
    strip_json_from_response,
)
from .const import (
    CONF_HOME_CONTEXT,
    CONF_LLM_HASS_API,
    CONF_LOCATION_CONTEXT,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_REASONING_EFFORT,
    CONF_SEND_USER_NAME,
    CONF_SHOW_CITATIONS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_VOICE_OPTIMIZED,
    CONVERSATION_ENTITY_NAME,
    DEFAULT_NAME,
    DOMAIN,
    EVENT_BUDGET_WARNING,
    GROK_CONVERSATION_ENTITY_ID,
    GROK_CONVERSATION_UNIQUE_ID,
    GROK_SYSTEM_PROMPT,
    MODE_CHAT_ONLY,
    RECOMMENDED_HOME_CONTEXT,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_SEND_USER_NAME,
    RECOMMENDED_SHOW_CITATIONS,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_P,
    RECOMMENDED_VOICE_OPTIMIZED,
    VOICE_OPTIMIZED_SUFFIX,
)
from .grok import GrokChatError, async_responses_completion
from .tool_loop import run_tool_loop_with_fallback, tool_result_payload
from .tool_schema import format_llm_tool
from .usage import UsageTracker

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0
_SATELLITE_LONG_REPLY_CHARS = 280


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Grok conversation entity."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GrokConversationEntity(hass, entry, runtime)])


def _convert_content_to_param(content: Any) -> list[dict[str, Any]]:
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
        tool_calls_list = []
        for tool_call in tool_calls:
            if hasattr(tool_call, "function"):
                tool_calls_list.append(
                    {
                        "id": getattr(tool_call, "id", ""),
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                )
            elif hasattr(tool_call, "tool_name"):
                args = getattr(tool_call, "tool_args", {})
                tool_calls_list.append(
                    {
                        "id": getattr(tool_call, "id", str(hash(tool_call))),
                        "type": "function",
                        "function": {
                            "name": tool_call.tool_name,
                            "arguments": json.dumps(args) if not isinstance(args, str) else args,
                        },
                    }
                )
            elif isinstance(tool_call, dict):
                args = tool_call.get("tool_args", tool_call.get("arguments", {}))
                tool_calls_list.append(
                    {
                        "id": tool_call.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tool_call.get("tool_name", tool_call.get("name", "")),
                            "arguments": args if isinstance(args, str) else json.dumps(args),
                        },
                    }
                )
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


def pick_speech_content(chat_log: Any, fallback: str | None = None) -> str | None:
    """Prefer the last assistant message that is not a tool-call turn."""
    found: str | None = None
    content_list = getattr(chat_log, "content", None) if chat_log is not None else None
    if content_list:
        for content in reversed(content_list):
            role = getattr(content, "role", None)
            if role not in {None, "assistant"}:
                continue
            text = (getattr(content, "content", None) or "").strip()
            if not text:
                continue
            if getattr(content, "tool_calls", None):
                if found is None:
                    found = text
                continue
            return text
    return found or fallback


class GrokConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
):
    """Assist agent: Grok + real HA LLM HASS API tools."""

    _attr_has_entity_name = True
    _attr_name = CONVERSATION_ENTITY_NAME
    _attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, runtime: Any) -> None:
        self.hass = hass
        self.entry = entry
        self._runtime = runtime
        self.entity_id = GROK_CONVERSATION_ENTITY_ID
        self._attr_unique_id = GROK_CONVERSATION_UNIQUE_ID
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or DEFAULT_NAME,
            manufacturer="xAI",
            model="Grok",
        )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update_control_feature()
        conversation.async_set_agent(self.hass, self.entry, self)
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._async_entry_update_listener)
        )

    def _update_control_feature(self) -> None:
        plan = plan_turn("", self.entry.options)
        if plan["tools_enabled"]:
            self._attr_supported_features = conversation.ConversationEntityFeature.CONTROL
        else:
            self._attr_supported_features = conversation.ConversationEntityFeature(0)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    def _usage_tracker(self) -> UsageTracker | None:
        return getattr(self._runtime, "usage", None)

    async def _record_usage(
        self, model: str, prompt_tokens: int, completion_tokens: int, service: str = "conversation"
    ) -> None:
        tracker = self._usage_tracker()
        if not tracker:
            return
        await tracker.async_record(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            service=service,
        )
        budget = float(self.entry.options.get("budget_warn_usd", 0) or 0)
        if budget > 0 and tracker.snapshot.estimated_cost_usd >= budget:
            _LOGGER.warning(
                "Grok estimated spend $%.4f exceeded budget warn $%.2f",
                tracker.snapshot.estimated_cost_usd,
                budget,
            )
            self.hass.bus.async_fire(
                EVENT_BUDGET_WARNING,
                {
                    "entry_id": self.entry.entry_id,
                    "estimated_cost_usd": tracker.snapshot.estimated_cost_usd,
                    "budget_warn_usd": budget,
                },
            )

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        try:
            return await self._async_handle_message_inner(user_input, chat_log)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Unexpected error in conversation handler: %s", err, exc_info=True)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(
                "Sorry, I encountered an unexpected error. Please try again."
            )
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=getattr(chat_log, "conversation_id", None)
                or user_input.conversation_id,
            )

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Older HA path; prefer ChatLog wrapping when the core provides it."""
        parent = getattr(super(), "async_process", None)
        if callable(parent):
            try:
                return await parent(user_input)
            except TypeError:
                pass
            except NotImplementedError:
                pass
        return await self._async_handle_message(user_input, None)  # type: ignore[arg-type]

    def _build_factual_context(
        self, user_input: conversation.ConversationInput
    ) -> str:
        options = self.entry.options
        parts: list[str] = []
        location = (options.get(CONF_LOCATION_CONTEXT) or "").strip()
        if location:
            parts.append(
                "Home location context for local queries "
                f"(use this for 'near me', local weather, open now, distance): {location}."
            )
        else:
            tz = getattr(self.hass.config, "time_zone", None)
            if tz:
                parts.append(f"Home Assistant timezone: {tz}.")

        if options.get(CONF_HOME_CONTEXT, RECOMMENDED_HOME_CONTEXT):
            try:
                from homeassistant.util import dt as dt_util

                now = dt_util.now()
                parts.append(f"Current local time: {now.strftime('%A %Y-%m-%d %H:%M')}.")
            except Exception:  # noqa: BLE001
                pass
            people = []
            try:
                for state in self.hass.states.async_all("person"):
                    people.append(
                        f"{state.attributes.get('friendly_name', state.entity_id)}={state.state}"
                    )
            except Exception:  # noqa: BLE001
                people = []
            if people:
                parts.append("Person presence: " + ", ".join(people[:12]) + ".")
            try:
                weather = next(
                    (
                        s
                        for s in self.hass.states.async_all("weather")
                        if s.state not in ("unavailable", "unknown")
                    ),
                    None,
                )
            except Exception:  # noqa: BLE001
                weather = None
            if weather:
                temp = weather.attributes.get("temperature")
                unit = weather.attributes.get("temperature_unit", "")
                parts.append(
                    f"Weather entity {weather.entity_id}: {weather.state}"
                    + (f", {temp}{unit}" if temp is not None else "")
                    + "."
                )
        return "\n".join(parts)

    def _build_persona_context(
        self, user_input: conversation.ConversationInput
    ) -> str:
        options = self.entry.options
        parts: list[str] = []
        if options.get(CONF_VOICE_OPTIMIZED, RECOMMENDED_VOICE_OPTIMIZED):
            parts.append(VOICE_OPTIMIZED_SUFFIX.strip())
        if options.get(CONF_SEND_USER_NAME, RECOMMENDED_SEND_USER_NAME):
            name = self._resolve_user_name(user_input)
            if name:
                parts.append(
                    f"The current user is named {name}. Address them by name when natural."
                )
        return "\n".join(parts)

    def _build_extra_system_prompt(
        self, user_input: conversation.ConversationInput
    ) -> str:
        parts = [
            p
            for p in (
                self._build_persona_context(user_input),
                self._build_factual_context(user_input),
            )
            if p
        ]
        return "\n".join(parts)

    def _resolve_user_name(
        self, user_input: conversation.ConversationInput
    ) -> str | None:
        context = getattr(user_input, "context", None)
        user_id = getattr(context, "user_id", None) if context else None
        if user_id:
            try:
                for state in self.hass.states.async_all("person"):
                    if state.attributes.get("user_id") == user_id:
                        return state.attributes.get("friendly_name") or state.name
            except Exception:  # noqa: BLE001
                pass
            try:
                user = self.hass.auth.async_get_user(user_id) if self.hass.auth else None
                if user and user.name:
                    return user.name
            except Exception:  # noqa: BLE001
                pass
        return None

    async def _try_pipeline(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult | None:
        try:
            result = await conversation.async_converse(
                self.hass,
                text=user_input.text,
                conversation_id=None,
                context=user_input.context,
                language=user_input.language,
                agent_id="conversation.home_assistant",
                device_id=user_input.device_id,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Pipeline HA agent failed: %s", err)
            return None
        speech = ""
        if result and result.response:
            speech = result.response.speech.get("plain", {}).get("speech", "") or ""
            if not speech and hasattr(result.response, "as_dict"):
                data = result.response.as_dict()
                speech = data.get("speech", {}).get("plain", {}).get("speech", "") or ""
        if pipeline_speech_is_fallback(speech):
            return None
        return result

    async def _prewarm_pipeline_tts(
        self,
        message: str,
        user_input: conversation.ConversationInput,
    ) -> bool:
        try:
            from homeassistant.components import assist_pipeline, tts
            from homeassistant.components.tts.media_source import generate_media_source_id

            pipeline = assist_pipeline.async_get_pipeline(self.hass)
            if not pipeline or not pipeline.tts_engine:
                return False
            options: dict[str, Any] = {}
            if pipeline.tts_voice is not None:
                options[tts.ATTR_VOICE] = pipeline.tts_voice
            media_id = generate_media_source_id(
                self.hass,
                message=message,
                engine=pipeline.tts_engine,
                language=pipeline.tts_language,
                options=options or None,
                cache=True,
            )
            await tts.async_get_media_source_audio(self.hass, media_id)
            return True
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("TTS prewarm failed: %s", err)
            return False

    async def _resolve_continue_conversation(
        self,
        user_input: conversation.ConversationInput,
        chat_log: Any,
        speech: str | None,
    ) -> bool:
        continue_conv = bool(getattr(chat_log, "continue_conversation", False))
        if not continue_conv:
            return False
        if not getattr(user_input, "device_id", None):
            return True
        speech_text = (speech or "").strip()
        if not speech_text:
            return False
        if await self._prewarm_pipeline_tts(speech_text, user_input):
            return True
        if len(speech_text) >= _SATELLITE_LONG_REPLY_CHARS:
            _LOGGER.debug(
                "TTS prewarm failed for long satellite reply (%s chars); "
                "disabling continue_conversation",
                len(speech_text),
            )
            return False
        return True

    def _client(self) -> Any:
        return get_async_client(self.hass)

    async def _async_add_assistant(self, chat_log: Any, user_input: Any, text: str) -> None:
        if chat_log is None:
            return
        adder = getattr(chat_log, "async_add_assistant_content", None)
        if not callable(adder):
            without = getattr(chat_log, "async_add_assistant_content_without_tools", None)
            if callable(without):
                try:
                    without(
                        conversation.AssistantContent(
                            agent_id=user_input.agent_id, content=text
                        )
                    )
                except Exception:  # noqa: BLE001
                    _LOGGER.debug("Chat log attach skipped", exc_info=True)
            return
        try:
            async for _ in adder(
                conversation.AssistantContent(agent_id=user_input.agent_id, content=text)
            ):
                pass
        except TypeError:
            try:
                await adder(
                    conversation.AssistantContent(
                        agent_id=user_input.agent_id, content=text
                    )
                )
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Chat log attach skipped", exc_info=True)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Chat log attach skipped", exc_info=True)

    async def _execute_hass_tool(
        self,
        name: str,
        args: dict[str, Any],
        user_input: conversation.ConversationInput,
        chat_log: Any,
    ) -> Any:
        llm_api = getattr(chat_log, "llm_api", None) if chat_log is not None else None
        if llm_api is None:
            return {
                "error": (
                    "LLM HASS API not configured. Enable Assist control in "
                    "SpaceXAI options (LLM HASS API = Assist) and expose the entity."
                )
            }
        try:
            from homeassistant.helpers.llm import ToolInput
        except Exception:  # noqa: BLE001
            ToolInput = None  # type: ignore[misc, assignment]

        tool_input = None
        if ToolInput is not None:
            tool_input = ToolInput(tool_name=name, tool_args=args)

        if hasattr(llm_api, "async_call_tool") and tool_input is not None:
            return await llm_api.async_call_tool(tool_input)

        tool = next((t for t in getattr(llm_api, "tools", []) or [] if t.name == name), None)
        if tool is None:
            return {"error": f"Tool {name} not found"}
        llm_context = user_input.as_llm_context(DOMAIN)
        if tool_input is not None:
            return await tool.async_call(self.hass, tool_input, llm_context)
        return await tool.async_call(self.hass, name, args, llm_context)

    async def _async_handle_message_inner(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog | None,
    ) -> conversation.ConversationResult:
        options = self.entry.options
        plan = plan_turn(user_input.text, options)
        _LOGGER.info(
            "Grok handling message mode=%s device_id=%s text=%s",
            plan["mode"],
            getattr(user_input, "device_id", None),
            user_input.text,
        )

        if plan["try_pipeline"]:
            piped = await self._try_pipeline(user_input)
            if piped is not None:
                _LOGGER.debug("Served via HA intent pipeline")
                return piped

        extra = self._build_extra_system_prompt(user_input)
        user_extra = getattr(user_input, "extra_system_prompt", None) or ""
        combined_extra = "\n".join(p for p in (extra, user_extra) if p)
        llm_api_option = None if plan["mode"] == MODE_CHAT_ONLY else options.get(CONF_LLM_HASS_API)
        if not plan["tools_enabled"]:
            llm_api_option = None

        if chat_log is not None and hasattr(chat_log, "async_provide_llm_data"):
            try:
                await chat_log.async_provide_llm_data(
                    user_input.as_llm_context(DOMAIN),
                    llm_api_option,
                    options.get(CONF_PROMPT) or GROK_SYSTEM_PROMPT,
                    combined_extra or None,
                )
            except Exception as err:  # noqa: BLE001
                converse_err = getattr(conversation, "ConverseError", None)
                if converse_err is not None and isinstance(err, converse_err):
                    _LOGGER.error("ConverseError in async_provide_llm_data: %s", err)
                    as_result = getattr(err, "as_conversation_result", None)
                    if callable(as_result):
                        return as_result()
                _LOGGER.debug("async_provide_llm_data failed: %s", err, exc_info=True)

        messages: list[dict[str, Any]]
        if chat_log is not None and getattr(chat_log, "content", None):
            messages = [
                m
                for content in chat_log.content
                for m in _convert_content_to_param(content)
            ]
        else:
            from .grok import messages_from_chat_log

            messages = messages_from_chat_log(
                user_input.text,
                chat_log,
                system_prompt=options.get(CONF_PROMPT) or GROK_SYSTEM_PROMPT,
            )
            if combined_extra:
                messages[0]["content"] = f"{messages[0]['content']}\n\n{combined_extra}"

        if options.get(CONF_SEND_USER_NAME, RECOMMENDED_SEND_USER_NAME):
            name = self._resolve_user_name(user_input)
            if name and messages:
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i].get("role") == "user":
                        content = messages[i].get("content")
                        if isinstance(content, str) and not content.startswith(f"[{name}]"):
                            messages[i] = {**messages[i], "content": f"[{name}] {content}"}
                        break

        headers = await self._runtime.async_authorization_headers()
        client = self._client()
        show_citations = options.get(CONF_SHOW_CITATIONS, RECOMMENDED_SHOW_CITATIONS)
        show_citations_effective = bool(show_citations) and not bool(
            getattr(user_input, "device_id", None)
        )
        ha_tools_available = bool(
            plan["tools_enabled"]
            and chat_log is not None
            and getattr(getattr(chat_log, "llm_api", None), "tools", None)
        )

        if plan["use_search"]:
            search_system = [
                "You have live web/X search. Lead with the key fact or score, "
                "then briefly add context or opinion when the user's prompt "
                "asks for personality.",
                "Be concise. Prefer scores, times, and concrete outcomes first.",
                "Honor the user's personality/system prompt — keep voice and style.",
                "If results are uncertain, say what you found and what is unknown.",
                "When the user says 'near me' / local / open now, use the home "
                "location and local time below — do not ask them for a city.",
            ]
            if options.get(CONF_PROMPT):
                search_system.append(str(options.get(CONF_PROMPT)))
            factual = self._build_factual_context(user_input)
            if factual:
                search_system.append(factual)
            persona = self._build_persona_context(user_input)
            if persona:
                search_system.append(persona)
            if user_extra:
                search_system.append(user_extra)
            search_messages = [m for m in messages if m.get("role") != "system"]
            try:
                text, p_tok, c_tok = await async_responses_completion(
                    client,
                    headers,
                    model=plan["model"],
                    messages=search_messages,
                    system_prompt="\n\n".join(search_system) or None,
                    max_tokens=options.get(CONF_MAX_TOKENS, RECOMMENDED_MAX_TOKENS),
                    temperature=options.get(CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE),
                    top_p=options.get(CONF_TOP_P, RECOMMENDED_TOP_P),
                    live_search=plan["live_search"],
                    show_citations=show_citations_effective,
                    reasoning_effort=options.get(CONF_REASONING_EFFORT),
                )
                text = strip_json_from_response(text)
                await self._record_usage(plan["model"], p_tok, c_tok)
                if text and not ha_tools_available:
                    await self._async_add_assistant(chat_log, user_input, text)
                    return self._speech_result(user_input, chat_log, text)
                if text and ha_tools_available:
                    messages = inject_search_brief(messages, text)
                    _LOGGER.debug(
                        "Injected live search brief (%s chars) into tool loop",
                        len(text.strip()),
                    )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning(
                    "Live search path failed (%s); continuing without search context",
                    err,
                )

        tools: list[dict[str, Any]] | None = None
        if ha_tools_available:
            tools = []
            llm_api = chat_log.llm_api
            serializer = getattr(llm_api, "custom_serializer", None)
            for tool in llm_api.tools:
                try:
                    tools.append(format_llm_tool(tool, serializer))
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning(
                        "Skipping tool %s due to schema error: %s",
                        getattr(tool, "name", "?"),
                        err,
                    )
            if not tools:
                tools = None

        async def _execute(name: str, args: dict[str, Any]) -> Any:
            return await self._execute_hass_tool(name, args, user_input, chat_log)

        try:
            loop_result = await run_tool_loop_with_fallback(
                client,
                headers,
                models=plan["models_to_try"],
                messages=messages,
                execute_tool=_execute if ha_tools_available else None,
                tools=tools,
                max_tokens=options.get(CONF_MAX_TOKENS, RECOMMENDED_MAX_TOKENS),
                temperature=options.get(CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE),
                top_p=options.get(CONF_TOP_P, RECOMMENDED_TOP_P),
                reasoning_effort=options.get(CONF_REASONING_EFFORT),
                user=getattr(chat_log, "conversation_id", None)
                or user_input.conversation_id,
            )
        except GrokChatError as err:
            raise HomeAssistantError(f"Error talking to xAI: {err}") from err

        await self._record_usage(
            loop_result.model,
            loop_result.prompt_tokens,
            loop_result.completion_tokens,
        )
        if loop_result.speech:
            await self._async_add_assistant(chat_log, user_input, loop_result.speech)
        speech = pick_speech_content(chat_log, loop_result.speech) or loop_result.speech
        if not speech:
            speech = "Sorry, I couldn't generate a response."
        return await self._speech_result_async(user_input, chat_log, speech)

    def _speech_result(
        self,
        user_input: conversation.ConversationInput,
        chat_log: Any,
        speech: str,
    ) -> conversation.ConversationResult:
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(str(speech).strip())
        kwargs: dict[str, Any] = {
            "response": intent_response,
            "conversation_id": getattr(chat_log, "conversation_id", None)
            or user_input.conversation_id,
        }
        return conversation.ConversationResult(**kwargs)

    async def _speech_result_async(
        self,
        user_input: conversation.ConversationInput,
        chat_log: Any,
        speech: str,
    ) -> conversation.ConversationResult:
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(str(speech).strip())
        continue_conv = False
        if chat_log is not None:
            continue_conv = await self._resolve_continue_conversation(
                user_input, chat_log, speech
            )
        getter = getattr(conversation, "async_get_result_from_chat_log", None)
        if callable(getter) and chat_log is not None:
            try:
                result = getter(user_input, chat_log)
                if result is not None:
                    return result
            except Exception:  # noqa: BLE001
                _LOGGER.debug("async_get_result_from_chat_log skipped", exc_info=True)
        try:
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=getattr(chat_log, "conversation_id", None)
                or user_input.conversation_id,
                continue_conversation=continue_conv,
            )
        except TypeError:
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=getattr(chat_log, "conversation_id", None)
                or user_input.conversation_id,
            )

    async def _async_entry_update_listener(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        await hass.config_entries.async_reload(entry.entry_id)
