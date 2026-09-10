import json
import logging
from typing import Optional
from fastapi import BackgroundTasks
from app.core.config import settings
from app.workers.job_worker import process_generation_job
from app.schemas.story import StoryDiceRoll

logger = logging.getLogger(__name__)

async def enqueue_generation_job(
    background_tasks: BackgroundTasks,
    job_id: str,
    user_id: str,
    image_bytes: Optional[bytes] = None,
    filename: str = "",
    character_id: Optional[str] = None,
    experience_mode: str = "snaptale",
    language: str = "te-en",
    dice: Optional[StoryDiceRoll] = None,
    custom_prompt: Optional[str] = None
) -> str:
    redis_enqueued = False
    if settings.REDIS_URL:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5)
            await r.ping()
            job_payload = {
                "job_id": job_id,
                "user_id": user_id,
                "character_id": character_id,
                "experience_mode": experience_mode,
                "language": language,
                "custom_prompt": custom_prompt,
                "filename": filename
            }
            await r.rpush("snaptale:jobs:generation", json.dumps(job_payload))
            await r.aclose()
            redis_enqueued = True
            logger.info(f"Job {job_id} successfully queued to Redis.")
        except Exception as e:
            logger.debug(f"Redis queue unavailable, falling back to background worker: {e}")
            redis_enqueued = False

    if not redis_enqueued:
        background_tasks.add_task(
            process_generation_job,
            job_id=job_id,
            user_id=user_id,
            image_bytes=image_bytes,
            filename=filename,
            character_id=character_id,
            experience_mode=experience_mode,
            language=language,
            dice=dice,
            custom_prompt=custom_prompt
        )

    return job_id
