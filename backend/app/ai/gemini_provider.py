import json
import base64
import logging
from typing import List, Dict, Optional, Any
from fastapi import HTTPException, status
from app.ai.base import (
    BaseVisionProvider, BaseStoryProvider, BaseImageProvider, BaseModerationProvider
)
from app.schemas.photo import HumanDetectionResult, VisionAnalysisOutput
from app.schemas.character import CharacterDNA, SpeechStyle
from app.schemas.story import StoryDiceRoll

logger = logging.getLogger(__name__)

# Current (Sep 2026) supported Gemini models. gemini-1.5-flash was fully shut
# down (404s on every request); gemini-2.5-flash-image is scheduled to shut
# down Oct 2, 2026, too close to a new deployment to build against.
TEXT_MODEL_NAME = "gemini-3.5-flash"       # general-purpose multimodal text/vision GA model
IMAGE_MODEL_NAME = "gemini-3.1-flash-image"  # "Nano Banana 2", GA image generation model


def _unavailable(detail: str) -> HTTPException:
    """Fail-closed 503. Every Gemini-backed provider in this file raises this on any
    failure (client not initialized, API error, malformed response) instead of ever
    falling back to mock/placeholder output. Mock output belongs only behind
    AI_PROVIDER=mock, selected explicitly in app/ai/__init__.py — never as a silent
    degradation path inside a "real" provider."""
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


def _init_client(api_key: str):
    """Shared google-genai client init. Returns None on failure; every caller must
    treat None as fail-closed (raise _unavailable), never as a cue to use mock data."""
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as e:
        logger.warning(f"Failed to initialize google-genai client: {e}")
        return None


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


def _safety_block_reason(response) -> Optional[str]:
    """Inspect Gemini's own safety ratings/finish reason on a response, independent
    of whatever the model said in its text output. Used so moderation doesn't rely
    solely on the model self-reporting via JSON."""
    feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(feedback, "block_reason", None)
    if block_reason:
        return f"Blocked by safety filter: {block_reason}"

    for candidate in (getattr(response, "candidates", None) or []):
        finish_reason = str(getattr(candidate, "finish_reason", ""))
        if finish_reason and finish_reason.upper() not in ("STOP", "1", "FINISH_REASON_STOP"):
            return f"Blocked by safety filter: {finish_reason}"
        for rating in (getattr(candidate, "safety_ratings", None) or []):
            probability = str(getattr(rating, "probability", "")).upper()
            if probability in ("HIGH", "MEDIUM"):
                category = getattr(rating, "category", "unknown_category")
                return f"Flagged for {category} ({probability} probability)"
    return None


class GeminiVisionProvider(BaseVisionProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = _init_client(api_key)

    async def detect_human(self, image_bytes: bytes, filename: str = "") -> HumanDetectionResult:
        if not self.client:
            raise _unavailable("Human detection service is unavailable. Photo cannot be safely verified.")

        try:
            from google.genai import types
            prompt = """
Analyze this image strictly for human presence.
Does this image contain ANY human being, person, face, selfie, portrait, body, child, or group of people?
Even if an animal or object is the main subject, if any human is visible anywhere, answer true.
Output ONLY JSON in this format:
{"is_human_present": true/false, "confidence": float, "detected_labels": ["list", "of", "labels"]}
"""
            response = await self.client.aio.models.generate_content(
                model=TEXT_MODEL_NAME,
                contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")]
            )
            data = _parse_json_response(response.text)
            return HumanDetectionResult(**data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gemini human detection error: {e}")
            # FAIL CLOSED: never fall back to filename/magic-byte mock detection here.
            raise _unavailable("Human detection service encountered an error and failed closed. Please try again.")

    async def analyze_non_human(self, image_bytes: bytes) -> VisionAnalysisOutput:
        if not self.client:
            raise _unavailable("Vision analysis service is unavailable.")

        try:
            from google.genai import types
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
            response = await self.client.aio.models.generate_content(
                model=TEXT_MODEL_NAME,
                contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")]
            )
            data = _parse_json_response(response.text)
            return VisionAnalysisOutput(**data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gemini vision analysis error: {e}")
            raise _unavailable("Vision analysis service unavailable.")


class GeminiStoryProvider(BaseStoryProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = _init_client(api_key)

    async def _generate_json(self, prompt: str) -> dict:
        if not self.client:
            raise _unavailable("Story generation service is unavailable.")
        try:
            response = await self.client.aio.models.generate_content(
                model=TEXT_MODEL_NAME,
                contents=prompt
            )
            return _parse_json_response(response.text)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gemini story generation error: {e}")
            # FAIL CLOSED: no mock-story fallback for a configured real provider.
            raise _unavailable("Story generation failed and will not fall back to placeholder content. Please try again.")

    async def generate_character_dna(self, vision: VisionAnalysisOutput, preferred_language: str = "te-en") -> CharacterDNA:
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
        data = await self._generate_json(prompt)
        return CharacterDNA(**data)

    async def generate_story(
        self,
        character_dna: CharacterDNA,
        dice: StoryDiceRoll,
        mode: str = "snaptale",
        language: str = "te-en",
        custom_prompt: Optional[str] = None
    ) -> Dict[str, str]:
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
{f"Additional custom direction: {custom_prompt}" if custom_prompt else ""}
Tone: Conversational Telugu-English ('naatu naatu maatalu' code switching).
Follow narrative structure: {structure}.

Return ONLY JSON:
{{
  "title": "Story Title",
  "content": "Full story formatted with structure headers",
  "punchline": "Memorable short punchline for story card"
}}
"""
        return await self._generate_json(prompt)

    async def mutate_story(
        self,
        original_story_content: str,
        character_dna: CharacterDNA,
        mutation_type: str,
        mode: str = "snaptale",
        language: str = "te-en",
        custom_instruction: Optional[str] = None
    ) -> Dict[str, str]:
        prompt = f"""
You are branching an existing SnapTale story into an alternate version without overwriting the original.
Character: {character_dna.name} ({character_dna.species_or_object}), archetype: {character_dna.comedy_archetype}.
Original story:
\"\"\"{original_story_content}\"\"\"

Mutation type: {mutation_type}
{f"Custom instruction: {custom_instruction}" if custom_instruction else ""}
Mode: {mode}. Keep the character's core personality intact but shift tone/genre to match the mutation type.

Return ONLY JSON:
{{"title": "New branch title", "content": "Full mutated story", "punchline": "Short punchline"}}
"""
        return await self._generate_json(prompt)

    async def what_if_story(
        self,
        original_story_content: str,
        character_dna: CharacterDNA,
        scenario: str,
        mode: str = "snaptale",
        language: str = "te-en"
    ) -> Dict[str, str]:
        prompt = f"""
Generate a "What If" alternate-reality branch for an existing SnapTale character.
Character: {character_dna.name} ({character_dna.species_or_object}), archetype: {character_dna.comedy_archetype}.
Original story:
\"\"\"{original_story_content}\"\"\"

What if scenario: "{scenario}"
Mode: {mode}.

Return ONLY JSON:
{{"title": "What If: ...", "content": "Full alternate-reality story", "punchline": "Short punchline"}}
"""
        return await self._generate_json(prompt)

    async def continue_story(
        self,
        previous_story_content: str,
        character_dna: CharacterDNA,
        direction: Optional[str] = None,
        mode: str = "snaptale",
        language: str = "te-en"
    ) -> Dict[str, str]:
        prompt = f"""
Continue this SnapTale story with the next chapter, without rewriting what came before.
Character: {character_dna.name} ({character_dna.species_or_object}), archetype: {character_dna.comedy_archetype}.
Previous chapter:
\"\"\"{previous_story_content}\"\"\"

{f"Requested direction: {direction}" if direction else "Continue the natural next beat of the story."}
Mode: {mode}.

Return ONLY JSON:
{{"title": "Next chapter title", "content": "Full next-chapter story", "punchline": "Short punchline"}}
"""
        return await self._generate_json(prompt)

    async def chat_response(
        self,
        character_dna: CharacterDNA,
        chat_history: List[Dict[str, str]],
        message: str,
        universe_context: Optional[str] = None,
        is_snapplus: bool = False
    ) -> str:
        if not self.client:
            raise _unavailable("Chat service is unavailable.")

        history_text = "\n".join(
            f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in (chat_history or [])
        )
        prompt = f"""
You are roleplaying in-character as {character_dna.name}, a {character_dna.species_or_object}.
Personality: {', '.join(character_dna.personality)}. Archetype: {character_dna.comedy_archetype}.
Secret: {character_dna.secret}. Occupation: {character_dna.occupation}.
Speak in conversational Telugu-English code-switching matching this character's established voice.
{f"Universe context: {universe_context}" if universe_context else ""}
Content mode: {"SnapTale+ (edgier, dark comedy allowed)" if is_snapplus else "SnapTale (general audience)"}.

Conversation so far:
{history_text}

User's new message: "{message}"

Respond with a single short, in-character reply. Plain text only, no JSON, no quotation marks around the whole reply.
"""
        try:
            response = await self.client.aio.models.generate_content(
                model=TEXT_MODEL_NAME,
                contents=prompt
            )
            block_reason = _safety_block_reason(response)
            if block_reason:
                raise _unavailable(f"Chat response was blocked by safety filters: {block_reason}")
            return response.text.strip()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gemini chat response error: {e}")
            raise _unavailable("Chat service failed and will not fall back to placeholder dialogue. Please try again.")


class GeminiImageProvider(BaseImageProvider):
    """Generates a real, story-unique image via Gemini's current image-generation
    model. Never returns a fixed/stock placeholder — on any failure this fails
    closed (503) rather than silently substituting mock/stock imagery."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = _init_client(api_key)

    async def generate_story_image(
        self,
        character_dna: CharacterDNA,
        story_title: str,
        scene_summary: str,
        mode: str = "snaptale"
    ) -> str:
        if not self.client:
            raise _unavailable("Image generation service is unavailable. Story cannot be illustrated right now.")

        try:
            from google.genai import types
            appearance = ", ".join(f"{k}: {v}" for k, v in (character_dna.appearance or {}).items())
            tone = (
                "moody, cinematic, slightly dark comedic thriller lighting"
                if mode == "snapplus" else
                "bright, playful, meme-style comedic illustration"
            )
            prompt = f"""
Create a single vivid illustration for a short-form comedic story app.
Subject: {character_dna.name}, a {character_dna.species_or_object} character with personality traits {', '.join(character_dna.personality)}.
Visual appearance details: {appearance or 'as photographed'}.
Scene: {scene_summary}. Story title: "{story_title}".
Style: {tone}. No text or lettering rendered in the image. No real, identifiable human beings.
"""
            response = await self.client.aio.models.generate_content(
                model=IMAGE_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"])
            )

            image_bytes = None
            mime_type = "image/png"
            for candidate in (getattr(response, "candidates", None) or []):
                parts = getattr(getattr(candidate, "content", None), "parts", None) or []
                for part in parts:
                    inline_data = getattr(part, "inline_data", None)
                    if inline_data and getattr(inline_data, "data", None):
                        image_bytes = inline_data.data
                        mime_type = getattr(inline_data, "mime_type", mime_type)
                        break
                if image_bytes:
                    break

            if not image_bytes:
                raise ValueError("Gemini response contained no image data")

            b64 = base64.b64encode(image_bytes).decode("utf-8")
            return f"data:{mime_type};base64,{b64}"
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gemini image generation error: {e}")
            raise _unavailable("Image generation failed and will not fall back to placeholder imagery. Please try again.")


class GeminiModerationProvider(BaseModerationProvider):
    """Real moderation backed by Gemini's safety ratings plus an explicit
    safety-review prompt, covering both generated text and generated image bytes.
    Fails closed: if the moderation call itself is unavailable, content is treated
    as unsafe rather than silently allowed through."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = _init_client(api_key)

    async def check_content_safety(self, text: str, is_snapplus: bool = False) -> Dict[str, Any]:
        if not self.client:
            raise _unavailable("Moderation service is unavailable. Content cannot be safely verified.")

        try:
            allowance = (
                "This app (SnapTale+) permits dark comedy, mild threat/thriller themes and edgy humor "
                "aimed at fictional non-human characters, but must still block genuinely harmful content."
                if is_snapplus else
                "This app (SnapTale) is general-audience comedic content and should apply a stricter, "
                "family-friendly bar."
            )
            prompt = f"""
You are a content safety reviewer for an entertainment app.
{allowance}
Review the following generated story text and determine if it contains any of:
sexual content involving minors, non-consensual sexual content, instructions for self-harm or suicide,
credible threats or incitement of real-world violence, hate speech targeting protected groups,
or any other severe policy violation.

Text to review:
\"\"\"{text}\"\"\"

Output ONLY JSON: {{"is_safe": true/false, "reason": "short explanation"}}
"""
            response = await self.client.aio.models.generate_content(model=TEXT_MODEL_NAME, contents=prompt)

            block_reason = _safety_block_reason(response)
            if block_reason:
                return {"is_safe": False, "reason": block_reason, "action": "block"}

            data = _parse_json_response(response.text)
            is_safe = bool(data.get("is_safe", False))
            return {
                "is_safe": is_safe,
                "reason": data.get("reason", "Reviewed by Gemini moderation"),
                "action": "allow" if is_safe else "block"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gemini content moderation error: {e}")
            # FAIL CLOSED: an unavailable/broken moderation call must never resolve to "safe".
            return {"is_safe": False, "reason": "Moderation service error; content blocked as a precaution.", "action": "block"}

    async def check_image_safety(self, image_bytes: bytes, is_snapplus: bool = False) -> Dict[str, Any]:
        if not self.client:
            # Cannot inspect the actual image bytes at all: fail closed, do not
            # fall back to moderating only a text description of the scene.
            return {"is_safe": False, "reason": "Image moderation service unavailable; cannot verify image.", "action": "block"}

        try:
            from google.genai import types
            prompt = """
Review this image for a comedic entertainment app. Check for:
sexual/explicit content, gore or graphic violence, hate symbolry, real identifiable human faces,
or any other severe policy violation.
Output ONLY JSON: {"is_safe": true/false, "reason": "short explanation"}
"""
            response = await self.client.aio.models.generate_content(
                model=TEXT_MODEL_NAME,
                contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/png")]
            )

            block_reason = _safety_block_reason(response)
            if block_reason:
                return {"is_safe": False, "reason": block_reason, "action": "block"}

            data = _parse_json_response(response.text)
            is_safe = bool(data.get("is_safe", False))
            return {
                "is_safe": is_safe,
                "reason": data.get("reason", "Reviewed by Gemini image moderation"),
                "action": "allow" if is_safe else "block"
            }
        except Exception as e:
            logger.error(f"Gemini image moderation error: {e}")
            # FAIL CLOSED here too: an inspection failure is not a pass.
            return {"is_safe": False, "reason": "Image moderation service error; content blocked as a precaution.", "action": "block"}
