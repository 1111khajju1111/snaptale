from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import GenerationJob
from app.schemas.job import GenerationJobResponse

router = APIRouter(prefix="/generation-jobs", tags=["jobs"])

@router.get("/{id}", response_model=GenerationJobResponse)
async def get_generation_job(
    id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(GenerationJob).where(
        GenerationJob.id == id,
        GenerationJob.user_id == user_id
    ))
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found.")
    return GenerationJobResponse(
        job_id=job.id,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        story_id=job.story_id,
        error_code=job.error_code,
        error_message=job.error_message
    )
