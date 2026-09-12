import asyncio
from datetime import datetime, timezone
from typing import Dict, Set, Optional
from fastapi import WebSocket, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import GenerationJob, Story, Character
from app.schemas.character import CharacterDNA
from app.schemas.photo import VisionAnalysisOutput
from app.schemas.story import StoryDiceRoll
import app.core.database as db_module
from app.services.character_engine import create_or_persist_character
from app.services.human_detection import validate_and_detect_human
from app.services.story_dice import roll_story_dice
from app.services.image_safety import is_generated_image_safe
from app.ai import story_provider, image_provider, moderation_provider

class JobConnectionManager:
    """Manages active WebSockets for real-time generation progress."""
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)

    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    async def broadcast_progress(self, job_id: str, payload: dict):
        if job_id in self.active_connections:
            for ws in list(self.active_connections[job_id]):
                try:
                    await ws.send_json(payload)
                except Exception:
                    self.disconnect(job_id, ws)

job_connection_manager = JobConnectionManager()

STAGE_MESSAGES = {
    "vision": "👁️ Looking around and analyzing the non-human subject...",
    "input_moderation": "🛡️ Verifying prompt and safety boundaries...",
    "character": "🪄 Giving it a name, personality, and secret fear...",
    "story_dice": "🎲 Rolling the story dice for unpredictable drama...",
    "story": "📖 Writing its secret story with peak cinematic punchlines...",
    "output_moderation": "🔍 Moderating story content safety...",
    "image": "🎨 Bringing the character and scene to life with AI art...",
    "completed": "✨ Story generation complete!"
}

async def process_generation_job(
    job_id: str,
    user_id: str,
    image_bytes: Optional[bytes] = None,
    filename: str = "",
    character_id: Optional[str] = None,
    experience_mode: str = "snaptale",
    language: str = "te-en",
    dice: Optional[StoryDiceRoll] = None,
    custom_prompt: Optional[str] = None
):
    async with db_module.AsyncSessionLocal() as db:
        res = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
        job = res.scalars().first()
        if not job:
            return

        async def update_stage(stage: str, progress: int):
            job.stage = stage
            job.progress = progress
            job.status = "processing"
            await db.commit()
            payload = {
                "job_id": job_id,
                "status": "processing",
                "stage": stage,
                "progress": progress,
                "message": STAGE_MESSAGES.get(stage, "Processing..."),
                "story_id": job.story_id
            }
            await job_connection_manager.broadcast_progress(job_id, payload)

        try:
            job.started_at = datetime.now(timezone.utc)

            # 1. VISION & SERVER-SIDE HUMAN DETECTION
            await update_stage("vision", 15)
            target_char_id = character_id
            character_dna: Optional[CharacterDNA] = None

            if image_bytes:
                vision_analysis: VisionAnalysisOutput = await validate_and_detect_human(image_bytes, filename)
                
                # 2. INPUT MODERATION
                await update_stage("input_moderation", 25)
                if custom_prompt:
                    safety = await moderation_provider.check_content_safety(custom_prompt, is_snapplus=(experience_mode == "snapplus"))
                    if not safety.get("is_safe", True):
                        raise ValueError(f"Input rejected by moderation policy: {safety.get('reason')}")

                # 3. CHARACTER PERSISTENCE
                await update_stage("character", 40)
                character = await create_or_persist_character(
                    db=db,
                    user_id=user_id,
                    vision=vision_analysis,
                    preferred_language=language
                )
                target_char_id = character.id
                character_dna = CharacterDNA(**character.dna)
            elif target_char_id:
                char_res = await db.execute(select(Character).where(Character.id == target_char_id, Character.user_id == user_id))
                character = char_res.scalars().first()
                if not character:
                    raise ValueError("Character not found or access denied.")
                character_dna = CharacterDNA(**character.dna)
            else:
                raise ValueError("Either image or character_id must be provided.")

            # 4. STORY DICE
            await update_stage("story_dice", 50)
            active_dice = dice or roll_story_dice()

            # 5. STORY GENERATION
            await update_stage("story", 65)
            story_dict = await story_provider.generate_story(
                character_dna=character_dna,
                dice=active_dice,
                mode=experience_mode,
                language=language,
                custom_prompt=custom_prompt
            )

            # 6. OUTPUT MODERATION (Check story text before image generation)
            await update_stage("output_moderation", 75)
            out_safety = await moderation_provider.check_content_safety(
                story_dict["content"],
                is_snapplus=(experience_mode == "snapplus")
            )
            mod_status = "approved" if out_safety.get("is_safe", True) else "flagged"

            # 7. REAL IMAGE GENERATION (Actually invoke ImageProvider!)
            await update_stage("image", 85)
            generated_img_url = await image_provider.generate_story_image(
                character_dna=character_dna,
                story_title=story_dict["title"],
                scene_summary=active_dice.setting,
                mode=experience_mode
            )

            # 8. GENERATED IMAGE MODERATION (checks the actual generated image bytes,
            # not just a text description of the scene, whenever real bytes are
            # available; fails closed rather than degrading to text-only checks
            # under AI_PROVIDER=gemini)
            await update_stage("image_moderation", 92)
            image_is_safe = await is_generated_image_safe(
                generated_img_url, active_dice.setting, story_dict["title"],
                is_snapplus=(experience_mode == "snapplus")
            )
            if not image_is_safe:
                mod_status = "flagged"

            # 9. PERSIST STORY
            story = Story(
                user_id=user_id,
                character_id=target_char_id,
                title=story_dict["title"],
                content=story_dict["content"],
                punchline=story_dict.get("punchline"),
                experience_mode=experience_mode,
                language=language,
                dice_roll=active_dice.model_dump(),
                generated_image_url=generated_img_url,
                privacy="private",
                moderation_status=mod_status
            )
            db.add(story)
            await db.commit()
            await db.refresh(story)

            # 9. COMPLETE JOB
            job.status = "completed"
            job.stage = "completed"
            job.progress = 100
            job.story_id = story.id
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            final_payload = {
                "job_id": job_id,
                "status": "completed",
                "stage": "completed",
                "progress": 100,
                "message": STAGE_MESSAGES["completed"],
                "story_id": story.id,
                "generated_image_url": generated_img_url
            }
            await job_connection_manager.broadcast_progress(job_id, final_payload)

        except Exception as e:
            job.status = "failed"
            job.error_code = "GENERATION_ERROR"
            job.error_message = str(e)
            await db.commit()
            fail_payload = {
                "job_id": job_id,
                "status": "failed",
                "stage": "failed",
                "progress": job.progress,
                "message": f"Story generation failed: {str(e)}",
                "error_message": str(e)
            }
            await job_connection_manager.broadcast_progress(job_id, fail_payload)