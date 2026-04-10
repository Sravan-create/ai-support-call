import os
import httpx
import logging
import base64

logger = logging.getLogger(__name__)

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

# Always use Rahul — Indian English male, bulbul:v3 only.
# Single consistent voice throughout the entire call. No switching.
MODEL    = "bulbul:v3"
SPEAKER  = "rahul"
LANGUAGE = "en-IN"


async def synthesize_speech(text: str) -> bytes:
    """
    Calls Sarvam AI TTS (bulbul:v3) — always Rahul, always Indian English.
    Consistent voice throughout every call, no mid-call switching.
    """
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not api_key:
        logger.error("SARVAM_API_KEY is not set.")
        raise ValueError("SARVAM_API_KEY is missing")

    logger.info(f"Sarvam TTS | speaker={SPEAKER} | '{text[:80]}'")

    payload = {
        "inputs":               [text],
        "target_language_code": LANGUAGE,
        "speaker":              SPEAKER,
        "model":                MODEL,
        "pace":                 1.1,
        "speech_sample_rate":   22050,
    }

    headers = {
        "api-subscription-key": api_key,
        "Content-Type":         "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(SARVAM_TTS_URL, json=payload, headers=headers)
            response.raise_for_status()
            data   = response.json()
            audios = data.get("audios", [])
            if not audios:
                logger.error(f"Sarvam returned no audio. Response: {data}")
                return b""
            return base64.b64decode(audios[0])
        except httpx.HTTPStatusError as e:
            logger.error(f"Sarvam TTS HTTP {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Sarvam TTS failed: {e}")
            raise
