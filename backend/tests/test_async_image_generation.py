import pytest
from sqlalchemy import select
from app.workers.job_worker import process_generation_job
from app.models.models import GenerationJob, Story, Character

@pytest.mark.asyncio
async def test_async_worker_executes_image_generation(db_session):
    """Verify that the async generation job explicitly calls ImageProvider and persists image URL."""
    user_id = "user-async-worker-test"

    # Create initial job
    job = GenerationJob(
        user_id=user_id,
        status="queued",
        stage="queued",
        progress=0
    )
    db_session.add(job)
    await db_session.commit()
    job_id = job.id

    # Run worker with non-human image
    await process_generation_job(
        job_id=job_id,
        user_id=user_id,
        image_bytes=b"NON_HUMAN_CHAI_CUP_BYTES",
        filename="chai_cup.jpg",
        experience_mode="snaptale",
        language="te-en"
    )

    # Use a fresh query in a clean session or refreshed state
    await db_session.refresh(job)

    assert job.status == "completed"
    assert job.stage == "completed"
    assert job.progress == 100
    assert job.story_id is not None

    # Verify Story has real image URL persisted
    story_res = await db_session.execute(select(Story).where(Story.id == job.story_id))
    story = story_res.scalars().first()

    assert story is not None
    assert story.generated_image_url is not None
    assert story.generated_image_url.startswith("http")
    assert story.moderation_status == "approved"