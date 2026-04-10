import os
import httpx
import logging
import base64

logger = logging.getLogger(__name__)

SARVAM_BASE_URL = "https://api.sarvam.ai/text-to-speech"


def _detect_language(text: str) -> tuple[str, str]:
    """
    Detect language from Unicode script and return (language_code, speaker).
    Returns Indian English as default for unrecognised scripts.
    """
    for char in text:
        cp = ord(char)
        if 0x0C00 <= cp <= 0x0C7F:   # Telugu
            return "te-IN", "pavithra"
        if 0x0900 <= cp <= 0x097F:   # Hindi / Devanagari
            return "hi-IN", "meera"
        if 0x0B80 <= cp <= 0x0BFF:   # Tamil
            return "ta-IN", "meera"
        if 0x0C80 <= cp <= 0x0CFF:   # Kannada
            return "kn-IN", "meera"
        if 0x0A00 <= cp <= 0x0A7F:   # Punjabi / Gurmukhi
            return "pa-IN", "meera"
        if 0x0A80 <= cp <= 0x0AFF:   # Gujarati
            return "gu-IN", "meera"
        if 0x0B00 <= cp <= 0x0B7F:   # Odia
            return "or-IN", "meera"
        if 0x0980 <= cp <= 0x09FF:   # Bengali
            return "bn-IN", "meera"
    # Default: Indian English — Rahul (male, natural Indian accent)
    return "en-IN", "rahul"


async def synthesize_speech(text: str) -> bytes:
    """
    Calls Sarvam AI Text-to-Speech API to convert text to audio.
    Auto-detects language (Telugu, Hindi, English, etc.) from the script.
    Returns decoded raw audio bytes (WAV).
    """
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        logger.error("SARVAM_API_KEY is not set in environment.")
        raise ValueError("SARVAM_API_KEY is missing")

    lang_code, speaker = _detect_language(text)
    logger.info(f"Sarvam TTS: lang={lang_code} speaker={speaker} text='{text[:60]}'")

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": [text],
        "target_language_code": lang_code,
        "speaker": speaker,
        "pitch": 0,
        "pace": 1.05,          # Slightly faster = more natural conversation pace
        "loudness": 1.5,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True,
        "model": "bulbul:v1",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                SARVAM_BASE_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            audios = data.get("audios", [])
            if not audios:
                logger.error(f"No audio returned from Sarvam. Payload: {payload}")
                return b""

            return base64.b64decode(audios[0])

        except Exception as e:
            logger.error(f"Sarvam TTS failed: {e}")
            raise
