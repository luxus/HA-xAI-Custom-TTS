"""Constants for the SpaceXAI Home Assistant umbrella integration."""

from typing import Final, Literal

from ha_spacexai_auth import (
    CLIENT_ID,
    DEVICE_AUTHORIZATION_URL,
    DEVICE_GRANT_TYPE,
    ISSUER,
    REFERRER,
    SCOPES,
    TOKEN_URL,
)

DOMAIN: Final = "spacexai"
LEGACY_DOMAIN: Final = "xai_custom_tts"
DEFAULT_NAME: Final = "SpaceXAI"
CONFIG_VERSION: Final = 2

PLATFORMS: Final = ("conversation", "tts", "stt", "sensor")

# TokenSet / config-entry keys (ha_spacexai_auth contract)
CONF_API_KEY: Final = "api_key"
CONF_AUTH_METHOD: Final = "auth_method"
CONF_ACCESS_TOKEN: Final = "access_token"
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_EXPIRES_AT: Final = "expires_at"
CONF_TOKEN_TYPE: Final = "token_type"
CONF_SCOPE: Final = "scope"
CONF_OAUTH_RECOVERY: Final = "oauth_recovery"

AUTH_OAUTH: Final = "oauth"
AUTH_API_KEY: Final = "api_key"
AuthMethod = Literal["oauth", "api_key"]

OAUTH_RECOVERY_RETRY: Final = "retry_oauth"
OAUTH_RECOVERY_API_KEY: Final = "api_key"
OAUTH_RECOVERY_ABORT: Final = "abort"

TOKEN_EXPIRY_SKEW_SECONDS: Final = 60

# Grok CLI public client — sourced from ha_spacexai_auth (grok-build config.rs).
GROK_OAUTH_ISSUER: Final = ISSUER
GROK_OAUTH_CLIENT_ID: Final = CLIENT_ID
GROK_OAUTH_DEVICE_URL: Final = DEVICE_AUTHORIZATION_URL
GROK_OAUTH_TOKEN_URL: Final = TOKEN_URL
GROK_OAUTH_SCOPES: Final = SCOPES
GROK_DEVICE_GRANT: Final = DEVICE_GRANT_TYPE
GROK_OAUTH_REFERRER: Final = REFERRER

# xAI inference
XAI_API_BASE: Final = "https://api.x.ai/v1"
XAI_TTS_URL: Final = f"{XAI_API_BASE}/tts"
XAI_VOICES_URL: Final = f"{XAI_API_BASE}/tts/voices"
XAI_CUSTOM_VOICES_URL: Final = f"{XAI_API_BASE}/custom-voices"
XAI_RESPONSES_URL: Final = f"{XAI_API_BASE}/responses"
XAI_CHAT_COMPLETIONS_URL: Final = f"{XAI_API_BASE}/chat/completions"
XAI_MODELS_URL: Final = f"{XAI_API_BASE}/models"
XAI_IMAGES_GENERATIONS_URL: Final = f"{XAI_API_BASE}/images/generations"
XAI_STT_URL: Final = f"{XAI_API_BASE}/stt"
XAI_TTS_WS_URL: Final = "wss://api.x.ai/v1/tts"
XAI_STT_WS_URL: Final = "wss://api.x.ai/v1/stt"
XAI_REALTIME_URL: Final = "wss://api.x.ai/v1/realtime"

# Unary POST /v1/tts limits
MAX_TTS_TEXT_CHARS: Final = 60_000
TTS_REQUEST_TIMEOUT: Final = 120.0
TTS_MAX_RETRIES: Final = 3
TTS_RETRY_STATUS_CODES: Final = (429, 500, 503)
SPEED_MIN: Final = 0.7
SPEED_MAX: Final = 1.5
DEFAULT_SPEED: Final = 1.0
DEFAULT_TEXT_NORMALIZATION: Final = False

STT_REQUEST_TIMEOUT: Final = 120.0

# Chat / fast / fallback — live GET /v1/models fills the pickers; these are defaults.
RECOMMENDED_CHAT_MODEL: Final = "grok-4.3-latest"
RECOMMENDED_FAST_MODEL: Final = "grok-4-1-fast-non-reasoning"
RECOMMENDED_FALLBACK_MODEL: Final = "grok-3-mini-fast"
RECOMMENDED_VISION_MODEL: Final = "grok-2-vision-1212"
RECOMMENDED_IMAGE_GENERATION_MODEL: Final = "grok-imagine-image"
RECOMMENDED_IMAGE_MODEL: Final = RECOMMENDED_IMAGE_GENERATION_MODEL
DEFAULT_GROK_MODEL: Final = RECOMMENDED_CHAT_MODEL

# Assist LLM HASS API (HA const CONF_LLM_HASS_API). Default Assist so tools work.
CONF_LLM_HASS_API: Final = "llm_hass_api"
CONF_CHAT_MODEL: Final = "chat_model"
CONF_FAST_MODEL: Final = "fast_model"
CONF_FALLBACK_MODEL: Final = "fallback_model"
CONF_VISION_MODEL: Final = "vision_model"
CONF_IMAGE_MODEL: Final = "image_model"
CONF_MAX_TOKENS: Final = "max_tokens"
CONF_PROMPT: Final = "prompt"
CONF_REASONING_EFFORT: Final = "reasoning_effort"
CONF_RECOMMENDED: Final = "recommended"
CONF_TEMPERATURE: Final = "temperature"
CONF_TOP_P: Final = "top_p"
CONF_LIVE_SEARCH: Final = "live_search"
CONF_SHOW_CITATIONS: Final = "show_citations"
CONF_SEND_USER_NAME: Final = "send_user_name"
CONF_LOCATION_CONTEXT: Final = "location_context"
CONF_INTERACTION_MODE: Final = "interaction_mode"
CONF_VOICE_OPTIMIZED: Final = "voice_optimized"
CONF_AUTO_MODEL_ROUTING: Final = "auto_model_routing"
CONF_HOME_CONTEXT: Final = "home_context"
CONF_BUDGET_WARN_USD: Final = "budget_warn_usd"
CONF_FILENAMES: Final = "filenames"

RECOMMENDED_MAX_TOKENS: Final = 600
RECOMMENDED_REASONING_EFFORT: Final = "low"
RECOMMENDED_TEMPERATURE: Final = 1.0
RECOMMENDED_TOP_P: Final = 1.0
RECOMMENDED_LIVE_SEARCH: Final = "off"
RECOMMENDED_SHOW_CITATIONS: Final = True
RECOMMENDED_SEND_USER_NAME: Final = True
RECOMMENDED_LOCATION_CONTEXT: Final = ""
RECOMMENDED_VOICE_OPTIMIZED: Final = True
RECOMMENDED_AUTO_MODEL_ROUTING: Final = True
RECOMMENDED_HOME_CONTEXT: Final = True
RECOMMENDED_BUDGET_WARN_USD: Final = 0.0
RECOMMENDED_LLM_HASS_API: Final = ["assist"]

LIVE_SEARCH_OFF: Final = "off"
LIVE_SEARCH_WEB: Final = "web"
LIVE_SEARCH_X: Final = "x"
LIVE_SEARCH_FULL: Final = "full"
LIVE_SEARCH_OPTIONS: Final = [
    LIVE_SEARCH_OFF,
    LIVE_SEARCH_WEB,
    LIVE_SEARCH_X,
    LIVE_SEARCH_FULL,
]

MODE_TOOLS: Final = "tools"
MODE_PIPELINE: Final = "pipeline"
MODE_CHAT_ONLY: Final = "chat_only"
RECOMMENDED_INTERACTION_MODE: Final = MODE_TOOLS
INTERACTION_MODE_OPTIONS: Final = [MODE_TOOLS, MODE_PIPELINE, MODE_CHAT_ONLY]

IMAGE_SIZES: Final = ("1024x1024", "1024x1792", "1792x1024")
IMAGE_QUALITIES: Final = ("standard", "hd")
IMAGE_STYLES: Final = ("vivid", "natural")

DEFAULT_INPUT_PRICE_PER_M: Final = 3.0
DEFAULT_OUTPUT_PRICE_PER_M: Final = 15.0

EVENT_USAGE_UPDATED: Final = f"{DOMAIN}_usage_updated"
EVENT_BUDGET_WARNING: Final = f"{DOMAIN}_budget_warning"

MAX_TOOL_ITERATIONS: Final = 10
GROK_REQUEST_TIMEOUT: Final = 60.0

# Ported from braytonstafford/grok_conversation — real tool use, never invent states.
GROK_SYSTEM_PROMPT: Final = """
You are Grok, a helpful and maximally truthful AI built by xAI, integrated with Home Assistant.

Critical rules for smart home control and sensors:
- NEVER invent device states, temperatures, weather, or claim an action succeeded unless a tool result confirms it.
- NEVER say you turned something on/off, set a value, or ran a script until after a successful tool result.
- If a tool returns an error or empty data, tell the user honestly. Do not improvise sensor readings.
- For device control, status, sensors, weather entities, scripts, and scenes: ALWAYS use Home Assistant tools.
- For current events, news, sports, stocks, or web/X info: use live search when enabled; otherwise say you lack live data.
- For general knowledge (history, science, definitions): answer from training data without tools.
- When calling tools, keep any pre-tool text minimal or empty. Put the user-facing answer in the final reply after tools finish.
- Keep spoken Assist replies concise (1-3 sentences) unless the user asks for detail.
"""
DEFAULT_SYSTEM_PROMPT: Final = GROK_SYSTEM_PROMPT

VOICE_OPTIMIZED_SUFFIX: Final = (
    "\nYou are responding through a voice assistant. "
    "Keep answers short (1-3 sentences) unless the user asks for detail. "
    "Avoid markdown, bullet lists, and code blocks in spoken replies. "
    "Do not narrate tool calls out loud."
)

RECOMMENDED_OPTIONS: Final = {
    CONF_RECOMMENDED: True,
    CONF_PROMPT: GROK_SYSTEM_PROMPT,
    CONF_CHAT_MODEL: RECOMMENDED_CHAT_MODEL,
    CONF_FAST_MODEL: RECOMMENDED_FAST_MODEL,
    CONF_FALLBACK_MODEL: RECOMMENDED_FALLBACK_MODEL,
    CONF_LIVE_SEARCH: RECOMMENDED_LIVE_SEARCH,
    CONF_SHOW_CITATIONS: RECOMMENDED_SHOW_CITATIONS,
    CONF_SEND_USER_NAME: RECOMMENDED_SEND_USER_NAME,
    CONF_INTERACTION_MODE: RECOMMENDED_INTERACTION_MODE,
    CONF_VOICE_OPTIMIZED: RECOMMENDED_VOICE_OPTIMIZED,
    CONF_AUTO_MODEL_ROUTING: RECOMMENDED_AUTO_MODEL_ROUTING,
    CONF_HOME_CONTEXT: RECOMMENDED_HOME_CONTEXT,
    CONF_LLM_HASS_API: list(RECOMMENDED_LLM_HASS_API),
}

# Stable entity IDs for Assist pipelines and jev_assist handoff.
GROK_CONVERSATION_AGENT_NAME: Final = "Grok"
GROK_CONVERSATION_ENTITY_ID: Final = "conversation.spacexai_grok"
GROK_CONVERSATION_UNIQUE_ID: Final = "spacexai_grok"
CONVERSATION_ENTITY_NAME: Final = GROK_CONVERSATION_AGENT_NAME

TTS_ENTITY_NAME: Final = "TTS"
TTS_ENTITY_ID: Final = "tts.spacexai_tts"
TTS_UNIQUE_ID: Final = "spacexai_tts"

STT_ENTITY_NAME: Final = "STT"
STT_ENTITY_ID: Final = "stt.spacexai_stt"
STT_UNIQUE_ID: Final = "spacexai_stt"

# Service names
SERVICE_GET_VOICES: Final = "get_voices"
SERVICE_ASK: Final = "ask"
SERVICE_PHOTO_ANALYSIS: Final = "photo_analysis"
SERVICE_QUERY_IMAGE: Final = "query_image"
SERVICE_HOME_BRIEFING: Final = "home_briefing"
SERVICE_GENERATE_IMAGE: Final = "generate_image"
SERVICE_GENERATE_CONTENT: Final = "generate_content"
SERVICE_CLEAR_MEMORY: Final = "clear_memory"
SERVICE_RESET_STATS: Final = "reset_stats"

ALL_SERVICES: Final = (
    SERVICE_GET_VOICES,
    SERVICE_ASK,
    SERVICE_PHOTO_ANALYSIS,
    SERVICE_QUERY_IMAGE,
    SERVICE_HOME_BRIEFING,
    SERVICE_GENERATE_IMAGE,
    SERVICE_GENERATE_CONTENT,
    SERVICE_CLEAR_MEMORY,
    SERVICE_RESET_STATS,
)

# Service parameters
ATTR_TEXT: Final = "text"
ATTR_VOICE_ID: Final = "voice_id"
ATTR_VOICE: Final = "voice"
ATTR_PROFILE_NAME: Final = "profile_name"
ATTR_LANGUAGE: Final = "language"
ATTR_CODEC: Final = "codec"
ATTR_SAMPLE_RATE: Final = "sample_rate"
ATTR_BIT_RATE: Final = "bit_rate"
ATTR_SPEED: Final = "speed"
ATTR_TEXT_NORMALIZATION: Final = "text_normalization"
ATTR_REPLACE: Final = "replace"
ATTR_SEARCH_TEXT: Final = "search_text"
ATTR_MEDIA_PLAYER_ENTITY: Final = "media_player_entity"

# xAI voices — 25+ catalog aligned with grok_conversation / GET /v1/tts/voices.
# Cached defaults; voices are fetched dynamically from the API when possible.
XAI_VOICES: Final = {
    "eve": {
        "name": "Eve",
        "type": "Female",
        "tone": "Energetic, upbeat",
        "description": "Default voice, engaging and enthusiastic",
    },
    "ara": {
        "name": "Ara",
        "type": "Female",
        "tone": "Warm, friendly",
        "description": "Balanced and conversational",
    },
    "rex": {
        "name": "Rex",
        "type": "Male",
        "tone": "Confident, clear",
        "description": "Professional and articulate, ideal for business",
    },
    "sal": {
        "name": "Sal",
        "type": "Neutral",
        "tone": "Smooth, balanced",
        "description": "Versatile voice suitable for various contexts",
    },
    "leo": {
        "name": "Leo",
        "type": "Male",
        "tone": "Authoritative, strong",
        "description": "Decisive and commanding, suitable for instructional content",
    },
    "carina": {
        "name": "Carina",
        "type": "Female",
        "tone": "Soft, empathetic",
        "description": "Soft, empathetic",
    },
    "luna": {
        "name": "Luna",
        "type": "Female",
        "tone": "Gentle, patient",
        "description": "Gentle, patient",
    },
    "iris": {
        "name": "Iris",
        "type": "Female",
        "tone": "Friendly, upbeat",
        "description": "Friendly, upbeat",
    },
    "helios": {
        "name": "Helios",
        "type": "Male",
        "tone": "Upbeat, versatile",
        "description": "Upbeat, versatile assistant",
    },
    "celeste": {
        "name": "Celeste",
        "type": "Female",
        "tone": "Compassionate, reassuring",
        "description": "Compassionate, reassuring",
    },
    "ursa": {
        "name": "Ursa",
        "type": "Neutral",
        "tone": "Friendly, warm",
        "description": "Friendly, warm",
    },
    "rigel": {
        "name": "Rigel",
        "type": "Male",
        "tone": "Precise, professional",
        "description": "Precise, professional",
    },
    "cosmo": {
        "name": "Cosmo",
        "type": "Neutral",
        "tone": "Bright, curious",
        "description": "Bright, curious",
    },
    "lux": {
        "name": "Lux",
        "type": "Neutral",
        "tone": "Grounded, calm",
        "description": "Grounded, calm",
    },
    "atlas": {
        "name": "Atlas",
        "type": "Male",
        "tone": "Confident, commanding",
        "description": "Confident, commanding",
    },
    "castor": {
        "name": "Castor",
        "type": "Male",
        "tone": "Charismatic, easygoing",
        "description": "Charismatic, easygoing",
    },
    "naksh": {
        "name": "Naksh",
        "type": "Neutral",
        "tone": "Warm, thoughtful",
        "description": "Warm, thoughtful",
    },
    "lumen": {
        "name": "Lumen",
        "type": "Neutral",
        "tone": "Warm, articulate",
        "description": "Warm, articulate",
    },
    "sirius": {
        "name": "Sirius",
        "type": "Male",
        "tone": "Quick-witted, playful",
        "description": "Quick-witted, playful",
    },
    "orion": {
        "name": "Orion",
        "type": "Male",
        "tone": "Rich, cinematic",
        "description": "Rich, cinematic",
    },
    "altair": {
        "name": "Altair",
        "type": "Neutral",
        "tone": "Elegant, premium",
        "description": "Elegant, premium",
    },
    "perseus": {
        "name": "Perseus",
        "type": "Male",
        "tone": "Strong, trustworthy",
        "description": "Strong, trustworthy",
    },
    "zenith": {
        "name": "Zenith",
        "type": "Neutral",
        "tone": "Sharp, focused",
        "description": "Sharp, focused",
    },
    "helix": {
        "name": "Helix",
        "type": "Neutral",
        "tone": "Bold, dynamic",
        "description": "Bold, dynamic",
    },
    "kepler": {
        "name": "Kepler",
        "type": "Male",
        "tone": "Inventive, charismatic",
        "description": "Inventive, charismatic",
    },
    "zagan": {
        "name": "Zagan",
        "type": "Male",
        "tone": "Powerful, dramatic",
        "description": "Powerful, dramatic",
    },
}

# Extra IDs merged if the API lists names we do not have locally.
XAI_ADDITIONAL_VOICES: Final = {}

DEFAULT_VOICE: Final = "eve"
DEFAULT_LANGUAGE: Final = "en"
DEFAULT_CODEC: Final = "mp3"
DEFAULT_SAMPLE_RATE: Final = 24000
DEFAULT_BIT_RATE: Final = 128000

SUPPORT_CODECS: Final = ["mp3", "wav", "pcm", "mulaw", "alaw"]
CODEC_CONTENT_TYPES: Final = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
    "mulaw": "audio/basic",
    "alaw": "audio/alaw",
}
CODEC_EXTENSIONS: Final = {
    "mp3": "mp3",
    "wav": "wav",
    "pcm": "pcm",
    "mulaw": "au",
    "alaw": "au",
}
SUPPORT_SAMPLE_RATES: Final = [8000, 16000, 22050, 24000, 44100, 48000]
SUPPORT_BIT_RATES: Final = [32000, 64000, 96000, 128000, 192000]

SUPPORT_LANGUAGES: Final = [
    "auto",
    "en",
    "ar-EG",
    "ar-SA",
    "ar-AE",
    "bn",
    "zh",
    "fr",
    "de",
    "hi",
    "id",
    "it",
    "ja",
    "ko",
    "pt-BR",
    "pt-PT",
    "ru",
    "es-MX",
    "es-ES",
    "tr",
    "vi",
]

LANGUAGE_NAMES: Final = {
    "auto": "Auto-detect",
    "en": "English",
    "ar-EG": "Arabic (Egypt)",
    "ar-SA": "Arabic (Saudi Arabia)",
    "ar-AE": "Arabic (UAE)",
    "bn": "Bengali",
    "zh": "Chinese",
    "fr": "French",
    "de": "German",
    "hi": "Hindi",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "pt-BR": "Portuguese (Brazil)",
    "pt-PT": "Portuguese (Portugal)",
    "ru": "Russian",
    "es-MX": "Spanish (Mexico)",
    "es-ES": "Spanish (Spain)",
    "tr": "Turkish",
    "vi": "Vietnamese",
}

CODEC_NAMES: Final = {
    "mp3": "MP3",
    "wav": "WAV",
    "pcm": "PCM",
    "mulaw": "G.711 μ-law",
    "alaw": "G.711 A-law",
}

# STT languages from https://docs.x.ai/developers/model-capabilities/audio/speech-to-text
# plus common HA Assist BCP-47 tags (mapped to the 2-letter xAI code at request time).
STT_LANGUAGE_CODES: Final = (
    "ar",
    "cs",
    "da",
    "nl",
    "en",
    "fil",
    "fa",
    "fr",
    "de",
    "hi",
    "id",
    "it",
    "ja",
    "ko",
    "mk",
    "ms",
    "pl",
    "pt",
    "ro",
    "ru",
    "es",
    "sv",
    "th",
    "tr",
    "vi",
)
STT_LANGUAGE_ALIASES: Final = {
    "en-US": "en",
    "en-GB": "en",
    "de-DE": "de",
    "fr-FR": "fr",
    "es-ES": "es",
    "es-MX": "es",
    "it-IT": "it",
    "pt-BR": "pt",
    "pt-PT": "pt",
    "nl-NL": "nl",
    "sv-SE": "sv",
    "ja-JP": "ja",
    "ko-KR": "ko",
    "zh-CN": "zh",
    "zh": "zh",
    "pl-PL": "pl",
    "ru-RU": "ru",
    "tr-TR": "tr",
    "hi-IN": "hi",
    "id-ID": "id",
    "vi-VN": "vi",
    "th-TH": "th",
    "cs-CZ": "cs",
    "da-DK": "da",
    "ro-RO": "ro",
    "fa-IR": "fa",
    "fil-PH": "fil",
    "ms-MY": "ms",
    "mk-MK": "mk",
    "ar-SA": "ar",
    "ar-EG": "ar",
    "ar-AE": "ar",
}
STT_SUPPORTED_LANGUAGES: Final = list(STT_LANGUAGE_CODES) + list(STT_LANGUAGE_ALIASES.keys())
