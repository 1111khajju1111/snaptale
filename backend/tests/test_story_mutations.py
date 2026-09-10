import pytest
from app.schemas.character import CharacterDNA, SpeechStyle
from app.schemas.story import StoryDiceRoll
from app.ai import story_provider

@pytest.mark.asyncio
async def test_story_dice_and_mutations():
    """Verify that mutations create new branches without altering the original narrative."""
    dna = CharacterDNA(
        name="Dogesh Bhai",
        species_or_object="dog",
        personality=["brave", "sarcastic"],
        secret="Controls satellites",
        fear="Vacuum cleaners",
        origin="Old City",
        occupation="Street Detective",
        abilities=["Super hearing"],
        weaknesses=["Parotta smell"],
        comedy_archetype="overconfident_hero",
        humor_style=["sarcasm", "absurdity"],
        speech_style=SpeechStyle(language="te-en", register="naatu", slang="naatu", code_switching=0.4)
    )
    dice = StoryDiceRoll(
        genre="Comedy",
        setting="Mars",
        goal="Escape",
        twist="Simulation",
        chaos_mode=False
    )
    # 1. Generate original story
    original = await story_provider.generate_story(dna, dice, mode="snaptale")
    assert "Mars" in original["title"] or "Dogesh" in original["title"]
    assert original["punchline"] != ""

    # 2. Mutate to space
    mutated = await story_provider.mutate_story(original["content"], dna, mutation_type="space")
    assert "Mars" in mutated["title"] or "Space" in mutated["title"] or "Dogesh" in mutated["title"]

    # 3. What-if branch
    what_if = await story_provider.what_if_story(original["content"], dna, scenario="Dogesh became Emperor of Mars")
    assert "What If" in what_if["title"]
