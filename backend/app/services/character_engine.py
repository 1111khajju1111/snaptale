from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Character, Universe
from app.schemas.character import CharacterDNA, CharacterCreate
from app.schemas.photo import VisionAnalysisOutput
from app.ai import story_provider

async def create_or_persist_character(
    db: AsyncSession,
    user_id: str,
    vision: VisionAnalysisOutput,
    universe_id: Optional[str] = None,
    preferred_language: str = "te-en"
) -> Character:
    # Generate structured Character DNA via AI provider
    dna: CharacterDNA = await story_provider.generate_character_dna(
        vision=vision,
        preferred_language=preferred_language
    )

    character = Character(
        user_id=user_id,
        universe_id=universe_id,
        name=dna.name,
        species_or_object=dna.species_or_object,
        dna=dna.model_dump(),
        origin_story=dna.origin,
        story_count=0,
        chat_count=0
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return character
