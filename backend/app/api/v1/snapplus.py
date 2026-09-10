from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user_id, create_snapplus_session_token
from app.models.models import Profile, SnapPlusChatSecurity
from app.schemas.snapplus import PinSetupRequest, PinVerifyRequest, PinChangeRequest, AgeGateRequest
from app.services.snapplus_service import setup_snapplus_pin, verify_snapplus_pin
from app.core.config import settings

router = APIRouter(prefix="/snapplus", tags=["snapplus"])

@router.post("/age-gate")
async def confirm_age_eligibility(
    payload: AgeGateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Self-declaration age gate for SnapTale+ mature mode.
    User explicitly confirms they meet the age requirement.
    """
    res = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = res.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    
    profile.is_snapplus_eligible = payload.confirmed_age_eligible
    profile.snapplus_enabled = payload.confirmed_age_eligible
    await db.commit()
    return {
        "is_snapplus_eligible": profile.is_snapplus_eligible,
        "snapplus_enabled": profile.snapplus_enabled,
        "declaration": "User confirmed they meet the age requirement for SnapTale+.",
        "message": "SnapTale+ mature mode activated." if profile.snapplus_enabled else "SnapTale+ disabled."
    }

@router.post("/pin/setup")
async def setup_pin(
    payload: PinSetupRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Set 4-digit private PIN for protected mature chats."""
    await setup_snapplus_pin(db, user_id, payload.pin)
    return {"message": "4-digit private chat PIN configured successfully."}

@router.post("/pin/verify")
async def verify_pin_endpoint(
    payload: PinVerifyRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify 4-digit PIN before unlocking private SnapTale+ chats.
    Returns a short-lived (15-minute) signed unlock session token on success.
    """
    is_valid = await verify_snapplus_pin(db, user_id, payload.pin)
    session_token = create_snapplus_session_token(user_id)
    return {
        "valid": is_valid,
        "session_token": session_token,
        "expires_in_minutes": settings.SNAPPLUS_SESSION_MINUTES,
        "message": "Access granted to protected chats."
    }

@router.put("/pin/change")
async def change_pin(
    payload: PinChangeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Verify current PIN first
    await verify_snapplus_pin(db, user_id, payload.current_pin)
    await setup_snapplus_pin(db, user_id, payload.new_pin)
    return {"message": "PIN updated successfully."}