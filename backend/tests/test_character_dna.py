import pytest
from app.schemas.photo import VisionAnalysisOutput
from app.schemas.character import CharacterDNA
from app.ai import story_provider

@pytest.mark.asyncio
async def test_character_dna_generation():
    """Verify persistent Character DNA generation conforms to archetype and speech profile."""
    vision = VisionAnalysisOutput(
        subject="dog",
        category="animal",
        breed_or_type="indie",
        color="brown",
        environment="street",
        visible_objects=["collar", "road"],
        estimated_expression="curious",
        is_human_present=False
    )
    dna: CharacterDNA = await story_provider.generate_character_dna(vision, preferred_language="te-en")
    
    assert dna.name != ""
    assert dna.species_or_object == "dog"
    assert dna.secret != ""
    assert dna.fear != ""
    assert dna.comedy_archetype in [
        "confused_legend", "deadpan_savage", "overthinking_genius", "overconfident_hero",
        "victim_king", "silent_killer", "cunning_friend", "innocent_idiot", "mass_character",
        "old_school_uncle", "technical_fellow", "dark_deadpan"
    ]
    assert dna.speech_style.language == "te-en"
    assert dna.speech_style.slang == "naatu"
    assert dna.telugu_slang_level > 0.5
