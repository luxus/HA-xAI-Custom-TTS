# HA-xAI-Custom-TTS

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/luxus/HA-xAI-Custom-TTS.svg)](https://github.com/luxus/HA-xAI-Custom-TTS/releases/)

A xAI (Grok) TTS integration for Home Assistant that provides voice synthesis using xAI's Text-to-Speech API and integrates with Home Assistant's native TTS platform.

This custom component provides:
1. **Get Voices Service** - Retrieve available xAI voices (Eve, Ara, Rex, Sal, Leo)
2. **Native TTS Platform** - Full integration with Home Assistant's TTS system
3. **Voice Profile Management** - Create, modify, and delete named voice profiles with full audio format control
4. **Flexible Output Formats** - MP3, WAV, PCM, and telephony codecs (G.711 μ-law/A-law) with configurable sample rates

### Why use this instead of other TTS integrations?
- 🎙️ **Simple & Clean** – xAI provides 5 high-quality voices without complex parameter tuning
- 🌍 **21 Languages** – Natural pronunciation with auto-detection support
- 🔧 **Voice Profiles** – Define multiple voice configurations with codec, sample rate, and bit rate settings
- 📞 **Telephony Ready** – Native G.711 codec support for SIP/PBX integration
- 🚀 **Enterprise Ready** – SOC 2 Type II, HIPAA eligible, GDPR compliant

> **🙏 Credits**: This integration is based on the excellent work of [@loryanstrant](https://github.com/loryanstrant) and the [HA-ElevenLabs-Custom-TTS](https://github.com/loryanstrant/HA-ElevenLabs-Custom-TTS) project. The voice profile management system and architecture were adapted from that original integration.

---

## ✨ Features

> **📝 Note:** The default TTS entity ID is `tts.xai_custom_tts`. This is used in all the examples below.

### Voice Discovery
- **5 Distinct Voices**: Eve (energetic female), Ara (warm female), Rex (professional male), Sal (neutral), Leo (authoritative male)
- **Voice Search**: Search voices by name, type, tone, or description
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
   - **Voice**: Choose from the 5 xAI voices
   - **Language**: Select the language code (default: "en", or use "auto" for auto-detection)
   - **Audio Codec**: Select output format (MP3, WAV, PCM, G.711 μ-law, G.711 A-law)
   - **Sample Rate**: Audio quality (24000 Hz default, lower for telephony)
   - **Bit Rate**: Compression quality for MP3 (128000 bps default)
3. Click **Submit** to save the profile

#### Available Voices

| Voice | Type | Tone | Best For |
|-------|------|------|----------|
| **Eve** | Female | Energetic, upbeat | Engaging announcements, energetic content |
| **Ara** | Female | Warm, friendly | Conversational interactions, friendly greetings |
| **Rex** | Male | Confident, clear | Professional announcements, business content |
| **Sal** | Neutral | Smooth, balanced | General purpose, versatile contexts |
| **Leo** | Male | Authoritative, strong | Instructions, alerts, important announcements |

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
    voice: "rex"  # xAI voice ID: eve, ara, rex, sal, leo
    language: "en"
    codec: "mp3"
    sample_rate: 24000
    bit_rate: 128000
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
- **voice** (optional): xAI voice ID to use (default: "eve")
  - Options: `eve`, `ara`, `rex`, `sal`, `leo`
- **language** (optional): Language code (default: "en")
  - Options: `auto`, `en`, `ar-EG`, `ar-SA`, `ar-AE`, `bn`, `zh`, `fr`, `de`, `hi`, `id`, `it`, `ja`, `ko`, `pt-BR`, `pt-PT`, `ru`, `es-MX`, `es-ES`, `tr`, `vi`
- **codec** (optional): Audio codec (default: "mp3")
  - Options: `mp3`, `wav`, `pcm`, `mulaw`, `alaw`
- **sample_rate** (optional): Sample rate in Hz (default: 24000)
  - Options: `8000`, `16000`, `22050`, `24000`, `44100`, `48000`
- **bit_rate** (optional): Bit rate for MP3 in bps (default: 128000)
  - Options: `32000`, `64000`, `96000`, `128000`, `192000`

**Note:** When using `voice_profile`, the profile settings are applied first, then any additional options override specific profile settings.

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
- Check Home Assistant logs for detailed error messages
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
      ├── const.py
      ├── strings.json
      ├── services.yaml
      └── translations/
          └── en.json
  ```

---

## 📝 Changelog

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

- [xAI Voice API Documentation](https://docs.x.ai/docs/api-reference#text-to-speech)
- [xAI Voice Demos](https://x.ai/api/voice)
- [Get xAI API Key](https://console.x.ai/team/default/api-keys)
