from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Character, Story, Chat
from app.schemas.character import CharacterCreate, CharacterResponse

router = APIRouter(prefix="/characters", tags=["characters"])

@router.post("", response_model=CharacterResponse)
async def create_character(
    payload: CharacterCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    character = Character(
        user_id=user_id,
        universe_id=payload.universe_id,
        name=payload.name,
        species_or_object=payload.species_or_object,
        dna=payload.dna.model_dump(),
        photo_url=payload.photo_url,
        origin_story=payload.origin_story or payload.dna.origin
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return character

@router.get("", response_model=List[CharacterResponse])
async def list_characters(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Character).where(Character.user_id == user_id).order_by(Character.last_activity_at.desc()))
    return res.scalars().all()

@router.get("/{id}", response_model=CharacterResponse)
async def get_character(
    id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Character).where(Character.id == id, Character.user_id == user_id))
    character = res.scalars().first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")
    return character

@router.delete("/{id}")
async def delete_character(
    id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Character).where(Character.id == id, Character.user_id == user_id))
    character = res.scalars().first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")
    await db.delete(character)
    await db.commit()
    return {"message": f"Character {id} deleted successfully."}
