from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from fastapi import HTTPException, status
from app.models.models import PinnedItem, Character, Story, Chat, Universe, StoryBranch
from app.core.config import settings

async def verify_item_ownership(db: AsyncSession, user_id: str, item_type: str, item_id: str):
    """Ensure user owns the resource before allowing it to be pinned."""
    if item_type == "character":
        res = await db.execute(select(Character).where(Character.id == item_id, Character.user_id == user_id))
        if not res.scalars().first():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot pin an unowned character.")
    elif item_type == "story":
        res = await db.execute(select(Story).where(Story.id == item_id, Story.user_id == user_id))
        if not res.scalars().first():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot pin an unowned story.")
    elif item_type == "chat":
        res = await db.execute(select(Chat).where(Chat.id == item_id, Chat.user_id == user_id))
        if not res.scalars().first():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot pin an unowned chat.")
    elif item_type == "universe":
        res = await db.execute(select(Universe).where(Universe.id == item_id, Universe.user_id == user_id))
        if not res.scalars().first():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot pin an unowned universe.")
    elif item_type == "mutation":
        # Mutation is a story branch, verify branch ownership
        res = await db.execute(
            select(StoryBranch).where(
                or_(StoryBranch.id == item_id, StoryBranch.child_story_id == item_id),
                StoryBranch.created_by == user_id
            )
        )
        if not res.scalars().first():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot pin an unowned mutation.")

async def pin_item(db: AsyncSession, user_id: str, item_type: str, item_id: str) -> PinnedItem:
    valid_types = ["character", "story", "chat", "universe", "mutation"]
    if item_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid item_type. Allowed: {valid_types}")

    # Check resource ownership first
    await verify_item_ownership(db, user_id, item_type, item_id)

    # Check category count limit (max 10 pinned per category)
    count_res = await db.execute(
        select(func.count(PinnedItem.id)).where(
            and_(PinnedItem.user_id == user_id, PinnedItem.item_type == item_type)
        )
    )
    current_count = count_res.scalar() or 0
    if current_count >= settings.MAX_PINNED_PER_CATEGORY:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pin more than {settings.MAX_PINNED_PER_CATEGORY} items in category '{item_type}'."
        )

    # Check if already pinned
    existing = await db.execute(
        select(PinnedItem).where(
            and_(PinnedItem.user_id == user_id, PinnedItem.item_type == item_type, PinnedItem.item_id == item_id)
        )
    )
    if existing.scalars().first():
        return existing.scalars().first()

    item = PinnedItem(
        user_id=user_id,
        item_type=item_type,
        item_id=item_id
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

async def unpin_item(db: AsyncSession, user_id: str, item_id: str) -> bool:
    res = await db.execute(
        select(PinnedItem).where(
            PinnedItem.user_id == user_id,
            or_(PinnedItem.id == item_id, PinnedItem.item_id == item_id)
        )
    )
    item = res.scalars().first()
    if item:
        await db.delete(item)
        await db.commit()
    return True