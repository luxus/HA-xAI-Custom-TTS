# xAI TTS API alignment review (docs as of 2026-09)

Compared [Text to Speech](https://docs.x.ai/developers/model-capabilities/audio/text-to-speech), [List voices](https://docs.x.ai/developers/rest-api-reference/inference/voice), and [Custom voices](https://docs.x.ai/developers/model-capabilities/audio/custom-voices) against `custom_components/xai_custom_tts`.

Auth stays **API key** (`Authorization: Bearer`). Grok OAuth is out of scope.

| Area | Docs | Before | After |
|------|------|--------|-------|
| Unary TTS | `POST https://api.x.ai/v1/tts`, nested `output_format.{codec,sample_rate,bit_rate}` | Already matched | Unchanged |
| `speed` | `0.7`–`1.5`, default `1.0` | Not exposed | HA option + voice-profile field |
| `text_normalization` | bool, default `false` | Not exposed | HA option + voice-profile field |
| `replace` | phrase → pronunciation map | Not exposed | HA option (`dict` or JSON object string) |
| `optimize_streaming_latency` | `0`/`1`/`2` (streaming TTFA) | Not exposed | **Unsupported** — unary HA waits for the full file |
| `with_timestamps` | JSON envelope (`audio` + `audio_timestamps`) | Not exposed | **Unsupported** — HA TTS needs raw audio bytes |
| Voices | `GET /v1/tts/voices` → `voices[].voice_id`, `name` (+ `language`) | Hardcoded 5; unknown IDs rewritten to `eve` | Live list; unknown/custom IDs passed through; `404` logged |
| Custom voices | `GET /v1/custom-voices` (`voice_id` 8-char lowercase) | Rejected by `XAI_VOICES` allow-list | Fetched into profile dropdown + `get_voices`; 403 skipped |
| `alaw` Content-Type | `audio/alaw` | Mapped to `audio/basic` | `audio/alaw` (`mulaw` stays `audio/basic`) |
| Streaming URL | TTS WS `wss://api.x.ai/v1/tts` | Dead `XAI_REALTIME_URL = wss://api.x.ai/v1/realtime` (Speech-to-Speech) | Renamed `XAI_TTS_WS_URL`; **no WS client** (follow-up) |
| Text limit | 60,000 chars unary | Unchecked (30s timeout) | Pre-check 60k; timeout 120s |
| Errors | 400/401/404/429/503 (+500 retry) | Generic `raise_for_status` | Mapped log lines; retry 429/500/503 (3× backoff) |
| Languages | 21 codes + `auto` | Matched | Unchanged |
| Speech tags | Inline `[pause]`…`[sigh]`; wrapping `<soft>`…`<emphasis>` | README had extra `<laugh-speak>` | README aligned; `<laugh-speak>` removed |
| Built-in roster | REST example includes Carina/Luna/… plus Eve/Ara/Rex/Sal/Leo | Docs/UI said “5 voices” | Discover from API; 5 kept as labeled fallback |

## Intentionally not in this change

- OAuth / SuperGrok login
- WebSocket streaming TTS client (`wss://api.x.ai/v1/tts`)
- STT / Speech-to-Speech (`wss://api.x.ai/v1/realtime`)

## Smoke

No live xAI key in this environment. Offline checks:

```bash
python -m unittest tests.test_tts_request -v
```

Manual (needs `XAI_API_KEY`):

1. `GET https://api.x.ai/v1/tts/voices` — confirm `voices[].voice_id` / `name`.
2. `tts.speak` with `voice: eve`, then a custom id from `GET /v1/custom-voices`.
3. `options.speed: 1.2` and `text_normalization: true`.
4. Unknown `voice_id` should log HTTP 404, not silently become Eve.
5. `codec: alaw` still synthesizes (telephony).
