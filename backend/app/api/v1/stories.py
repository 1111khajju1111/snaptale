import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user_id, get_optional_user_id
from app.models.models import Story, StoryBranch, Character, GenerationJob, Like, Comment
from app.schemas.story import (
    StoryCreate, StoryResponse, StoryMutationRequest, WhatIfRequest, ContinueStoryRequest, LoreTreeNode
)
from app.schemas.job import GenerationJobResponse
from app.services.story_engine import generate_and_save_story, mutate_story_branch
from app.services.story_dice import roll_story_dice
from app.workers.job_worker import process_generation_job
from app.workers.queue import enqueue_generation_job
from app.ai import story_provider, image_provider

router = APIRouter(prefix="/stories", tags=["stories"])

@router.post("/generate", response_model=GenerationJobResponse)
async def generate_story_endpoint(
    background_tasks: BackgroundTasks,
    character_id: Optional[str] = Form(None),
    experience_mode: str = Form("snaptale"),
    language: str = Form("te-en"),
    custom_prompt: Optional[str] = Form(None),
    idempotency_key_form: Optional[str] = Form(None, alias="idempotency_key"),
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    file: Optional[UploadFile] = File(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Support Idempotency-Key header or form field
    active_idempotency_key = idempotency_key_header or idempotency_key_form

    if active_idempotency_key:
        res = await db.execute(select(GenerationJob).where(
            GenerationJob.user_id == user_id,
            GenerationJob.idempotency_key == active_idempotency_key
        ))
        existing_job = res.scalars().first()
        if existing_job:
            return GenerationJobResponse(
                job_id=existing_job.id,
                status=existing_job.status,
                stage=existing_job.stage,
                progress=existing_job.progress,
                story_id=existing_job.story_id,
                message="Returning existing job for idempotency key."
            )

    image_bytes = None
    filename = ""
    if file:
        image_bytes = await file.read()
        filename = file.filename or ""

    job = GenerationJob(
        user_id=user_id,
        status="queued",
        stage="queued",
        progress=5,
        idempotency_key=active_idempotency_key
    )
    db.add(job)
    try:
        await db.commit()
        await db.refresh(job)
    except Exception:
        await db.rollback()
        if active_idempotency_key:
            res = await db.execute(select(GenerationJob).where(
                GenerationJob.user_id == user_id,
                GenerationJob.idempotency_key == active_idempotency_key
            ))
            existing_job = res.scalars().first()
            if existing_job:
                return GenerationJobResponse(
                    job_id=existing_job.id,
                    status=existing_job.status,
                    stage=existing_job.stage,
                    progress=existing_job.progress,
                    story_id=existing_job.story_id,
                    message="Returning existing job for concurrent idempotency key."
                )
        raise

    await enqueue_generation_job(
        background_tasks=background_tasks,
        job_id=job.id,
        user_id=user_id,
        image_bytes=image_bytes,
        filename=filename,
        character_id=character_id,
        experience_mode=experience_mode,
        language=language,
        dice=roll_story_dice(),
        custom_prompt=custom_prompt
    )

    return GenerationJobResponse(
        job_id=job.id,
        status="queued",
        stage="queued",
        progress=5,
        story_id=None,
        message="Generation job scheduled successfully."
    )

@router.get("", response_model=List[StoryResponse])
async def list_stories(
    character_id: Optional[str] = None,
    mode: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    query = select(Story).where(Story.user_id == user_id)
    if character_id:
        query = query.where(Story.character_id == character_id)
    if mode:
        query = query.where(Story.experience_mode == mode)
    query = query.options(selectinload(Story.character)).order_by(Story.created_at.desc())
    res = await db.execute(query)
    stories = res.scalars().all()
    
    output = []
    for s in stories:
        resp = StoryResponse.model_validate(s)
        if s.character:
            resp.character_name = s.character.name
        output.append(resp)
    return output

@router.get("/{id}", response_model=StoryResponse)
async def get_story(
    id: str,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Story).options(selectinload(Story.character)).where(Story.id == id))
    story = res.scalars().first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")

    # Authorization rules:
    # 1. PRIVATE: strictly owner-only
    # 2. PUBLIC: accessible to anyone if approved
    # 3. UNLISTED: accessible to anyone with direct link
    if story.privacy == "private":
        if not user_id or story.user_id != user_id:
            raise HTTPException(status_code=404, detail="Story not found or access denied.")
    elif story.privacy == "public":
        if story.moderation_status != "approved" and (not user_id or story.user_id != user_id):
            raise HTTPException(status_code=403, detail="Story pending moderation.")

    resp = StoryResponse.model_validate(story)
    if story.character:
        resp.character_name = story.character.name
    return resp

@router.delete("/{id}")
async def delete_story(
    id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Story).where(Story.id == id, Story.user_id == user_id))
    story = res.scalars().first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")
    await db.delete(story)
    await db.commit()
    return {"message": "Story deleted successfully."}

@router.post("/{id}/mutate", response_model=StoryResponse)
async def mutate_story(
    id: str,
    payload: StoryMutationRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    child_story = await mutate_story_branch(
        db=db,
        user_id=user_id,
        story_id=id,
        mutation_type=payload.mutation_type,
        custom_instruction=payload.custom_instruction
    )
    resp = StoryResponse.model_validate(child_story)
    if child_story.character:
        resp.character_name = child_story.character.name
    return resp

@router.post("/{id}/what-if", response_model=StoryResponse)
async def what_if_story_endpoint(
    id: str,
    payload: WhatIfRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    child_story = await mutate_story_branch(
        db=db,
        user_id=user_id,
        story_id=id,
        mutation_type="what_if",
        custom_instruction=payload.scenario
    )
    resp = StoryResponse.model_validate(child_story)
    if child_story.character:
        resp.character_name = child_story.character.name
    return resp

@router.post("/{id}/continue", response_model=StoryResponse)
async def continue_story_endpoint(
    id: str,
    payload: ContinueStoryRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    child_story = await mutate_story_branch(
        db=db,
        user_id=user_id,
        story_id=id,
        mutation_type="chapter",
        custom_instruction=payload.direction
    )
    resp = StoryResponse.model_validate(child_story)
    if child_story.character:
        resp.character_name = child_story.character.name
    return resp

@router.get("/{id}/lore-tree", response_model=List[LoreTreeNode])
async def get_lore_tree(
    id: str,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Fetch root story (eager-load .character since it's read below via
    # current_story.character.name — accessing it lazily outside this
    # request's async session would raise MissingGreenlet)
    res = await db.execute(
        select(Story).options(selectinload(Story.character)).where(Story.id == id)
    )
    current_story = res.scalars().first()
    if not current_story:
        raise HTTPException(status_code=404, detail="Story not found.")

    if current_story.privacy == "private" and (not user_id or current_story.user_id != user_id):
        raise HTTPException(status_code=404, detail="Story not found or access denied.")

    # Filter stories for this character: owned by current user OR public
    if user_id:
        story_filter = or_(Story.user_id == user_id, Story.privacy == "public")
    else:
        story_filter = (Story.privacy == "public")

    all_res = await db.execute(
        select(Story).where(
            and_(Story.character_id == current_story.character_id, story_filter)
        )
    )
    char_stories = all_res.scalars().all()
    accessible_story_ids = {s.id for s in char_stories}
    char_name = current_story.character.name if current_story.character else "Hero"

    # STRICT DEEP ISOLATION: Fetch branch edges connecting accessible stories
    branch_conditions = [
        and_(
            StoryBranch.parent_story_id.in_(accessible_story_ids),
            StoryBranch.child_story_id.in_(accessible_story_ids)
        )
    ]
    if user_id:
        branch_conditions.append(StoryBranch.created_by == user_id)

    branch_res = await db.execute(select(StoryBranch).where(or_(*branch_conditions)))
    branches = branch_res.scalars().all()

    child_to_parent = {
        b.child_story_id: b.parent_story_id 
        for b in branches if b.child_story_id in accessible_story_ids
    }
    mutation_types = {
        b.child_story_id: b.mutation_type 
        for b in branches if b.child_story_id in accessible_story_ids
    }
    parent_to_children = {}
    for b in branches:
        if b.parent_story_id in accessible_story_ids and b.child_story_id in accessible_story_ids:
            parent_to_children.setdefault(b.parent_story_id, []).append(b.child_story_id)

    nodes = []
    for s in char_stories:
        nodes.append(LoreTreeNode(
            id=s.id,
            title=s.title,
            character_name=char_name,
            mutation_type=mutation_types.get(s.id),
            created_at=s.created_at,
            parent_id=child_to_parent.get(s.id),
            children_ids=parent_to_children.get(s.id, [])
        ))
    return nodes

@router.post("/{id}/publish")
async def publish_story(
    id: str,
    privacy: str = "public",
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Story).where(Story.id == id, Story.user_id == user_id))
    story = res.scalars().first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")
    story.privacy = privacy
    await db.commit()
    return {"message": f"Story updated to {privacy}.", "privacy": privacy}

@router.post("/{id}/like")
async def toggle_like_story(
    id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Story).where(Story.id == id))
    story = res.scalars().first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")
    
    like_res = await db.execute(select(Like).where(Like.user_id == user_id, Like.story_id == id))
    existing_like = like_res.scalars().first()
    if existing_like:
        await db.delete(existing_like)
        story.like_count = max(0, story.like_count - 1)
        liked = False
    else:
        db.add(Like(user_id=user_id, story_id=id))
        story.like_count += 1
        liked = True
    await db.commit()
    return {"liked": liked, "like_count": story.like_count}