from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.library import LibrarySearchResult
from app.services.library_service import search_library

router = APIRouter(prefix="/library", tags=["library"])

@router.get("/search", response_model=LibrarySearchResult)
async def search_library_endpoint(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    return await search_library(db, user_id, q, page, page_size)
