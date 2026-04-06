"""Constants for the xAI Custom TTS integration."""

DOMAIN = "xai_custom_tts"

# Configuration constants
CONF_API_KEY = "api_key"

# Service names
SERVICE_GET_VOICES = "get_voices"

# Service parameters
ATTR_TEXT = "text"
ATTR_VOICE_ID = "voice_id"
ATTR_VOICE = "voice"
ATTR_PROFILE_NAME = "profile_name"
ATTR_LANGUAGE = "language"

# Output format parameters
ATTR_CODEC = "codec"
ATTR_SAMPLE_RATE = "sample_rate"
ATTR_BIT_RATE = "bit_rate"

# Voice filtering parameters
ATTR_SEARCH_TEXT = "search_text"

# Media player parameters
ATTR_MEDIA_PLAYER_ENTITY = "media_player_entity"

# API constants
XAI_TTS_URL = "https://api.x.ai/v1/tts"
XAI_VOICES_URL = "https://api.x.ai/v1/tts/voices"
XAI_REALTIME_URL = "wss://api.x.ai/v1/realtime"

# xAI voices - https://docs.x.ai/docs/api-reference#voices
# These are cached defaults; voices are fetched dynamically from API
XAI_VOICES = {
    "eve": {"name": "Eve", "type": "Female", "tone": "Energetic, upbeat", "description": "Default voice, engaging and enthusiastic"},
    "ara": {"name": "Ara", "type": "Female", "tone": "Warm, friendly", "description": "Balanced and conversational"},
    "rex": {"name": "Rex", "type": "Male", "tone": "Confident, clear", "description": "Professional and articulate, ideal for business"},
    "sal": {"name": "Sal", "type": "Neutral", "tone": "Smooth, balanced", "description": "Versatile voice suitable for various contexts"},
    "leo": {"name": "Leo", "type": "Male", "tone": "Authoritative, strong", "description": "Decisive and commanding, suitable for instructional content"},
}

# Default settings
DEFAULT_VOICE = "eve"
DEFAULT_LANGUAGE = "en"
DEFAULT_CODEC = "mp3"
DEFAULT_SAMPLE_RATE = 24000
DEFAULT_BIT_RATE = 128000

# Supported codecs
SUPPORT_CODECS = ["mp3", "wav", "pcm", "mulaw", "alaw"]

# Supported sample rates
SUPPORT_SAMPLE_RATES = [8000, 16000, 22050, 24000, 44100, 48000]

# Supported bit rates (MP3 only)
SUPPORT_BIT_RATES = [32000, 64000, 96000, 128000, 192000]

# Supported languages for xAI TTS - https://docs.x.ai/docs/api-reference#text-to-speech
SUPPORT_LANGUAGES = [
    "auto",     # Automatic language detection
    "en",       # English
    "ar-EG",    # Arabic (Egypt)
    "ar-SA",    # Arabic (Saudi Arabia)
    "ar-AE",    # Arabic (UAE)
    "bn",       # Bengali
    "zh",       # Chinese
    "fr",       # French
    "de",       # German
    "hi",       # Hindi
    "id",       # Indonesian
    "it",       # Italian
    "ja",       # Japanese
    "ko",       # Korean
    "pt-BR",    # Portuguese (Brazil)
    "pt-PT",    # Portuguese (Portugal)
    "ru",       # Russian
    "es-MX",    # Spanish (Mexico)
    "es-ES",    # Spanish (Spain)
    "tr",       # Turkish
    "vi",       # Vietnamese
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
