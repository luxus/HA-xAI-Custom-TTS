# SpaceXAI (Home Assistant umbrella)

<p align="center">
  <img src="https://pbs.twimg.com/profile_images/1769430779845611520/lIgjSJGU_400x400.jpg" alt="xAI Logo" width="120">
</p>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/luxus/ha-spacexai.svg)](https://github.com/luxus/ha-spacexai/releases/)

**SpaceXAI** is the Home Assistant umbrella for Grok: **one config entry after OAuth**, then platforms load under that entry.

| Layer | Repo | Role |
| --- | --- | --- |
| 1. Auth library | [`luxus/ha-spacexai-auth`](https://github.com/luxus/ha-spacexai-auth) | Device-code + PKCE, `ensure_fresh`, `TokenSet` entry keys. No HA domain. |
| 2. **This integration** | [`luxus/ha-spacexai`](https://github.com/luxus/ha-spacexai) (HACS name **SpaceXAI**) | Domain **`spacexai`**. Conversation **Grok** + **TTS** + **STT**. |
| 3. Router | [`luxus/ha-conversation-jev`](https://github.com/luxus/ha-conversation-jev) (`jev_assist`) | Thin classifier / light fast-path only. On `grok` routes it should hand off to **this** conversation agent. |

This is **not** Home Assistant Application Credentials.

### Platforms this entry loads

After setup, Home Assistant forwards the single config entry to:

| Platform | Entity ID | Unique ID | Name | API |
| --- | --- | --- | --- | --- |
| `conversation` | **`conversation.spacexai_grok`** | `spacexai_grok` | Grok | `https://api.x.ai/v1/responses` |
| `tts` | **`tts.spacexai_tts`** | `spacexai_tts` | TTS | `https://api.x.ai/v1/tts` |
| `stt` | **`stt.spacexai_stt`** | `spacexai_stt` | STT | `https://api.x.ai/v1/stt` |

All three use the same `Authorization: Bearer …` from `ensure_fresh` / `ha_spacexai_auth` (OAuth access token or API-key fallback). STT is **not** OpenAI Whisper-compatible (`/v1/audio/transcriptions` does not exist on api.x.ai).

**jev_assist handoff target:** `conversation.spacexai_grok`

---

## Breaking change: domain `xai_custom_tts` → `spacexai`

**This is a clean domain rename.** Home Assistant config entries are keyed by domain, so existing **xAI Custom TTS** entries do **not** migrate automatically.

1. Note any TTS voice profiles you care about (they live on the old entry's options).
2. Remove **xAI Custom TTS** (**Settings → Devices & services**).
3. If HACS left `config/custom_components/xai_custom_tts/` behind after the update, delete that folder.
4. Restart Home Assistant.
5. Add **SpaceXAI** and sign in with Grok (OAuth) or paste the same console API key as fallback.
6. Recreate voice profiles if needed. Point automations at `tts.spacexai_tts` (was `tts.xai_custom_tts`) and `spacexai.get_voices` (was `xai_custom_tts.get_voices`).
7. Point Assist pipelines at `conversation.spacexai_grok`, `stt.spacexai_stt`, and `tts.spacexai_tts`.

Within the new domain, config-entry **version 2** stores `auth_method` (`oauth` \| `api_key`) plus `TokenSet` keys (`access_token`, `refresh_token`, `expires_at`, `token_type`, `scope`). A v1 API-key-only payload is migrated in `async_migrate_entry` if it is ever loaded under `spacexai`.

The **GitHub / HACS repository URL** is `luxus/ha-spacexai`. The Home Assistant domain remains **`spacexai`**.

---

## Architecture

```
Assist pipeline
        │
        ├─ STT  stt.spacexai_stt
        │         Bearer from ensure_fresh
        │         collect PCM/WAV → POST https://api.x.ai/v1/stt (multipart, file last)
        │
        ├─ conversation
        │         │
        │         ▼
        │   jev_assist (optional router)
        │         │  kind=fast_service → HA light service
        │         │  kind=reject       → canned refusal
        │         │  kind=grok         → hand off
        │         ▼
        │   conversation.spacexai_grok
        │         Bearer from ensure_fresh
        │         mode=tools → POST /v1/chat/completions + Assist LLM tools
        │         live search → POST /v1/responses (web_search / x_search)
        │         real HassTurnOn / HassTurnOff (exposed entities only)
        │
        └─ TTS  tts.spacexai_tts
                  Bearer from ensure_fresh
                  POST https://api.x.ai/v1/tts
```

OAuth uses the public Grok CLI client from `ha-spacexai-auth` (device code + PKCE S256 at `https://auth.x.ai`). Setup/reload calls `ensure_fresh` (refresh when `expires_at` is within 60s). Rotated refresh tokens are persisted. API key for `https://api.x.ai` is **fallback only** (same pattern as `jev_assist`).

---

## Enable path

1. Install **SpaceXAI** (HACS or manual) and restart Home Assistant.  
   Manifest requirement: `ha-spacexai-auth@git+https://github.com/luxus/ha-spacexai-auth.git@main`
2. **Settings → Devices & services → Add integration → SpaceXAI**
3. **Sign in with Grok** (default). Home Assistant shows a URL + user code, polls the token endpoint, and stores access + refresh tokens.  
   Or choose **xAI API key** if OAuth entitlement is missing / you bill via [console.x.ai](https://console.x.ai/team/default/api-keys).
4. Confirm three entities on the SpaceXAI device:
   - `conversation.spacexai_grok` (name **Grok**)
   - `tts.spacexai_tts` (name **TTS**)
   - `stt.spacexai_stt` (name **STT**)
5. **Assist pipeline**
   - Conversation agent: **Grok**, **or** Jev Assist with a grok handoff (see below)
   - Speech-to-text: **STT** (`stt.spacexai_stt`)
   - Text-to-speech: **TTS** (`tts.spacexai_tts`)
6. Optional: **Configure** on the integration to add TTS voice profiles.

---

## How `jev_assist` should hand off

`jev_assist` stays a **thin router**. Do not implement Grok inside that repo. When `route(...).kind == "grok"`, hand the utterance to this umbrella's conversation agent:

```python
from homeassistant.components import conversation

# After Jev routes kind == "grok":
result = await conversation.async_converse(
    hass,
    text=user_input.text,
    conversation_id=user_input.conversation_id,
    context=user_input.context,
    language=user_input.language,
    agent_id="conversation.spacexai_grok",
)
```

Until that handoff ships in `jev_assist`, set the Assist pipeline conversation agent to **Grok** (this integration). This repository does **not** change `jev_assist`.

---

## Installation

### Via HACS (Recommended)

1. Open HACS → **Integrations**
2. Custom repositories → `https://github.com/luxus/ha-spacexai` → category **Integration**
3. Install **SpaceXAI**, restart Home Assistant
4. **Settings → Devices & services → Add integration → SpaceXAI**

[![Open your Home Assistant instance and open a repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=luxus&repository=ha-spacexai&category=integration)

### Manual Installation

1. Copy `custom_components/spacexai` into your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the **SpaceXAI** integration

---

## Conversation (Grok)

The **Grok** conversation entity (`conversation.spacexai_grok`) is a full Assist LLM agent, ported from the proven [`braytonstafford/grok_conversation`](https://github.com/braytonstafford/grok_conversation) patterns, still authenticated with `ha_spacexai_auth` (OAuth device code + `ensure_fresh`, or API-key fallback). It does **not** use Application Credentials.

| Capability | How it works |
| --- | --- |
| **Assist LLM HASS API tools** | Real device control. Grok calls HA tools (`HassTurnOn`, `HassTurnOff`, timers, …). Tool JSON schemas are sanitized for xAI (anyOf/oneOf merged). Tool results are passed through — Grok must not invent a successful action. |
| **Live Search** | `off` / `web` / `x` / `full`. Responses API server tools `web_search` / `x_search`. Citations appended on text chat; skipped on satellite/voice. Two-pass when Assist tools are on: search brief → tool loop. |
| **Interaction modes** | `tools` (default) · `pipeline` (built-in HA intent first, then Grok) · `chat_only` (no device control) |
| **Model pickers** | Chat / fast / fallback from live `GET https://api.x.ai/v1/models` (image/voice models filtered). Auto-routing sends short commands to the fast model. |
| **Services** | `spacexai.ask`, `photo_analysis`, `home_briefing`, `generate_image`, `generate_content` (+ `query_image`, `clear_memory`, `reset_stats`, `get_voices`) |
| **Voice probe** | Setup probes `/v1/tts/voices` (then a tiny TTS POST). Conversation still loads if Voice is denied. |
| **Usage sensors** | Diagnostic token/cost counters on the SpaceXAI device |

Default chat model: `grok-4.3-latest` (overridable from the live list). Default LLM HASS API: **Assist**.

### How Assist tools work (lights end-to-end)

1. **Expose the light** to Assist: *Settings → Voice assistants → Expose* (or entity *Settings → Voice assistants* toggle). Unexposed entities are invisible to the LLM API.
2. **One SpaceXAI entry** (OAuth or API key). Confirm `conversation.spacexai_grok` exists.
3. **Configure → Conversation:**
   - **LLM HASS API** = **Assist** (not “No control”)
   - **Interaction mode** = **Tool Control** (`tools`)
   - Optional: Live Search `web`/`x`/`full`
4. **Assist pipeline:** Conversation agent = **Grok** (`conversation.spacexai_grok`). TTS/STT can stay `tts.spacexai_tts` / `stt.spacexai_stt`.
5. Say or type: **“Turn on the kitchen light.”**
6. What happens:
   1. Mode `tools` skips the built-in intent pipeline.
   2. `chat_log.async_provide_llm_data` attaches the Assist LLM API tools for exposed entities.
   3. Grok is called on `POST https://api.x.ai/v1/chat/completions` with those function tools.
   4. The model returns a `HassTurnOn` (or similar) tool call. SpaceXAI executes it via `ToolInput` / `llm_api.async_call_tool` — **a real HA service call**, not a stub.
   5. The raw tool payload is sent back to Grok. Only after a successful result may Grok say the light is on.
7. Confirm in **Developer Tools → States** that `light.kitchen` (or whatever you exposed) is `on`, and in HA logs a debug line `Tool HassTurnOn result: …`.

`chat_only` never sends HA tools. `pipeline` tries `conversation.home_assistant` first and only falls through to Grok tools if the built-in agent produces a “sorry / not aware” style reply.

Live Search in `tools` mode uses an allow-list (news, scores, weather, “near me”, …) so “turn on the lights” does not waste a search pass. In `pipeline` mode a deny-list is used instead. When both search and tools apply, the search brief is injected into the tool-loop system prompt (two-pass).

---

## Configuration options

Open **Settings → Devices & services → SpaceXAI → Configure**.

| Option | Notes |
| --- | --- |
| LLM HASS API | Assist control (not “No control”) |
| Interaction mode | `tools` / `pipeline` / `chat_only` |
| Chat / fast / fallback model | Live list from xAI `/v1/models` |
| Live Search | off / web / x / full |
| Show citations | Text chat only (not spoken Assist) |
| Voice-optimized replies | Short spoken answers |
| Auto-route to fast model | Short commands |
| Home context | Time, presence, weather |
| Location context | For “near me” live search |
| TTS voice profiles | Existing profile manager (unchanged) |

---

## Services

All take a `config_entry` selector for the SpaceXAI entry.

| Service | Purpose |
| --- | --- |
| `spacexai.ask` | Stateless instructions + input_data, optional live search |
| `spacexai.photo_analysis` | Vision over paths or `http(s)` URLs |
| `spacexai.home_briefing` | Snapshot HA entities → spoken status |
| `spacexai.generate_image` | Grok Imagine (`/v1/images/generations`) |
| `spacexai.generate_content` | Prompt (+ optional local image files) |
| `spacexai.query_image` | Legacy alias for photo analysis |
| `spacexai.clear_memory` | Reload the entry |
| `spacexai.reset_stats` | Zero usage sensors |
| `spacexai.get_voices` | List TTS voices |

---

## STT

Default STT entity ID is **`stt.spacexai_stt`**.

Home Assistant Assist STT is a collected-stream entity (`SpeechToTextEntity.async_process_audio_stream`): PCM/WAV bytes are gathered, wrapped as WAV when headerless, then posted as multipart `POST https://api.x.ai/v1/stt`. Option fields (`model=grok-voice-transcribe-2.0`, `language`, `format=true` for inverse text normalization) are sent **before** `file`, as required by xAI.

- Assist `en-US` / `en-GB` map to xAI `language=en` (and similarly for other BCP-47 tags).
- Typical Assist input: 16-bit PCM, 16 kHz, mono.
- Streaming WebSocket `wss://api.x.ai/v1/stt` is **not** used on this entity (Assist is not a live WS client).

Point the Assist pipeline **Speech-to-text** engine at `stt.spacexai_stt`.

---

## TTS

Default TTS entity ID is **`tts.spacexai_tts`**. Voice profiles, codecs, speed, text normalization, pronunciation `replace`, and speech tags work on the same entry.

### Voice Profile Management

**Settings → Devices & services → SpaceXAI → Configure**

Built-in voices include Eve, Ara, Rex, Sal, Leo plus 20 more catalog IDs (Luna, Helios, Zagan, … — 25+ total) from `GET /v1/tts/voices`. Custom voices from `GET /v1/custom-voices` appear when the team has them enabled. Codecs: MP3, WAV, PCM, G.711 μ-law/A-law.

```yaml
service: tts.speak
data:
  entity_id: tts.spacexai_tts
  message: "Hello from Grok TTS"
  media_player_entity_id: media_player.living_room_speaker
  options:
    voice: "ara"
    language: "en"
    codec: "mp3"
    sample_rate: 24000
    speed: 1.0
    # or: voice_profile: "News Reader"
```

### Get Voices

```yaml
service: spacexai.get_voices
data:
  search_text: "female"
```

### TTS options

- **voice_profile** — saved profile name
- **voice** — `eve`, `ara`, `rex`, `sal`, `leo`, extra built-in IDs, or a custom `voice_id`
- **language** — `auto`, `en`, `ar-EG`, `ar-SA`, `ar-AE`, `bn`, `zh`, `fr`, `de`, `hi`, `id`, `it`, `ja`, `ko`, `pt-BR`, `pt-PT`, `ru`, `es-MX`, `es-ES`, `tr`, `vi`
- **codec** — `mp3`, `wav`, `pcm`, `mulaw`, `alaw`
- **sample_rate** — `8000`, `16000`, `22050`, `24000`, `44100`, `48000`
- **bit_rate** — MP3 only: `32000`–`192000`
- **speed** — `0.7`–`1.5`
- **text_normalization** — boolean
- **replace** — JSON object of phrase → pronunciation (max 200 entries)

### Speech tags

Inline: `[pause]`, `[laugh]`, `[sigh]`, …  
Wrapping: `<whisper>…</whisper>`, `<emphasis>…</emphasis>`, …

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

No live xAI keys are required. Tests cover `TokenSet` config-entry roundtrip, `ensure_entry_tokens` / `ensure_fresh`, domain/manifest requirements, Grok conversation against mocked HTTP, **Assist tool routing / interaction modes with mocks**, TTS payload/voice parsers, STT multipart (`file` last, language map, transcript extract), usage sensors, and the Voice API probe.

---

## Requirements

- Home Assistant 2024.8 or later
- Grok OAuth (default) or an xAI API key from [console.x.ai](https://console.x.ai/team/default/api-keys)
- Shared library [`ha-spacexai-auth`](https://github.com/luxus/ha-spacexai-auth)

---

## Changelog

### Version 2.1.2

- Pin unary STT to `grok-voice-transcribe-2.0` (`model` multipart field on `POST /v1/stt`). xAI still defaults to `grok-voice-transcribe-1.0` when the field is omitted.

### Version 2.1.1

- Fix Assist handoff crash: converting ChatLog tool calls no longer `hash()`s unhashable Home Assistant `ToolInput` objects (`tool_name` + `tool_args`). Fallback ids are JSON-safe strings (`id` / `tool_call_id` / `call_{n}_{uuid}`).

### Version 2.1.0

- Conversation feature parity with `grok_conversation`: Assist LLM HASS API tools (real device control), live search + citations, interaction modes (`tools` / `pipeline` / `chat_only`), live model pickers, ask / photo_analysis / home_briefing / image+content services, Voice API probe, usage sensors
- TTS fallback catalog expanded to 25+ voices; OAuth via `ha_spacexai_auth` unchanged
- Stable entity IDs: `conversation.spacexai_grok`, `tts.spacexai_tts`, `stt.spacexai_stt`

### Version 2.0.0

- **Breaking:** HA domain `xai_custom_tts` → `spacexai` (see migration above)
- Umbrella config entry: OAuth-first via `ha-spacexai-auth` (device code + PKCE); API-key fallback
- Conversation platform entity **Grok** → `conversation.spacexai_grok` → `https://api.x.ai/v1/responses`
- TTS kept on the same entry / auth headers → `tts.spacexai_tts` (speed, text_normalization, replace, extra/custom voices)
- STT platform → `stt.spacexai_stt` → `POST https://api.x.ai/v1/stt`

### Version 1.0.0

- Initial TTS-only release (legacy domain `xai_custom_tts`)

---

## License

MIT — see [LICENSE](LICENSE).

## Support

[GitHub Issues](https://github.com/luxus/ha-spacexai/issues)

## xAI resources

- [Speech to text](https://docs.x.ai/developers/model-capabilities/audio/speech-to-text)
- [xAI Voice / TTS](https://docs.x.ai/docs/api-reference#text-to-speech)
- [Responses API](https://docs.x.ai/docs/api-reference#responses)
- [Get an API key](https://console.x.ai/team/default/api-keys)
