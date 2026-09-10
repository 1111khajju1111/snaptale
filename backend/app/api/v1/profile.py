from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Profile, User

router = APIRouter(tags=["profile"])

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    preferred_language: Optional[str] = None

@router.get("/profile")
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = res.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return profile

@router.put("/profile")
async def update_profile(
    payload: ProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = res.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.preferred_language is not None:
        profile.preferred_language = payload.preferred_language
    await db.commit()
    await db.refresh(profile)
    return profile

@router.delete("/account")
async def delete_account(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Complete account and data deletion."""
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if user:
        await db.delete(user)
        await db.commit()
    return {"message": "Account and all associated characters, stories, and chats have been permanently deleted."}
