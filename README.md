# SpaceXAI (Home Assistant umbrella)

<p align="center">
  <img src="https://pbs.twimg.com/profile_images/1769430779845611520/lIgjSJGU_400x400.jpg" alt="xAI Logo" width="120">
</p>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/luxus/HA-xAI-Custom-TTS.svg)](https://github.com/luxus/HA-xAI-Custom-TTS/releases/)

**SpaceXAI** is the Home Assistant umbrella for Grok: **one config entry after OAuth**, then platforms load under that entry.

| Layer | Repo | Role |
| --- | --- | --- |
| 1. Auth library | [`luxus/ha-spacexai-auth`](https://github.com/luxus/ha-spacexai-auth) | Device-code + PKCE, `ensure_fresh`, `TokenSet` entry keys. No HA domain. |
| 2. **This integration** | `luxus/HA-xAI-Custom-TTS` (HACS name **SpaceXAI**) | Domain **`spacexai`**. Conversation agent **Grok** + existing **TTS**. STT later. |
| 3. Router | [`luxus/ha-conversation-jev`](https://github.com/luxus/ha-conversation-jev) (`jev_assist`) | Thin classifier / light fast-path only. On `grok` routes it should hand off to **this** conversation agent. |

This is **not** Home Assistant Application Credentials.

### Platforms this entry loads

After setup, Home Assistant forwards the single config entry to:

- **`conversation`** — entity **Grok** (`conversation.spacexai_grok`) talking to `https://api.x.ai/v1/responses` (Chat Completions JSON is still parsed if returned)
- **`tts`** — entity **TTS** (`tts.spacexai_tts`) using the existing xAI Voice path (`https://api.x.ai/v1/tts`)

STT is out of scope.

---

## Breaking change: domain `xai_custom_tts` → `spacexai`

**This is a clean domain rename.** Home Assistant config entries are keyed by domain, so existing **xAI Custom TTS** entries do **not** migrate automatically.

1. Note any TTS voice profiles you care about (they live on the old entry's options).
2. Remove **xAI Custom TTS** (**Settings → Devices & services**).
3. If HACS left `config/custom_components/xai_custom_tts/` behind after the update, delete that folder.
4. Restart Home Assistant.
5. Add **SpaceXAI** and sign in with Grok (OAuth) or paste the same console API key as fallback.
6. Recreate voice profiles if needed. Point automations at `tts.spacexai_tts` (was `tts.xai_custom_tts`) and `spacexai.get_voices` (was `xai_custom_tts.get_voices`).

Within the new domain, config-entry **version 2** stores `auth_method` (`oauth` \| `api_key`) plus `TokenSet` keys (`access_token`, `refresh_token`, `expires_at`, `token_type`, `scope`). A v1 API-key-only payload is migrated in `async_migrate_entry` if it is ever loaded under `spacexai`.

The **GitHub / HACS repository URL** stays `luxus/HA-xAI-Custom-TTS` for now.

---

## Architecture

```
Assist / conversation.process
        │
        ▼
  jev_assist (optional router)
        │  kind=fast_service → HA light service
        │  kind=reject       → canned refusal
        │  kind=grok         → hand off
        ▼
  spacexai conversation “Grok”
        │  Authorization: Bearer <oauth access_token | api_key>
        ▼
  https://api.x.ai/v1/responses   (same auth headers as TTS)
        │
        ▼
  real Grok prose (Assist tools are a stub; no HA service calls from Grok yet)

TTS (tts.speak → tts.spacexai_tts) uses the same config entry and Bearer token
against https://api.x.ai/v1/tts.
```

OAuth uses the public Grok CLI client from `ha-spacexai-auth` (device code + PKCE S256 at `https://auth.x.ai`). Setup/reload calls `ensure_fresh` (refresh when `expires_at` is within 60s). Rotated refresh tokens are persisted. API key for `https://api.x.ai` is **fallback only** (same pattern as `jev_assist`).

---

## Enable path

1. Install **SpaceXAI** (HACS or manual) and restart Home Assistant.  
   Manifest requirement: `ha-spacexai-auth @ git+https://github.com/luxus/ha-spacexai-auth.git@main`
2. **Settings → Devices & services → Add integration → SpaceXAI**
3. **Sign in with Grok** (default). Home Assistant shows a URL + user code, polls the token endpoint, and stores access + refresh tokens.  
   Or choose **xAI API key** if OAuth entitlement is missing / you bill via [console.x.ai](https://console.x.ai/team/default/api-keys).
4. Confirm two entities on the SpaceXAI device:
   - `conversation.spacexai_grok` (name **Grok**)
   - `tts.spacexai_tts` (name **TTS**)
5. **Assist pipeline**
   - Use **Grok** directly as the conversation agent, **or**
   - Use **Jev Assist** as the pipeline agent and have it hand off `grok` routes here (see below).
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
2. Custom repositories → `https://github.com/luxus/HA-xAI-Custom-TTS` → category **Integration**
3. Install **SpaceXAI**, restart Home Assistant
4. **Settings → Devices & services → Add integration → SpaceXAI**

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=luxus&repository=HA-xAI-Custom-TTS&category=integration)

### Manual Installation

1. Copy `custom_components/spacexai` into your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the **SpaceXAI** integration

---

## Conversation (Grok)

The **Grok** conversation entity calls `https://api.x.ai/v1/responses` with the same `Authorization: Bearer …` headers used for TTS (`ha_spacexai_auth.authorization_headers`). It returns Grok's assistant text as Assist speech. Home Assistant LLM tool-calling is stubbed: Grok will talk about devices but will not execute services (Jev's fast path covers lights).

Default model: `grok-4`.

---

## TTS

Default TTS entity ID is **`tts.spacexai_tts`**. Voice profiles, codecs, and speech tags work as before.

### Voice Profile Management

**Settings → Devices & services → SpaceXAI → Configure**

Voices: Eve, Ara, Rex, Sal, Leo. Codecs: MP3, WAV, PCM, G.711 μ-law/A-law.

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
- **voice** — `eve` \| `ara` \| `rex` \| `sal` \| `leo`
- **language** — `auto`, `en`, `ar-EG`, `ar-SA`, `ar-AE`, `bn`, `zh`, `fr`, `de`, `hi`, `id`, `it`, `ja`, `ko`, `pt-BR`, `pt-PT`, `ru`, `es-MX`, `es-ES`, `tr`, `vi`
- **codec** — `mp3`, `wav`, `pcm`, `mulaw`, `alaw`
- **sample_rate** — `8000`, `16000`, `22050`, `24000`, `44100`, `48000`
- **bit_rate** — MP3 only: `32000`–`192000`

### Speech tags

Inline: `[pause]`, `[laugh]`, `[sigh]`, …  
Wrapping: `<whisper>…</whisper>`, `<emphasis>…</emphasis>`, …

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

No live xAI keys are required. Tests cover `TokenSet` config-entry roundtrip, `ensure_entry_tokens` / `ensure_fresh`, domain/manifest requirements, and a Grok conversation client smoke test against mocked HTTP.

---

## Requirements

- Home Assistant 2024.8 or later
- Grok OAuth (default) or an xAI API key from [console.x.ai](https://console.x.ai/team/default/api-keys)
- Shared library [`ha-spacexai-auth`](https://github.com/luxus/ha-spacexai-auth)

---

## Changelog

### Version 2.0.0

- **Breaking:** HA domain `xai_custom_tts` → `spacexai` (see migration above)
- Umbrella config entry: OAuth-first via `ha-spacexai-auth` (device code + PKCE); API-key fallback
- Conversation platform entity **Grok** → `https://api.x.ai/v1/responses`
- TTS kept on the same entry / auth headers
- STT not included

### Version 1.0.0

- Initial TTS-only release (legacy domain `xai_custom_tts`)

---

## License

MIT — see [LICENSE](LICENSE).

## Support

[GitHub Issues](https://github.com/luxus/HA-xAI-Custom-TTS/issues)

## xAI resources

- [xAI Voice API](https://docs.x.ai/docs/api-reference#text-to-speech)
- [Responses API](https://docs.x.ai/docs/api-reference#responses)
- [Get an API key](https://console.x.ai/team/default/api-keys)
