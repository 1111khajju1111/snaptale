from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.models import Story, StoryBranch, Character
from app.schemas.story import StoryDiceRoll, StoryCreate
from app.schemas.character import CharacterDNA
from app.ai import story_provider, image_provider, moderation_provider
from app.services.story_dice import roll_story_dice

async def generate_and_save_story(
    db: AsyncSession,
    user_id: str,
    character_id: str,
    dice: Optional[StoryDiceRoll] = None,
    experience_mode: str = "snaptale", # snaptale vs snapplus
    language: str = "te-en",
    parent_story_id: Optional[str] = None,
    custom_prompt: Optional[str] = None
) -> Story:
    # 1. Fetch character and verify ownership
    result = await db.execute(select(Character).where(Character.id == character_id, Character.user_id == user_id))
    character = result.scalars().first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found or access denied.")

    character_dna = CharacterDNA(**character.dna)
    active_dice = dice or roll_story_dice()

    # 2. Generate Story Content via AI Provider
    story_dict = await story_provider.generate_story(
        character_dna=character_dna,
        dice=active_dice,
        mode=experience_mode,
        language=language,
        custom_prompt=custom_prompt
    )

    # 3. Content safety moderation
    safety = await moderation_provider.check_content_safety(story_dict["content"], is_snapplus=(experience_mode == "snapplus"))
    mod_status = "approved" if safety.get("is_safe", True) else "flagged"

    # 4. Generate 1 Story Image via ImageProvider
    img_url = await image_provider.generate_story_image(
        character_dna=character_dna,
        story_title=story_dict["title"],
        scene_summary=active_dice.setting,
        mode=experience_mode
    )

    # 5. Persist Story
    story = Story(
        user_id=user_id,
        character_id=character.id,
        universe_id=character.universe_id,
        title=story_dict["title"],
        content=story_dict["content"],
        punchline=story_dict.get("punchline"),
        experience_mode=experience_mode,
        language=language,
        dice_roll=active_dice.model_dump(),
        generated_image_url=img_url,
        privacy="private", # Default privacy is private
        moderation_status=mod_status
    )
    db.add(story)
    
    # Increment character story count
    character.story_count += 1
    
    await db.commit()
    await db.refresh(story)

    # If linked to parent story, create branch link
    if parent_story_id:
        branch = StoryBranch(
            parent_story_id=parent_story_id,
            child_story_id=story.id,
            mutation_type="continuation",
            created_by=user_id
        )
        db.add(branch)
        await db.commit()

    return story

async def mutate_story_branch(
    db: AsyncSession,
    user_id: str,
    story_id: str,
    mutation_type: str,
    custom_instruction: Optional[str] = None
) -> Story:
    # 1. Fetch parent story and check ownership
    result = await db.execute(select(Story).where(Story.id == story_id, Story.user_id == user_id))
    parent_story = result.scalars().first()
    if not parent_story:
        raise HTTPException(status_code=404, detail="Original story not found.")

    char_result = await db.execute(select(Character).where(Character.id == parent_story.character_id))
    character = char_result.scalars().first()
    character_dna = CharacterDNA(**character.dna)

    # 2. Mutate story without overwriting parent
    mutated_dict = await story_provider.mutate_story(
        original_story_content=parent_story.content,
        character_dna=character_dna,
        mutation_type=mutation_type,
        mode=parent_story.experience_mode,
        language=parent_story.language,
        custom_instruction=custom_instruction
    )

    # 3. Generate image for the mutation
    img_url = await image_provider.generate_story_image(
        character_dna=character_dna,
        story_title=mutated_dict["title"],
        scene_summary=mutation_type,
        mode=parent_story.experience_mode
    )

    child_story = Story(
        user_id=user_id,
        character_id=character.id,
        universe_id=character.universe_id,
        title=mutated_dict["title"],
        content=mutated_dict["content"],
        punchline=mutated_dict.get("punchline"),
        experience_mode=parent_story.experience_mode,
        language=parent_story.language,
        dice_roll={"mutation": mutation_type},
        generated_image_url=img_url,
        privacy="private",
        moderation_status="approved"
    )
    db.add(child_story)
    await db.commit()
    await db.refresh(child_story)

    # Record lineage in story_branches
    branch = StoryBranch(
        parent_story_id=parent_story.id,
        child_story_id=child_story.id,
        mutation_type=mutation_type,
        mutation_prompt=custom_instruction,
        created_by=user_id
    )
    db.add(branch)
    await db.commit()

    return child_story
