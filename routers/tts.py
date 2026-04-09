import logging
from fastapi import APIRouter, Request, HTTPException, Response
from helpers.sarvam import synthesize_speech

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["tts"])

@router.post("/sarvam-tts")
async def handle_sarvam_tts(request: Request):
    """
    Ultravox generic externalVoice endpoint.
    Ultravox will send a JSON payload containing the text.
    We proxy the request to Sarvam and return audio bytes.
    """
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON from Ultravox TTS payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Ultravox TTS request payload varies but usually contains 'text'. Let's extract it.
    text = data.get("text", "")
    
    if not text:
        logger.warning(f"No text field found in incoming TTS request. Payload: {data}")
        return Response(content=b"", media_type="audio/wav")

    logger.info(f"Received text for Sarvam TTS: '{text}'")

    try:
        audio_bytes = await synthesize_speech(text)
        # Returning standard wav audio content stream
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        logger.error(f"Error serving audio from Sarvam: {e}")
        raise HTTPException(status_code=500, detail="TTS generation failed")
