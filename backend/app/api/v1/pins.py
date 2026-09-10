from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services.pin_service import pin_item, unpin_item

router = APIRouter(prefix="/pins", tags=["pins"])

class PinCreate(BaseModel):
    item_type: str # character, story, chat, universe, mutation
    item_id: str

@router.post("")
async def create_pin(
    payload: PinCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    pinned = await pin_item(db, user_id, payload.item_type, payload.item_id)
    return {"id": pinned.id, "item_type": pinned.item_type, "item_id": pinned.item_id, "message": "Pinned successfully"}

@router.delete("/{id}")
async def delete_pin(
    id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    await unpin_item(db, user_id, id)
    return {"message": "Unpinned successfully"}
