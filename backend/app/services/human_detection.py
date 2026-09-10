import os
from typing import Tuple
from fastapi import HTTPException, status
from app.ai import vision_provider
from app.schemas.photo import HumanDetectionResult, VisionAnalysisOutput

REJECTION_MESSAGE = "🚫 SnapTale can't use photos containing people. Try photographing an animal, object, vehicle, food, or anything else!"
REJECTION_BUTTON = "📸 Try Again"

async def validate_and_detect_human(image_bytes: bytes, filename: str = "", temp_file_path: str = None) -> VisionAnalysisOutput:
    """
    Strict server-side human detection pipeline:
    1. Size and file check.
    2. Vision provider human detection.
    3. If human: immediately unlink temp file, abort pipeline with HTTP 422, zero DB writes.
    4. If non-human: return vision analysis.
    """
    if len(image_bytes) > 15 * 1024 * 1024:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image size exceeds 15MB limit."
        )

    try:
        # Server-side human detection
        detection: HumanDetectionResult = await vision_provider.detect_human(image_bytes, filename)
    except HTTPException:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
        raise
    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Human detection service is temporarily unavailable. Photo cannot be safely verified. Please try again."
        )

    if detection.is_human_present:
        # Immediate cleanup of temporary files
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

        # Reject immediately
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "status": "rejected",
                "reason": "human_detected",
                "message": REJECTION_MESSAGE,
                "action_button": REJECTION_BUTTON,
                "confidence": detection.confidence,
                "labels": detection.detected_labels
            }
        )

    # Non-human confirmed: extract safe visual attributes
    analysis: VisionAnalysisOutput = await vision_provider.analyze_non_human(image_bytes)
    return analysis
