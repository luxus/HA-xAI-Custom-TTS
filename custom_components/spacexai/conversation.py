"""Conversation platform: Grok entity that calls https://api.x.ai/v1/responses."""

from __future__ import annotations

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

from .const import (
    CONVERSATION_ENTITY_NAME,
    DEFAULT_NAME,
    DOMAIN,
)
from .grok import GrokChatError, async_chat_complete, messages_from_chat_log

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Grok conversation entity."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GrokConversationEntity(hass, entry, runtime)])


class GrokConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
):
    """Assist agent that returns real Grok prose from api.x.ai."""

    _attr_has_entity_name = True
    _attr_name = CONVERSATION_ENTITY_NAME
    _attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, runtime: Any) -> None:
        self.hass = hass
        self.entry = entry
        self._runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}-grok"
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
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        result = await self._async_grok_reply(user_input, chat_log)
        speech = _speech_from_result(result)
        try:
            chat_log.async_add_assistant_content_without_tools(
                conversation.AssistantContent(
                    agent_id=user_input.agent_id,
                    content=speech,
                )
            )
        except Exception:  # noqa: BLE001 — older ChatLog shapes
            _LOGGER.debug("Chat log attach skipped", exc_info=True)
        getter = getattr(conversation, "async_get_result_from_chat_log", None)
        if callable(getter):
            try:
                return getter(user_input, chat_log)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("async_get_result_from_chat_log skipped", exc_info=True)
        return result

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Older HA path without ChatLog wrapping."""
        return await self._async_grok_reply(user_input, None)

    async def _async_grok_reply(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog | None,
    ) -> conversation.ConversationResult:
        intent_response = intent.IntentResponse(language=user_input.language)
        try:
            headers = await self._runtime.async_authorization_headers()
            messages = messages_from_chat_log(user_input.text, chat_log)
            client = get_async_client(self.hass)
            speech = await async_chat_complete(client, headers, messages)
        except GrokChatError as err:
            _LOGGER.error("Grok returned no prose: %s", err)
            speech = "Grok did not return a reply."
        except HomeAssistantError:
            raise
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Grok conversation failed: %s", err)
            speech = "I couldn't reach Grok. Check SpaceXAI authentication and try again."
        if not speech or not str(speech).strip():
            speech = "Grok did not return a reply."
        intent_response.async_set_speech(str(speech).strip())
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
        )


def _speech_from_result(result: conversation.ConversationResult) -> str:
    try:
        speech = result.response.speech.get("plain", {}).get("speech")
        if isinstance(speech, str):
            return speech
    except Exception:  # noqa: BLE001
        pass
    return ""
