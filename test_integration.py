"""Optional live TTS check. Unit tests live in tests/ (no keys required)."""

import asyncio
import os

import httpx

XAI_TTS_URL = "https://api.x.ai/v1/tts"


async def test_xai_tts():
    """Hit xAI TTS with XAI_API_KEY if set."""
    api_key = os.environ.get("XAI_API_KEY")

    if not api_key:
        print("Skipping live TTS: XAI_API_KEY is not set. Run: pytest")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": "Hello from SpaceXAI TTS.",
        "voice_id": "eve",
        "language": "en",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                XAI_TTS_URL,
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            audio_data = response.content
            with open("test_output.mp3", "wb") as f:
                f.write(audio_data)
            print(f"Success! Generated {len(audio_data)} bytes of audio")
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_xai_tts())
