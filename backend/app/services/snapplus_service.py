from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.models import SnapPlusChatSecurity, Profile
from app.core.security import hash_pin, verify_pin
from app.core.config import settings

async def setup_snapplus_pin(db: AsyncSession, user_id: str, pin: str) -> bool:
    if not (pin.isdigit() and len(pin) == 4):
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 numeric digits.")
    
    result = await db.execute(select(SnapPlusChatSecurity).where(SnapPlusChatSecurity.user_id == user_id))
    existing = result.scalars().first()
    
    pin_hashed = hash_pin(pin)
    if existing:
        existing.pin_hash = pin_hashed
        existing.failed_attempts = 0
        existing.locked_until = None
    else:
        record = SnapPlusChatSecurity(
            user_id=user_id,
            pin_hash=pin_hashed,
            failed_attempts=0
        )
        db.add(record)
    
    await db.commit()
    return True

async def verify_snapplus_pin(db: AsyncSession, user_id: str, pin: str) -> bool:
    result = await db.execute(select(SnapPlusChatSecurity).where(SnapPlusChatSecurity.user_id == user_id))
    sec = result.scalars().first()
    if not sec:
        raise HTTPException(status_code=404, detail="SnapTale+ PIN has not been set up yet.")

    now = datetime.now(timezone.utc)
    # Check if locked out
    if sec.locked_until and sec.locked_until > now:
        remaining = int((sec.locked_until - now).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed PIN attempts. Locked out for {remaining} more minutes."
        )

    if verify_pin(pin, sec.pin_hash):
        sec.failed_attempts = 0
        sec.locked_until = None
        await db.commit()
        return True
    else:
        sec.failed_attempts += 1
        if sec.failed_attempts >= settings.PIN_MAX_ATTEMPTS:
            sec.locked_until = now + timedelta(minutes=settings.PIN_LOCKOUT_MINUTES)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"PIN attempts exceeded. Account locked for {settings.PIN_LOCKOUT_MINUTES} minutes."
            )
        await db.commit()
        attempts_left = settings.PIN_MAX_ATTEMPTS - sec.failed_attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid 4-digit PIN. {attempts_left} attempts remaining."
        )
