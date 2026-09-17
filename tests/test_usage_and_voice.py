"""Usage tracker and voice probe (mocked, no live keys)."""

from __future__ import annotations

import pytest

from spacexai.const import XAI_TTS_URL, XAI_VOICES_URL
from spacexai.usage import UsageTracker
from spacexai.voice_probe import async_validate_voice_access

from .fakes import FakeHttpxClient, FakeHttpxResponse


@pytest.mark.asyncio
async def test_usage_tracker_records_and_resets() -> None:
    tracker = UsageTracker(hass=None, entry_id="entry")
    await tracker.async_record(
        model="grok-4", prompt_tokens=100, completion_tokens=20, service="conversation"
    )
    assert tracker.snapshot.request_count == 1
    assert tracker.snapshot.total_tokens == 120
    assert tracker.snapshot.last_model == "grok-4"
    assert tracker.snapshot.estimated_cost_usd > 0
    await tracker.async_reset()
    assert tracker.snapshot.request_count == 0
    assert tracker.snapshot.total_tokens == 0


@pytest.mark.asyncio
async def test_voice_probe_ok_on_voices_list() -> None:
    client = FakeHttpxClient(
        FakeHttpxResponse(200, {"voices": [{"voice_id": "eve"}]}),
        expected_url=XAI_VOICES_URL,
    )
    ok, detail = await async_validate_voice_access(
        client, {"Authorization": "Bearer tok"}
    )
    assert ok is True
    assert "voices list OK" in detail


@pytest.mark.asyncio
async def test_voice_probe_falls_back_to_tts() -> None:
    client = FakeHttpxClient(
        responses=[
            FakeHttpxResponse(404, {"error": "nope"}),
            FakeHttpxResponse(200, b"ID3"),
        ]
    )
    ok, detail = await async_validate_voice_access(
        client, {"Authorization": "Bearer tok"}
    )
    assert ok is True
    assert "TTS probe OK" in detail
    assert client.calls[1]["url"] == XAI_TTS_URL


@pytest.mark.asyncio
async def test_voice_probe_denied() -> None:
    client = FakeHttpxClient(FakeHttpxResponse(403, "no voice"))
    ok, detail = await async_validate_voice_access(
        client, {"Authorization": "Bearer tok"}
    )
    assert ok is False
    assert "403" in detail
