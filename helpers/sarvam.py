import os
import httpx
import logging
import base64

logger = logging.getLogger(__name__)

SARVAM_BASE_URL = "https://api.sarvam.ai/text-to-speech"

async def synthesize_speech(text: str) -> bytes:
    """
    Calls Sarvam AI Text-to-Speech API to convert text to audio.
    Returns:
        bytes: The decoded raw audio data.
    """
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        logger.error("SARVAM_API_KEY is not set in environment.")
        raise ValueError("SARVAM_API_KEY is missing")

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    # You can customize these based on Sarvam's 'bulbul:v3' or other params if needed
    payload = {
        "inputs": [text],
        "target_language_code": "en-IN",
        "speaker": "meera",
        "pitch": 0,
        "pace": 1.0,
        "loudness": 1.5,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True,
        "model": "bulbul:v1"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                SARVAM_BASE_URL,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            # Sarvam returns an array of audios as base64 string
            audios = data.get("audios", [])
            if not audios:
                logger.error(f"No audio returned from Sarvam API. Payload: {payload}")
                return b""

            base64_audio = audios[0]
            raw_audio = base64.b64decode(base64_audio)
            
            return raw_audio
            
        except Exception as e:
            logger.error(f"Failed to synthesize speech via Sarvam API: {e}")
            raise
