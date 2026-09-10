from fastapi import APIRouter
from app.schemas.snapfacts import SnapFactsResponse
from app.services.snapfacts import get_snapfacts_for_subject

router = APIRouter(prefix="/snapfacts", tags=["snapfacts"])

@router.get("/{subject}", response_model=SnapFactsResponse)
async def get_subject_snapfacts(subject: str):
    return get_snapfacts_for_subject(subject)
