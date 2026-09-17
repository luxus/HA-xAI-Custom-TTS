"""Constants for the xAI Custom TTS integration."""

DOMAIN = "xai_custom_tts"

# Configuration constants
CONF_API_KEY = "api_key"

# Service names
SERVICE_GET_VOICES = "get_voices"

# Service / option parameter names (1:1 with xAI TTS request fields where possible)
ATTR_TEXT = "text"
ATTR_VOICE_ID = "voice_id"
ATTR_VOICE = "voice"
ATTR_PROFILE_NAME = "profile_name"
ATTR_LANGUAGE = "language"
ATTR_CODEC = "codec"
ATTR_SAMPLE_RATE = "sample_rate"
ATTR_BIT_RATE = "bit_rate"
ATTR_SPEED = "speed"
ATTR_TEXT_NORMALIZATION = "text_normalization"
ATTR_REPLACE = "replace"
ATTR_SEARCH_TEXT = "search_text"
ATTR_MEDIA_PLAYER_ENTITY = "media_player_entity"

# Unary REST TTS
XAI_TTS_URL = "https://api.x.ai/v1/tts"
XAI_VOICES_URL = "https://api.x.ai/v1/tts/voices"
XAI_CUSTOM_VOICES_URL = "https://api.x.ai/v1/custom-voices"

# Bidirectional streaming TTS (not implemented in this integration).
# Distinct from Speech-to-Speech realtime: wss://api.x.ai/v1/realtime
XAI_TTS_WS_URL = "wss://api.x.ai/v1/tts"

# Unary POST /v1/tts limits (docs: Text to Speech, Sep 2026)
MAX_TTS_TEXT_CHARS = 60_000
TTS_REQUEST_TIMEOUT = 120.0
TTS_MAX_RETRIES = 3
TTS_RETRY_STATUS_CODES = (429, 500, 503)

# speed: 0.7–1.5, default 1.0
SPEED_MIN = 0.7
SPEED_MAX = 1.5
DEFAULT_SPEED = 1.0
DEFAULT_TEXT_NORMALIZATION = False

# Cached personality copy for the original five voices. Live lists come from
# GET /v1/tts/voices; this is offline fallback + richer labels only.
# https://docs.x.ai/developers/model-capabilities/audio/text-to-speech
XAI_VOICES = {
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

# Additional built-in voice IDs from GET /v1/tts/voices (REST example, Sep 2026).
# Used only as offline fallback names; live discovery is preferred.
XAI_ADDITIONAL_VOICES = {
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

# Default settings
DEFAULT_VOICE = "eve"
DEFAULT_LANGUAGE = "en"
DEFAULT_CODEC = "mp3"
DEFAULT_SAMPLE_RATE = 24000
DEFAULT_BIT_RATE = 128000

# Supported codecs (Content-Type per docs)
SUPPORT_CODECS = ["mp3", "wav", "pcm", "mulaw", "alaw"]
CODEC_CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
    "mulaw": "audio/basic",
    "alaw": "audio/alaw",
}
CODEC_EXTENSIONS = {
    "mp3": "mp3",
    "wav": "wav",
    "pcm": "pcm",
    "mulaw": "au",
    "alaw": "au",
}

# Supported sample rates
SUPPORT_SAMPLE_RATES = [8000, 16000, 22050, 24000, 44100, 48000]

# Supported bit rates (MP3 only)
SUPPORT_BIT_RATES = [32000, 64000, 96000, 128000, 192000]

# Supported languages for xAI TTS
# https://docs.x.ai/developers/model-capabilities/audio/text-to-speech
SUPPORT_LANGUAGES = [
    "auto",  # Automatic language detection
    "en",  # English
    "ar-EG",  # Arabic (Egypt)
    "ar-SA",  # Arabic (Saudi Arabia)
    "ar-AE",  # Arabic (UAE)
    "bn",  # Bengali
    "zh",  # Chinese
    "fr",  # French
    "de",  # German
    "hi",  # Hindi
    "id",  # Indonesian
    "it",  # Italian
    "ja",  # Japanese
    "ko",  # Korean
    "pt-BR",  # Portuguese (Brazil)
    "pt-PT",  # Portuguese (Portugal)
    "ru",  # Russian
    "es-MX",  # Spanish (Mexico)
    "es-ES",  # Spanish (Spain)
    "tr",  # Turkish
    "vi",  # Vietnamese
]

# Language display names for UI
LANGUAGE_NAMES = {
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

# Codec display names
CODEC_NAMES = {
    "mp3": "MP3",
    "wav": "WAV",
    "pcm": "PCM",
    "mulaw": "G.711 μ-law",
    "alaw": "G.711 A-law",
}
