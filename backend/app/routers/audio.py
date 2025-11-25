from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.user import User
import logging
import traceback
import io

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/audio", tags=["audio"])
settings = get_settings()

SUPPORTED_AUDIO_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/mp4",
    "audio/aac",
    "video/webm",
}

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_content_type = (file.content_type or "").split(";")[0].strip()
    logger.info(f"Uploaded audio: filename={file.filename}, content_type={file.content_type}, base={base_content_type}")

    if base_content_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio content-type: {file.content_type}",
        )

    try:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty audio file")
        if len(data) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio file too large (max 20MB)")

        buffer = io.BytesIO(data)
        buffer.name = file.filename or "audio.webm"
        buffer.seek(0)

        model = settings.AUDIO_TRANSCRIBE_MODEL or "whisper-1"  # або "gpt-4o-mini-transcribe"

        transcript = await client.audio.transcriptions.create(
            model=model,
            file=buffer,
        )

        text = getattr(transcript, "text", "") if not isinstance(transcript, str) else transcript

        return {"text": text}

    except Exception as e:
        logger.error(
            "Audio transcription failed for user %s: %s: %s\n%s",
            getattr(current_user, "id", None),
            type(e).__name__,
            e,
            traceback.format_exc(),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Transcription error: {type(e).__name__}: {e}",
        )
