import os
import json
import logging
from typing import List, Dict, Optional, Any
from fastapi import HTTPException, status
from app.ai.base import (
    BaseVisionProvider, BaseStoryProvider, BaseImageProvider, BaseModerationProvider
)
from app.schemas.photo import HumanDetectionResult, VisionAnalysisOutput
from app.schemas.character import CharacterDNA, SpeechStyle
from app.schemas.story import StoryDiceRoll
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiVisionProvider(BaseVisionProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        except Exception as e:
            logger.warning(f"Failed to initialize google.generativeai: {e}")
            self.model = None

    async def detect_human(self, image_bytes: bytes, filename: str = "") -> HumanDetectionResult:
        if not self.model:
            if settings.AI_PROVIDER == "gemini" or settings.APP_ENV == "production":
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Human detection service is unavailable. Photo cannot be safely verified."
                )
            from app.ai.mock_provider import MockVisionProvider
            return await MockVisionProvider().detect_human(image_bytes, filename)

        try:
            prompt = """
Analyze this image strictly for human presence.
Does this image contain ANY human being, person, face, selfie, portrait, body, child, or group of people?
Even if an animal or object is the main subject, if any human is visible anywhere, answer true.
Output ONLY JSON in this format:
{"is_human_present": true/false, "confidence": float, "detected_labels": ["list", "of", "labels"]}
"""
            response = self.model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_bytes}])
            clean_text = response.text.strip().strip("```json").strip("```")
            data = json.loads(clean_text)
            return HumanDetectionResult(**data)
        except Exception as e:
            logger.error(f"Gemini human detection error: {e}")
            # FAIL CLOSED: Never fall back to a permissive mock when real detection fails
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Human detection service encountered an error and failed closed. Please try again."
            )

    async def analyze_non_human(self, image_bytes: bytes) -> VisionAnalysisOutput:
        if not self.model:
            from app.ai.mock_provider import MockVisionProvider
            return await MockVisionProvider().analyze_non_human(image_bytes)

        try:
            prompt = """
Analyze this NON-HUMAN image. Identify:
1. Primary non-human subject (e.g. dog, cat, tea glass, chair, vintage car)
2. Category (animal, object, vehicle, food, plant, toy, building, gadget)
3. Breed or type
4. Dominant color
5. Surrounding environment
6. Visible objects in frame
7. Estimated expression or mood
Output ONLY JSON in this format:
{
  "subject": "string",
  "category": "string",
  "breed_or_type": "string",
  "color": "string",
  "environment": "string",
  "visible_objects": ["string"],
  "estimated_expression": "string",
  "is_human_present": false
}
"""
            response = self.model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_bytes}])
            clean_text = response.text.strip().strip("```json").strip("```")
            data = json.loads(clean_text)
            return VisionAnalysisOutput(**data)
        except Exception as e:
            logger.error(f"Gemini vision analysis error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vision analysis service unavailable."
            )

class GeminiStoryProvider(BaseStoryProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        except Exception as e:
            logger.warning(f"Failed to initialize google.generativeai: {e}")
            self.model = None

    async def generate_character_dna(self, vision: VisionAnalysisOutput, preferred_language: str = "te-en") -> CharacterDNA:
        from app.ai.mock_provider import MockStoryProvider
        if not self.model:
            return await MockStoryProvider().generate_character_dna(vision, preferred_language)
        try:
            prompt = f"""
Create a persistent Character DNA for an entertainment app called SnapTale.
Non-human visual subject: {vision.subject} ({vision.category}, {vision.breed_or_type}, color: {vision.color}, environment: {vision.environment}, expression: {vision.estimated_expression}).
Preferred language style: {preferred_language} (Support natural conversational Telugu-English 'naatu naatu maatalu' code-switching).
DO NOT imitate living actors or comedians. Select one original archetype:
[confused_legend, deadpan_savage, overthinking_genius, overconfident_hero, victim_king, silent_killer, cunning_friend, innocent_idiot, mass_character, old_school_uncle, technical_fellow, dark_deadpan].

Return ONLY JSON adhering to CharacterDNA:
{{
  "name": "Creative Name",
  "species_or_object": "{vision.subject}",
  "personality": ["trait1", "trait2", "trait3"],
  "secret": "funny or absurd secret",
  "fear": "humorous fear",
  "origin": "origin lore",
  "occupation": "fictional occupation",
  "abilities": ["ability 1", "ability 2"],
  "weaknesses": ["weakness 1"],
  "appearance": {{"color": "{vision.color}", "details": "visual details"}},
  "comedy_archetype": "overconfident_hero",
  "humor_style": ["sarcasm", "absurdity"],
  "speech_style": {{"language": "{preferred_language}", "register": "naatu", "slang": "naatu", "code_switching": 0.4}},
  "sarcasm_level": 0.85,
  "meme_level": 0.8,
  "dramatic_level": 0.9,
  "telugu_slang_level": 0.75,
  "english_mix": 0.35,
  "punchline_frequency": 0.85
}}
"""
            response = self.model.generate_content(prompt)
            clean_text = response.text.strip().strip("```json").strip("```")
            data = json.loads(clean_text)
            return CharacterDNA(**data)
        except Exception as e:
            logger.error(f"Gemini generate_character_dna error: {e}")
            return await MockStoryProvider().generate_character_dna(vision, preferred_language)

    async def generate_story(
        self,
        character_dna: CharacterDNA,
        dice: StoryDiceRoll,
        mode: str = "snaptale",
        language: str = "te-en",
        custom_prompt: Optional[str] = None
    ) -> Dict[str, str]:
        from app.ai.mock_provider import MockStoryProvider
        if not self.model:
            return await MockStoryProvider().generate_story(character_dna, dice, mode, language, custom_prompt)
        try:
            is_mature = (mode == "snapplus")
            structure = (
                "SETUP -> MISDIRECTION -> ESCALATION -> PUNCHLINE -> REACTION -> WHISTLE MOMENT"
                if is_mature else
                "SETUP -> CHARACTER -> PROBLEM -> CONFLICT -> TWIST -> CLIMAX -> ENDING"
            )
            prompt = f"""
You are the master entertainment writer for SnapTale.
Character: {character_dna.name} ({character_dna.species_or_object})
Archetype: {character_dna.comedy_archetype}
Mode: {mode} (SnapTale+ is mature/dark comedy/thriller; SnapTale is general humor/meme/absurdity)
Setting: {dice.setting}, Goal: {dice.goal}, Twist: {dice.twist}, Chaos Mode: {dice.chaos_mode}
Tone: Conversational Telugu-English ('naatu naatu maatalu' code switching like 'Bro literally cooked himself', 'ఏంట్రా ఇది 💀', 'Situation full ga out of control ayipoyindi ra!').
Follow narrative structure: {structure}.

Return ONLY JSON:
{{
  "title": "Story Title",
  "content": "Full story formatted with structure headers",
  "punchline": "Memorable short punchline for story card"
}}
"""
            response = self.model.generate_content(prompt)
            clean_text = response.text.strip().strip("```json").strip("```")
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"Gemini generate_story error: {e}")
            return await MockStoryProvider().generate_story(character_dna, dice, mode, language, custom_prompt)

    async def mutate_story(self, original_story_content: str, character_dna: CharacterDNA, mutation_type: str, mode: str = "snaptale", language: str = "te-en", custom_instruction: Optional[str] = None) -> Dict[str, str]:
        from app.ai.mock_provider import MockStoryProvider
        return await MockStoryProvider().mutate_story(original_story_content, character_dna, mutation_type, mode, language, custom_instruction)

    async def what_if_story(self, original_story_content: str, character_dna: CharacterDNA, scenario: str, mode: str = "snaptale", language: str = "te-en") -> Dict[str, str]:
        from app.ai.mock_provider import MockStoryProvider
        return await MockStoryProvider().what_if_story(original_story_content, character_dna, scenario, mode, language)

    async def continue_story(self, previous_story_content: str, character_dna: CharacterDNA, direction: Optional[str] = None, mode: str = "snaptale", language: str = "te-en") -> Dict[str, str]:
        from app.ai.mock_provider import MockStoryProvider
        return await MockStoryProvider().continue_story(previous_story_content, character_dna, direction, mode, language)

    async def chat_response(self, character_dna: CharacterDNA, chat_history: List[Dict[str, str]], message: str, universe_context: Optional[str] = None, is_snapplus: bool = False) -> str:
        from app.ai.mock_provider import MockStoryProvider
        return await MockStoryProvider().chat_response(character_dna, chat_history, message, universe_context, is_snapplus)