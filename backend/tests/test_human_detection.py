import pytest
from app.services.human_detection import validate_and_detect_human, REJECTION_MESSAGE, REJECTION_BUTTON
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_human_rejection_pipeline():
    """Verify that any image containing humans/selfies is strictly rejected server-side."""
    human_image_bytes = b"TEST_HUMAN_IMAGE_DATA_123"
    
    with pytest.raises(HTTPException) as exc_info:
        await validate_and_detect_human(human_image_bytes, filename="selfie_with_dog.jpg")
    
    assert exc_info.value.status_code == 422
    data = exc_info.value.detail
    assert data["status"] == "rejected"
    assert data["reason"] == "human_detected"
    assert data["message"] == REJECTION_MESSAGE
    assert data["action_button"] == REJECTION_BUTTON

@pytest.mark.asyncio
async def test_non_human_acceptance_pipeline():
    """Verify that non-human photos (dog, chair, food, etc.) are accepted and analyzed."""
    non_human_bytes = b"GENUINE_DOG_PHOTO_BYTES"
    analysis = await validate_and_detect_human(non_human_bytes, filename="street_dog.jpg")
    
    assert analysis.is_human_present is False
    assert analysis.subject != ""
    assert len(analysis.visible_objects) > 0
