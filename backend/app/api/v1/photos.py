from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services.human_detection import validate_and_detect_human
from app.schemas.photo import VisionAnalysisOutput

router = APIRouter(prefix="/photos", tags=["photos"])

@router.post("/analyze", response_model=VisionAnalysisOutput)
async def analyze_photo(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Validates uploaded photo and performs strict server-side human detection.
    Rejects immediately if human is present; otherwise returns non-human visual metadata.
    """
    image_bytes = await file.read()
    analysis = await validate_and_detect_human(
        image_bytes=image_bytes,
        filename=file.filename or ""
    )
    return analysis
