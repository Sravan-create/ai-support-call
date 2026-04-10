import os
import httpx
import logging
import base64

logger = logging.getLogger(__name__)

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

# ── Model ─────────────────────────────────────────────────────────────────────
# bulbul:v3 is the latest model (2024). "rahul" only exists in v3.
# v3 does NOT support pitch, loudness, or enable_preprocessing — those are v1/v2 only.
# v3 auto-enables preprocessing and handles code-mixed text natively.
MODEL = "bulbul:v3"

# ── Speaker map per language ──────────────────────────────────────────────────
# All speakers below are confirmed valid in bulbul:v3.
# "rahul" is a natural Indian English male voice (user's choice).
# For Indic languages, we pick voices that match the script.
_LANG_SPEAKER = {
    "en-IN": "rahul",      # Indian English male — user's preferred voice
    "te-IN": "kavitha",    # Telugu female
    "hi-IN": "ritu",       # Hindi female
    "ta-IN": "kavya",      # Tamil
    "kn-IN": "kavya",      # Kannada
    "ml-IN": "kavya",      # Malayalam
    "bn-IN": "priya",      # Bengali
    "gu-IN": "priya",      # Gujarati
    "pa-IN": "priya",      # Punjabi
    "or-IN": "priya",      # Odia
}


def _detect_language(text: str) -> str:
    """
    Detect primary language from Unicode script in the text.
    Returns BCP-47 language code for Sarvam target_language_code.
    Defaults to en-IN (Indian English) for Latin/unrecognised scripts.

    Note: Sarvam bulbul:v3 handles code-mixed text automatically —
    so even Tenglish (Telugu + English) works when te-IN is set.
    """
    for char in text:
        cp = ord(char)
        if 0x0C00 <= cp <= 0x0C7F:   # Telugu script
            return "te-IN"
        if 0x0900 <= cp <= 0x097F:   # Devanagari → Hindi/Marathi
            return "hi-IN"
        if 0x0B80 <= cp <= 0x0BFF:   # Tamil script
            return "ta-IN"
        if 0x0C80 <= cp <= 0x0CFF:   # Kannada script
            return "kn-IN"
        if 0x0D00 <= cp <= 0x0D7F:   # Malayalam script
            return "ml-IN"
        if 0x0980 <= cp <= 0x09FF:   # Bengali script
            return "bn-IN"
        if 0x0A80 <= cp <= 0x0AFF:   # Gujarati script
            return "gu-IN"
        if 0x0A00 <= cp <= 0x0A7F:   # Gurmukhi → Punjabi
            return "pa-IN"
    return "en-IN"


async def synthesize_speech(text: str) -> bytes:
    """
    Calls Sarvam AI TTS (bulbul:v3) to convert text to audio.

    - Auto-detects language from Unicode script (Telugu, Hindi, English, etc.)
    - Uses "rahul" for Indian English, language-appropriate speaker otherwise
    - bulbul:v3 handles code-mixed text (e.g. Tenglish) natively
    - Returns raw WAV bytes
    """
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not api_key:
        logger.error("SARVAM_API_KEY is not set.")
        raise ValueError("SARVAM_API_KEY is missing")

    lang_code = _detect_language(text)
    speaker   = _LANG_SPEAKER.get(lang_code, "rahul")

    logger.info(f"Sarvam TTS [{MODEL}] lang={lang_code} speaker={speaker} | '{text[:60]}'")

    # bulbul:v3 payload — NO pitch, loudness, or enable_preprocessing (v3 doesn't support them)
    payload = {
        "inputs":               [text],
        "target_language_code": lang_code,
        "speaker":              speaker,
        "model":                MODEL,
        "pace":                 1.1,       # 0.5–2.0 in v3; 1.1 = slightly faster, natural pace
        "speech_sample_rate":   22050,     # 22050 Hz — good quality, supported in v3
    }

    headers = {
        "api-subscription-key": api_key,
        "Content-Type":         "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(SARVAM_TTS_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            audios = data.get("audios", [])
            if not audios:
                logger.error(f"Sarvam returned no audio. Response: {data}")
                return b""

            return base64.b64decode(audios[0])

        except httpx.HTTPStatusError as e:
            logger.error(f"Sarvam TTS HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Sarvam TTS failed: {e}")
            raise
