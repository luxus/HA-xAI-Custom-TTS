# HA-xAI-Custom-TTS

<p align="center">
  <img src="https://pbs.twimg.com/profile_images/1769430779845611520/lIgjSJGU_400x400.jpg" alt="xAI Logo" width="120">
</p>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/luxus/HA-xAI-Custom-TTS.svg)](https://github.com/luxus/HA-xAI-Custom-TTS/releases/)

A xAI (Grok) TTS integration for Home Assistant that provides voice synthesis using xAI's Text-to-Speech API and integrates with Home Assistant's native TTS platform.

This custom component provides:
1. **Get Voices Service** - Retrieve built-in voices from `GET /v1/tts/voices` plus your team's custom voices from `GET /v1/custom-voices`
2. **Native TTS Platform** - Full integration with Home Assistant's TTS system (`POST /v1/tts`, API-key auth)
3. **Voice Profile Management** - Create, modify, and delete named voice profiles with codec, speed, and text-normalization control
4. **Flexible Output Formats** - MP3, WAV, PCM, and telephony codecs (G.711 μ-law/A-law) with configurable sample rates

### Why use this instead of other TTS integrations?
- 🎙️ **API-listed voices** – Built-in roster from xAI plus custom `voice_id`s from the console
- 🌍 **21 Languages** – Natural pronunciation with auto-detection support
- 🔧 **Voice Profiles** – Define multiple voice configurations with codec, sample rate, bit rate, speed, and text normalization
- 📞 **Telephony Ready** – Native G.711 codec support for SIP/PBX integration
- 🚀 **Enterprise Ready** – SOC 2 Type II, HIPAA eligible, GDPR compliant

> **🙏 Credits**: This integration is based on the excellent work of [@loryanstrant](https://github.com/loryanstrant) and the [HA-ElevenLabs-Custom-TTS](https://github.com/loryanstrant/HA-ElevenLabs-Custom-TTS) project. The voice profile management system and architecture were adapted from that original integration.

---

## ✨ Features

> **📝 Note:** The default TTS entity ID is `tts.xai_custom_tts`. This is used in all the examples below.

### Voice Discovery
- **Built-in voices**: Loaded live from `GET /v1/tts/voices` (Eve, Ara, Rex, Sal, Leo, plus additional documented IDs such as Luna, Carina, Atlas, …)
- **Custom voices**: Team-scoped IDs from `GET /v1/custom-voices` (or paste a console Copy Voice ID). Unknown IDs are sent through to the API; a `404` is logged rather than silently falling back to Eve
- **Voice Search**: Search voices by id, name, type, tone, description, or source (`builtin` / `custom`)
- **Multi-Language Support**: 21 languages including auto-detection

### Audio Format Options
- **Codecs**: MP3, WAV, PCM, G.711 μ-law, G.711 A-law
- **Sample Rates**: 8000, 16000, 22050, 24000 (default), 44100, 48000 Hz
- **Bit Rates**: 32, 64, 96, 128 (default), 192 kbps (MP3 only)
- **Telephony Integration**: Direct G.711 support for PBX/SIP systems without transcoding

### Native TTS Platform Integration
- **Seamless Integration**: Works with Home Assistant's native TTS services (`tts.speak`, `tts.cloud_say`, etc.)
- **Media Player Support**: Use with any Home Assistant media player through the TTS platform
- **Multi-Language Support**: Supports 21+ languages

### Voice Profile Management
- **Create Named Profiles**: Save your favorite voice configurations with custom names
- **Full Format Control**: Set codec, sample rate, and bit rate per profile
- **Easy Profile Management**: Add, modify, or delete voice profiles through the Home Assistant UI
- **Quick Profile Selection**: Use saved profiles with the `voice_profile` option in TTS calls
- **Profile Storage**: Profiles are stored in Home Assistant configuration and persist across restarts

---

## Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots menu and select "Custom repositories"
4. Add `https://github.com/luxus/HA-xAI-Custom-TTS` as repository
5. Set category to "Integration"
6. Click "Add"
7. Find "xAI Custom TTS" in the integration list and install it
8. Restart Home Assistant
9. Go to Configuration > Integrations
10. Click "Add Integration" and search for "xAI Custom TTS"
11. Enter your xAI API key from [console.x.ai](https://console.x.ai/team/default/api-keys)

Or replace steps 1-6 with this:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=luxus&repository=HA-xAI-Custom-TTS&category=integration)

### Manual Installation

1. Copy the `custom_components/xai_custom_tts` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click "Add Integration" and search for "xAI Custom TTS"
5. Enter your xAI API key from [console.x.ai](https://console.x.ai/team/default/api-keys)

---

## 🎭 Voice Profile Management

After installation, you can create and manage voice profiles through the Home Assistant UI. Voice profiles allow you to save your favorite voice configurations with custom names for easy reuse.

### Accessing Voice Profile Settings

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Find your **xAI Custom TTS** integration
3. Click **Configure** (or the gear icon)
4. You'll see the Voice Profile Management interface

### Managing Voice Profiles

#### Adding a New Voice Profile

1. In the Voice Profile Management interface, select **"Add New Voice Profile"**
2. Fill out the profile details:
   - **Profile Name**: A descriptive name for your profile (e.g., "News Reader", "Bedtime Story")
   - **Voice**: Choose a built-in or custom `voice_id` (list is fetched from the API)
   - **Language**: Select the language code (default: "en", or use "auto" for auto-detection)
   - **Audio Codec**: Select output format (MP3, WAV, PCM, G.711 μ-law, G.711 A-law)
   - **Sample Rate**: Audio quality (24000 Hz default, lower for telephony)
   - **Bit Rate**: Compression quality for MP3 (128000 bps default)
   - **Speed**: Speech multiplier `0.7`–`1.5` (default `1.0`)
   - **Normalize Text**: Expand numbers/abbreviations/symbols into spoken form (default off)
3. Click **Submit** to save the profile

#### Available Voices

Built-in IDs are case-insensitive (`eve` / `Eve`). Personality copy for the original five:

| Voice | Type | Tone | Best For |
|-------|------|------|----------|
| **Eve** | Female | Energetic, upbeat | Engaging announcements, energetic content |
| **Ara** | Female | Warm, friendly | Conversational interactions, friendly greetings |
| **Rex** | Male | Confident, clear | Professional announcements, business content |
| **Sal** | Neutral | Smooth, balanced | General purpose, versatile contexts |
| **Leo** | Male | Authoritative, strong | Instructions, alerts, important announcements |

Additional built-in voices (Carina, Luna, Atlas, and others) appear in the profile dropdown and `xai_custom_tts.get_voices` when the API returns them. Custom voices show as `(custom)` and use the 8-character id from the console.

#### Audio Format Recommendations

| Use Case | Codec | Sample Rate | Notes |
|----------|-------|-------------|-------|
| **General Home Assistant** | MP3 | 24000 Hz | Good balance of quality and size |
| **High Quality Audio** | WAV | 44100 Hz | Uncompressed, best quality |
| **SIP/PBX Integration** | mulaw | 8000 Hz | Native telephony format |
| **VoIP Systems** | alaw | 8000 Hz | European telephony standard |
| **Low Bandwidth** | MP3 | 16000 Hz | Smaller files, faster streaming |

#### Modifying an Existing Profile

1. Select **"Modify Existing Profile"** 
2. Choose the profile you want to edit from the dropdown
3. Update any settings you want to change
4. Click **Submit** to save changes

#### Deleting a Profile

1. Select **"Delete Voice Profile"**
2. Choose the profile to delete from the dropdown
3. Confirm the deletion

### Using Voice Profiles

Once you've created voice profiles, you can use them in your TTS calls:

```yaml
service: tts.speak
data:
  entity_id: tts.xai_custom_tts  # Note: Default entity ID
  message: "This message uses my custom voice profile!"
  media_player_entity_id: media_player.living_room_speaker
  options:
    voice_profile: "News Reader"  # Use your saved profile
```

You can also combine voice profiles with custom options (custom options override profile settings):

```yaml
service: tts.speak
data:
  entity_id: tts.xai_custom_tts
  message: "This uses the profile but in Spanish."
  media_player_entity_id: media_player.living_room_speaker
  options:
    voice_profile: "News Reader"
    language: "es"  # This overrides the profile's language setting
```

---

## Usage

### Get Voices Service

Retrieves all available xAI voices with optional filtering:

```yaml
# Get all voices
service: xai_custom_tts.get_voices

# Search for voices
service: xai_custom_tts.get_voices
data:
  search_text: "female"  # Search by name, type, tone, or description
```

This returns a list of voices with their IDs, names, types, tones, and descriptions.

### Native TTS Integration

Use with Home Assistant's native TTS services for direct media player output:

#### Basic TTS Usage
```yaml
service: tts.speak
data:
  entity_id: tts.xai_custom_tts  # Default entity ID
  message: "Hello from Home Assistant using xAI!"
  media_player_entity_id: media_player.living_room_speaker
```

#### Advanced TTS with Custom Options
```yaml
service: tts.speak  
data:
  entity_id: tts.xai_custom_tts
  message: "Good morning! The weather today is sunny."
  media_player_entity_id: media_player.living_room_speaker
  options:
    voice: "rex"  # any built-in or custom voice_id
    language: "en"
    codec: "mp3"
    sample_rate: 24000
    bit_rate: 128000
    speed: 1.2
    text_normalization: true
```

#### Telephony-Ready Output (G.711)
```yaml
service: tts.speak  
data:
  entity_id: tts.xai_custom_tts
  message: "You have reached the automated attendant."
  media_player_entity_id: media_player.pbx_gateway
  options:
    voice: "sal"  # Neutral voice
    codec: "mulaw"  # G.711 μ-law for telephony
    sample_rate: 8000  # Standard telephony rate
```

#### Using Voice Profiles
```yaml
service: tts.speak  
data:
  entity_id: tts.xai_custom_tts
  message: "This announcement uses my custom voice profile."
  media_player_entity_id: media_player.living_room_speaker
  options:
    voice_profile: "News Anchor"  # Use your saved voice profile
```

### Example Automations

#### Morning Announcement with xAI
```yaml
automation:
  - alias: "Morning Announcement"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: tts.speak
        data:
          entity_id: tts.xai_custom_tts
          message: "Good morning! Today is {{ now().strftime('%A, %B %d') }}. The weather is {{ states('weather.home') }}."
          media_player_entity_id: media_player.bedroom_speaker
          options:
            voice: "ara"  # Warm, friendly female voice
            language: "en"
```

#### Security Alert with Authoritative Voice
```yaml
automation:
  - alias: "Security Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: "on"
    action:
      - service: tts.speak
        data:
          entity_id: tts.xai_custom_tts
          message: "Security alert: Front door has been opened."
          media_player_entity_id: media_player.living_room_speaker
          options:
            voice: "leo"  # Authoritative male voice
```

#### Multi-Language Announcement
```yaml
automation:
  - alias: "Spanish Announcement"
    trigger:
      - platform: time
        at: "12:00:00"
    action:
      - service: tts.speak
        data:
          entity_id: tts.xai_custom_tts
          message: "Buenas tardes. Es la hora del almuerzo."
          media_player_entity_id: media_player.kitchen_speaker
          options:
            voice: "eve"
            language: "es-MX"  # Spanish (Mexico)
```

#### Bedtime Story with Voice Profile
```yaml
automation:
  - alias: "Bedtime Story"
    trigger:
      - platform: time
        at: "20:00:00"
    action:
      - service: tts.speak
        data:
          entity_id: tts.xai_custom_tts
          message: "Once upon a time, in a land far away..."
          media_player_entity_id: media_player.kids_room_speaker
          options:
            voice_profile: "Storyteller"
```

---

## Parameters

### Get Voices Service Parameters

- **search_text** (optional): Search for voices by name, type, tone, or description
  - Example: "female", "male", "energetic", "professional"

**Returns:** List of voices with voice_id, name, type, tone, and description

### TTS Platform Options

When using Home Assistant's native TTS services, you can pass these options:

- **voice_profile** (optional): Use a saved voice profile by name (overrides individual settings)
- **voice** (optional): xAI `voice_id` (default: `"eve"`). Built-in IDs from `GET /v1/tts/voices` or a custom id from `GET /v1/custom-voices` / the console. Unknown IDs are not rewritten to Eve; the API returns `404`.
- **language** (optional): Language code (default: `"en"`)
  - Options: `auto`, `en`, `ar-EG`, `ar-SA`, `ar-AE`, `bn`, `zh`, `fr`, `de`, `hi`, `id`, `it`, `ja`, `ko`, `pt-BR`, `pt-PT`, `ru`, `es-MX`, `es-ES`, `tr`, `vi`
- **codec** (optional): Audio codec (default: `"mp3"`)
  - Options: `mp3`, `wav`, `pcm`, `mulaw`, `alaw`
- **sample_rate** (optional): Sample rate in Hz (default: `24000`)
  - Options: `8000`, `16000`, `22050`, `24000`, `44100`, `48000`
- **bit_rate** (optional): Bit rate for MP3 in bps (default: `128000`)
  - Options: `32000`, `64000`, `96000`, `128000`, `192000`
- **speed** (optional): Speech speed multiplier (default: `1.0`, range `0.7`–`1.5`)
- **text_normalization** (optional): Normalize written-form numbers/abbreviations before synthesis (default: `false`)
- **replace** (optional): Pronunciation map (`{"Acme Mobile": "Acme Mobull"}` or IPA values like `{"nginx": "/ˈɛndʒɪn ˈɛks/"}`). Also accepts a JSON object string.

**Note:** When using `voice_profile`, the profile settings are applied first, then any additional options override specific profile settings.

Unary `POST /v1/tts` text is limited to **60,000 characters**. Longer content needs the streaming WebSocket (`wss://api.x.ai/v1/tts`), which this integration does not implement yet.

### API fields not exposed in Home Assistant

These exist on the xAI unary/streaming TTS API but are a poor fit for HA's audio-bytes TTS entity:

| Field | Why it is omitted |
|-------|-------------------|
| `with_timestamps` | Response becomes a JSON envelope (`audio` + `audio_timestamps`) instead of raw audio |
| `optimize_streaming_latency` | Only helps streaming time-to-first-audio; HA waits for the complete file |

TTS WebSocket streaming (`wss://api.x.ai/v1/tts`) is a different product from Speech-to-Speech realtime (`wss://api.x.ai/v1/realtime`). Neither client is included here.

### Errors and retries

| HTTP | Meaning | Integration behavior |
|------|---------|----------------------|
| 400 | Bad request (empty/too-long text, bad codec/rate/`replace`) | Logged, no retry |
| 401 | Missing/invalid API key | Logged, no retry |
| 404 | Unknown `voice_id` | Logged, no retry |
| 429 / 503 / 500 | Rate limit / unavailable / server error | Retry up to 3 times with exponential backoff (1s, 2s, 4s) |

---

## 🎭 AI Prompting with Speech Tags

When using xAI Custom TTS with AI-generated messages (via the [AI Contextual TTS Announcer blueprint](https://github.com/luxus/home-assistant-goodies) or custom automations), you can use **expressive speech tags** for more natural delivery.

### Inline Tags
Place these where the expression should occur:
- Pauses: `[pause]`, `[long-pause]`, `[hum-tune]`
- Laughter & crying: `[laugh]`, `[chuckle]`, `[giggle]`, `[cry]`
- Mouth sounds: `[tsk]`, `[tongue-click]`, `[lip-smack]`
- Breathing: `[breath]`, `[inhale]`, `[exhale]`, `[sigh]`

### Wrapping Tags
Wrap text sections to change delivery style:
- `<soft>text</soft>` - Softer volume
- `<whisper>text</whisper>` - Whispered speech
- `<loud>text</loud>` - Louder speech
- `<build-intensity>text</build-intensity>` - Increasing intensity
- `<decrease-intensity>text</decrease-intensity>` - Decreasing intensity
- `<higher-pitch>text</higher-pitch>` - Higher pitch
- `<lower-pitch>text</lower-pitch>` - Lower pitch
- `<slow>text</slow>` - Slower speed
- `<fast>text</fast>` - Faster speed
- `<sing-song>text</sing-song>` - Sing-song style
- `<singing>text</singing>` - Full singing
- `<emphasis>text</emphasis>` - Emphasized words

### Example with Speech Tags
```yaml
service: tts.speak
data:
  entity_id: tts.xai_custom_tts
  message: "So I walked in and [pause] there it was. [laugh] I honestly could not believe it! <whisper>It was a secret the whole time.</whisper>"
  media_player_entity_id: media_player.living_room_speaker
```

### AI Prompt Template
Add this to your AI prompts to ensure the AI knows to use speech tags:

```
You are generating text for xAI Text-to-Speech (TTS) API.
The TTS supports expressive speech tags for natural delivery:

Inline tags: [pause], [long-pause], [laugh], [chuckle], [giggle], [cry], [tsk], 
[tongue-click], [lip-smack], [breath], [inhale], [exhale], [sigh], [hum-tune]

Wrapping tags: <soft>, <whisper>, <loud>, <build-intensity>, <decrease-intensity>,
<higher-pitch>, <lower-pitch>, <slow>, <fast>, <sing-song>, <singing>, <emphasis>

Respond ONLY with the raw spoken text including any speech tags.
No markdown, no quotes, no formatting, no explanations.
```

---

## 🚨 Troubleshooting

### Entity ID Not Found
- **Default Entity ID**: `tts.xai_custom_tts`
- **Check Entity Registry**: Go to Settings → Devices & Services → Entities and search for "xai"

### Voice Profiles Not Working
- Ensure you're using the correct `voice_profile` name (case-sensitive)
- Check that the profile exists in Settings → Integrations → xAI Custom TTS → Configure

### API Errors
- Verify your xAI API key is correct from [console.x.ai](https://console.x.ai/team/default/api-keys)
- `401` — key missing/invalid
- `404` — unknown `voice_id` (check `GET /v1/tts/voices` or `GET /v1/custom-voices`)
- `429` / `503` / `500` — retried automatically with backoff; check logs if it still fails
- `400` — empty text, over 60,000 characters, or invalid codec / `replace` map
- Check Home Assistant logs for the mapped error line
- Ensure your internet connection is stable

### Audio Quality Issues
- For higher quality, use `codec: "wav"` with `sample_rate: 44100`
- For telephony integration, use `codec: "mulaw"` with `sample_rate: 8000`
- MP3 `bit_rate` only applies when using `codec: "mp3"`

### Integration Not Loading
- Restart Home Assistant after installation
- Check that the `custom_components` directory structure is correct:
  ```
  custom_components/
  └── xai_custom_tts/
      ├── __init__.py
      ├── manifest.json
      ├── config_flow.py
      ├── tts.py
      ├── tts_request.py
      ├── voices.py
      ├── const.py
      ├── strings.json
      ├── services.yaml
      └── translations/
          └── en.json
  ```

---

## 📝 Changelog

### Version 1.1.0
- Align unary TTS options with current xAI docs: `speed`, `text_normalization`, `replace`
- Accept API-listed and custom `voice_id`s instead of rewriting unknowns to Eve
- Fetch `GET /v1/tts/voices` and `GET /v1/custom-voices` for profiles / `get_voices`
- Map `alaw` to `audio/alaw`; document 60k character limit and HTTP 400/401/404/429/503
- Rename dead realtime WS constant to `wss://api.x.ai/v1/tts` (client not implemented)
- Speech tags: drop undocumented `<laugh-speak>`

### Version 1.0.0
- **Initial Release**: Migrated from ElevenLabs to xAI Voice API
- **Simplified Voice Management**: 5 distinct voices with clear use cases
- **Multi-Language Support**: 21 languages including auto-detection
- **Voice Profiles**: Complete UI for managing voice configurations
- **Audio Formats**: MP3, WAV, PCM, G.711 μ-law, G.711 A-law support
- **Telephony Ready**: Native G.711 codec support for SIP/PBX integration

---

## Requirements

- Home Assistant 2024.8 or later
- xAI API key from [console.x.ai](https://console.x.ai/team/default/api-keys)
- Internet connection for API calls

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

If you encounter any issues, please report them on the [GitHub Issues page](https://github.com/luxus/HA-xAI-Custom-TTS/issues).

---

## xAI Voice Resources

- [xAI Text to Speech](https://docs.x.ai/developers/model-capabilities/audio/text-to-speech)
- [List voices](https://docs.x.ai/developers/rest-api-reference/inference/voice)
- [Custom voices](https://docs.x.ai/developers/model-capabilities/audio/custom-voices)
- [xAI Voice Demos](https://x.ai/api/voice)
- [Get xAI API Key](https://console.x.ai/team/default/api-keys)
