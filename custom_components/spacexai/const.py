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

PLATFORMS: Final = ("conversation", "tts", "stt")

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

# Responses is the current xAI text API; chat completions remains as a parse fallback.
DEFAULT_GROK_MODEL: Final = "grok-4"
DEFAULT_SYSTEM_PROMPT: Final = (
    "You are Grok, a helpful assistant from xAI, running inside Home Assistant. "
    "Answer clearly and concisely in natural language. "
    "You cannot call Home Assistant services in this stub; describe what the user "
    "should do if they ask to control devices."
)

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

# xAI voices - https://docs.x.ai/docs/api-reference#voices
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
}

# Additional built-in voice IDs from GET /v1/tts/voices (offline fallback names).
XAI_ADDITIONAL_VOICES: Final = {
    "carina": "Carina",
    "zagan": "Zagan",
    "helix": "Helix",
    "orion": "Orion",
    "luna": "Luna",
    "iris": "Iris",
    "altair": "Altair",
    "zenith": "Zenith",
    "perseus": "Perseus",
    "helios": "Helios",
    "lux": "Lux",
    "kepler": "Kepler",
    "rigel": "Rigel",
    "cosmo": "Cosmo",
    "celeste": "Celeste",
    "ursa": "Ursa",
    "sirius": "Sirius",
    "lumen": "Lumen",
    "castor": "Castor",
    "naksh": "Naksh",
    "atlas": "Atlas",
}

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
