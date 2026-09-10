from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.core.database import get_db
from app.models.models import Story
from app.schemas.story import StoryResponse

router = APIRouter(prefix="/explore", tags=["explore"])

@router.get("", response_model=List[StoryResponse])
async def get_explore_feed(
    sort: str = "trending", # trending, funniest, horror, chaos, mutations, new
    db: AsyncSession = Depends(get_db)
):
    # Retrieve public, moderated stories
    query = select(Story).options(selectinload(Story.character)).where(Story.privacy == "public", Story.moderation_status == "approved")
    if sort == "trending":
        query = query.order_by(Story.like_count.desc())
    else:
        query = query.order_by(Story.created_at.desc())
        
    res = await db.execute(query.limit(30))
    stories = res.scalars().all()
    output = []
    for s in stories:
        resp = StoryResponse.model_validate(s)
        if s.character:
            resp.character_name = s.character.name
        output.append(resp)
    return output
