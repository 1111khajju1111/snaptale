from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from typing import Optional
from app.core.security import (
    create_access_token, get_current_user_id, hash_password, verify_password
)
from app.models.models import User, Profile
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRequest(BaseModel):
    email: str
    password: Optional[str] = None
    username: Optional[str] = "guest"
    preferred_language: str = "te-en"

class AuthResponse(BaseModel):
    user_id: str
    email: str
    username: str
    access_token: str
    token_type: str = "bearer"
    preferred_language: str

@router.post("/register", response_model=AuthResponse)
async def register(payload: AuthRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == payload.email))
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    hashed_pwd = hash_password(payload.password) if payload.password else None
    user = User(email=payload.email, hashed_password=hashed_pwd)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    username = payload.username or "guest"
    profile = Profile(
        id=user.id,
        username=username,
        display_name=username.title(),
        preferred_language=payload.preferred_language
    )
    db.add(profile)
    await db.commit()

    token = create_access_token({"sub": user.id, "email": user.email})
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        username=profile.username,
        access_token=token,
        preferred_language=profile.preferred_language
    )

@router.post("/login", response_model=AuthResponse)
async def login(payload: AuthRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == payload.email))
    user = res.scalars().first()
    if not user:
        # Strict rejection: no auto-registration on unknown email in production
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # If user has a password, verify it strictly
    if user.hashed_password:
        if not payload.password or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

    prof_res = await db.execute(select(Profile).where(Profile.id == user.id))
    profile = prof_res.scalars().first()
    username = profile.username if profile else (payload.username or "guest")
    lang = profile.preferred_language if profile else payload.preferred_language

    token = create_access_token({"sub": user.id, "email": user.email})
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        username=username,
        access_token=token,
        preferred_language=lang
    )

@router.post("/supabase-sync", response_model=AuthResponse)
async def supabase_sync(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Syncs a Supabase authenticated user into PostgreSQL application database."""
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if not user:
        user = User(id=user_id, email=f"{user_id}@supabase.user")
        db.add(user)
        profile = Profile(
            id=user_id,
            username=f"user_{user_id[:8]}",
            display_name="SnapTale Creator",
            preferred_language="te-en"
        )
        db.add(profile)
        await db.commit()
    else:
        prof_res = await db.execute(select(Profile).where(Profile.id == user.id))
        profile = prof_res.scalars().first()

    token = create_access_token({"sub": user.id, "email": user.email})
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        username=profile.username if profile else "Creator",
        access_token=token,
        preferred_language=profile.preferred_language if profile else "te-en"
    )

@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully."}
