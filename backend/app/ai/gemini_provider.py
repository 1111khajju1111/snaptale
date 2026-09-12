import asyncio
import base64
import json
import logging
import os
from typing import List, Dict, Optional, Any, Callable, Awaitable

from fastapi import HTTPException, status

from app.ai.base import (
    BaseVisionProvider,
    BaseStoryProvider,
    BaseImageProvider,
    BaseModerationProvider,
)
from app.schemas.photo import HumanDetectionResult, VisionAnalysisOutput
from app.schemas.character import CharacterDNA
from app.schemas.story import StoryDiceRoll


logger = logging.getLogger(__name__)


# ============================================================================
# GEMINI CONFIGURATION
# ============================================================================

# Gemini 3.8 Flash is the current stable Flash model and supports:
# - text
# - image understanding
# - structured output
# - multimodal input
#
# Environment variables allow the model to be changed without editing code.
TEXT_MODEL_NAME = os.getenv(
    "GEMINI_TEXT_MODEL",
    "gemini-3.8-flash",
)

# Nano Banana 2 / Gemini 3.1 Flash Image
IMAGE_MODEL_NAME = os.getenv(
    "GEMINI_IMAGE_MODEL",
    "gemini-3.1-flash-image",
)


# ============================================================================
# ERROR / RETRY CONFIGURATION
# ============================================================================

RETRY_DELAYS = (
    1.5,
    3.0,
    6.0,
)

MAX_RETRIES = 3


def _unavailable(detail: str) -> HTTPException:
    """
    Fail closed.

    Never silently fall back to mock content when the real Gemini provider
    fails. Mock output should only be selected explicitly through the
    application's AI provider configuration.
    """
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=detail,
    )


def _is_retryable_error(exc: Exception) -> bool:
    """
    Determine whether a Gemini failure is likely temporary.

    Retry:
    - 429
    - 500
    - 502
    - 503
    - 504
    - UNAVAILABLE
    - RESOURCE_EXHAUSTED
    - DEADLINE_EXCEEDED
    - INTERNAL
    - overloaded/capacity errors
    """

    error_text = str(exc).upper()

    retryable_markers = (
        "429",
        "500",
        "502",
        "503",
        "504",
        "UNAVAILABLE",
        "RESOURCE_EXHAUSTED",
        "DEADLINE_EXCEEDED",
        "INTERNAL",
        "OVERLOADED",
        "HIGH DEMAND",
        "TEMPORARILY UNAVAILABLE",
        "RATE LIMIT",
    )

    return any(marker in error_text for marker in retryable_markers)


async def _gemini_with_retry(
    operation: Callable[[], Awaitable[Any]],
    *,
    operation_name: str,
    retries: int = MAX_RETRIES,
) -> Any:
    """
    Execute a Gemini operation with exponential-style backoff.

    Important:
    - Only transient provider failures are retried.
    - Validation errors, malformed responses and other permanent failures
      are not needlessly retried.
    - After all retries fail, the original exception is raised.
    """

    for attempt in range(retries):
        try:
            return await operation()

        except Exception as exc:
            if not _is_retryable_error(exc):
                logger.error(
                    "%s failed with non-retryable error: %s",
                    operation_name,
                    exc,
                    exc_info=True,
                )
                raise

            if attempt >= retries - 1:
                logger.error(
                    "%s failed after %d attempt(s): %s",
                    operation_name,
                    attempt + 1,
                    exc,
                    exc_info=True,
                )
                raise

            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]

            logger.warning(
                "%s temporarily unavailable. "
                "Retrying in %.1fs (attempt %d/%d). Error: %s",
                operation_name,
                delay,
                attempt + 1,
                retries,
                exc,
            )

            await asyncio.sleep(delay)

    raise RuntimeError(
        f"{operation_name} unexpectedly exited retry loop."
    )


# ============================================================================
# GEMINI CLIENT
# ============================================================================

def _init_client(api_key: str):
    """
    Initialize the Google GenAI client.

    Returns None if initialization fails.
    Callers must treat None as unavailable and fail closed.
    """

    if not api_key:
        logger.error("Gemini API key is missing.")
        return None

    try:
        from google import genai

        client = genai.Client(
            api_key=api_key,
        )

        logger.info(
            "Gemini client initialized successfully. "
            "text_model=%s image_model=%s",
            TEXT_MODEL_NAME,
            IMAGE_MODEL_NAME,
        )

        return client

    except Exception as exc:
        logger.error(
            "Failed to initialize google-genai client: %s",
            exc,
            exc_info=True,
        )
        return None


# ============================================================================
# RESPONSE HELPERS
# ============================================================================

def _parse_json_response(text: str) -> dict:
    """
    Parse Gemini JSON output.

    Supports:
    - normal JSON
    - ```json ... ```
    - accidental markdown fences
    """

    if not text:
        raise ValueError("Gemini returned an empty response.")

    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].strip().lower() in (
            "```json",
            "```",
        ):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    if not cleaned:
        raise ValueError("Gemini returned an empty JSON response.")

    return json.loads(cleaned)


def _response_text(response) -> str:
    """
    Safely retrieve response text.
    """

    text = getattr(response, "text", None)

    if not text:
        raise ValueError(
            "Gemini response did not contain text output."
        )

    return text


def _safety_block_reason(response) -> Optional[str]:
    """
    Inspect Gemini safety metadata independently from model-generated JSON.
    """

    feedback = getattr(
        response,
        "prompt_feedback",
        None,
    )

    block_reason = getattr(
        feedback,
        "block_reason",
        None,
    )

    if block_reason:
        return f"Blocked by safety filter: {block_reason}"

    candidates = getattr(
        response,
        "candidates",
        None,
    ) or []

    for candidate in candidates:

        finish_reason = getattr(
            candidate,
            "finish_reason",
            None,
        )

        if finish_reason:
            finish_name = getattr(
                finish_reason,
                "name",
                str(finish_reason),
            ).upper()

            allowed_finish_reasons = {
                "STOP",
                "1",
                "FINISH_REASON_STOP",
                "FINISHREASON.STOP",
            }

            if finish_name not in allowed_finish_reasons:
                return (
                    "Blocked by safety filter: "
                    f"{finish_name}"
                )

        safety_ratings = getattr(
            candidate,
            "safety_ratings",
            None,
        ) or []

        for rating in safety_ratings:

            probability = str(
                getattr(
                    rating,
                    "probability",
                    "",
                )
            ).upper()

            if probability in (
                "HIGH",
                "MEDIUM",
            ):
                category = getattr(
                    rating,
                    "category",
                    "unknown_category",
                )

                return (
                    f"Flagged for {category} "
                    f"({probability} probability)"
                )

    return None


def _guess_image_mime_type(
    filename: str,
    image_bytes: bytes,
) -> str:
    """
    Determine a safe MIME type for uploaded images.

    Falls back to JPEG because the existing SnapTale pipeline primarily
    sends JPEG images.
    """

    filename_lower = (
        filename or ""
    ).lower()

    if filename_lower.endswith(".png"):
        return "image/png"

    if filename_lower.endswith(".webp"):
        return "image/webp"

    if filename_lower.endswith(".gif"):
        return "image/gif"

    if filename_lower.endswith(".jpg") or filename_lower.endswith(".jpeg"):
        return "image/jpeg"

    # Magic-byte detection as a fallback.
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"

    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
        return "image/webp"

    if image_bytes.startswith(b"GIF8"):
        return "image/gif"

    return "image/jpeg"


# ============================================================================
# VISION PROVIDER
# ============================================================================

class GeminiVisionProvider(BaseVisionProvider):

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = _init_client(api_key)

    # ------------------------------------------------------------------------
    # HUMAN DETECTION
    # ------------------------------------------------------------------------

    async def detect_human(
        self,
        image_bytes: bytes,
        filename: str = "",
    ) -> HumanDetectionResult:

        if not self.client:
            raise _unavailable(
                "Human detection service is unavailable. "
                "Photo cannot be safely verified."
            )

        if not image_bytes:
            raise _unavailable(
                "The uploaded photo is empty and cannot be verified."
            )

        try:
            from google.genai import types

            mime_type = _guess_image_mime_type(
                filename,
                image_bytes,
            )

            prompt = """
Analyze this image STRICTLY for human presence.

Return TRUE if ANY visible human is present anywhere in the image.

This includes:
- a person's face
- full human body
- partial human body
- hands
- arms
- legs
- children
- groups of people
- selfies
- portraits
- people in the background
- people in reflections
- people partially hidden behind objects
- human body parts

Important:
Even if an animal or object is the main subject, if a human is visible
ANYWHERE in the frame, return TRUE.

Return FALSE only when there is NO visible human at all.

Do NOT infer:
- identity
- age
- gender
- ethnicity
- religion
- health
- other sensitive personal attributes

This is ONLY a binary human-presence classification.

Return the result using the supplied structured JSON schema.
"""

            async def call_gemini():
                return await self.client.aio.models.generate_content(
                    model=TEXT_MODEL_NAME,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=mime_type,
                        ),
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=HumanDetectionResult,
                    ),
                )

            response = await _gemini_with_retry(
                call_gemini,
                operation_name="Gemini human detection",
            )

            block_reason = _safety_block_reason(
                response
            )

            if block_reason:
                logger.warning(
                    "Gemini human detection blocked: %s",
                    block_reason,
                )

                raise _unavailable(
                    "Human detection could not safely verify "
                    "this photo. Please try another photo."
                )

            data = _parse_json_response(
                _response_text(response)
            )

            result = HumanDetectionResult(
                **data
            )

            logger.info(
                "Human detection completed: "
                "present=%s confidence=%.3f labels=%s",
                result.is_human_present,
                result.confidence,
                result.detected_labels,
            )

            return result

        except HTTPException:
            raise

        except Exception as exc:
            logger.error(
                "Gemini human detection failed closed: %s",
                exc,
                exc_info=True,
            )

            raise _unavailable(
                "Human detection service is temporarily "
                "unavailable. Your photo was not processed. "
                "Please try again in a moment."
            )

    # ------------------------------------------------------------------------
    # NON-HUMAN VISION ANALYSIS
    # ------------------------------------------------------------------------

    async def analyze_non_human(
        self,
        image_bytes: bytes,
    ) -> VisionAnalysisOutput:

        if not self.client:
            raise _unavailable(
                "Vision analysis service is unavailable."
            )

        if not image_bytes:
            raise _unavailable(
                "The uploaded photo is empty."
            )

        try:
            from google.genai import types

            prompt = """
Analyze this NON-HUMAN image.

Identify:

1. Primary non-human subject
   Examples:
   dog, cat, tea glass, chair, vintage car

2. Category
   Examples:
   animal, object, vehicle, food, plant, toy,
   building, gadget

3. Breed or type

4. Dominant color

5. Surrounding environment

6. Visible objects in frame

7. Estimated expression or mood

Do NOT identify or infer sensitive information about people.

The image has already passed the server-side human detection gate.

Return ONLY JSON:

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

            mime_type = _guess_image_mime_type(
                "",
                image_bytes,
            )

            async def call_gemini():
                return await self.client.aio.models.generate_content(
                    model=TEXT_MODEL_NAME,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=mime_type,
                        ),
                    ],
                )

            response = await _gemini_with_retry(
                call_gemini,
                operation_name="Gemini vision analysis",
            )

            block_reason = _safety_block_reason(
                response
            )

            if block_reason:
                raise _unavailable(
                    f"Vision analysis was blocked by safety filters: "
                    f"{block_reason}"
                )

            data = _parse_json_response(
                _response_text(response)
            )

            return VisionAnalysisOutput(
                **data
            )

        except HTTPException:
            raise

        except Exception as exc:
            logger.error(
                "Gemini vision analysis error: %s",
                exc,
                exc_info=True,
            )

            raise _unavailable(
                "Vision analysis service is temporarily "
                "unavailable. Please try again."
            )


# ============================================================================
# STORY PROVIDER
# ============================================================================

class GeminiStoryProvider(BaseStoryProvider):

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = _init_client(api_key)

    async def _generate_json(
        self,
        prompt: str,
    ) -> dict:

        if not self.client:
            raise _unavailable(
                "Story generation service is unavailable."
            )

        try:

            async def call_gemini():
                return await self.client.aio.models.generate_content(
                    model=TEXT_MODEL_NAME,
                    contents=prompt,
                )

            response = await _gemini_with_retry(
                call_gemini,
                operation_name="Gemini story generation",
            )

            block_reason = _safety_block_reason(
                response
            )

            if block_reason:
                raise _unavailable(
                    "Story generation was blocked by safety filters."
                )

            return _parse_json_response(
                _response_text(response)
            )

        except HTTPException:
            raise

        except Exception as exc:
            logger.error(
                "Gemini story generation error: %s",
                exc,
                exc_info=True,
            )

            raise _unavailable(
                "Story generation failed and will not "
                "fall back to placeholder content. "
                "Please try again."
            )

    # ------------------------------------------------------------------------
    # CHARACTER DNA
    # ------------------------------------------------------------------------

    async def generate_character_dna(
        self,
        vision: VisionAnalysisOutput,
        preferred_language: str = "te-en",
    ) -> CharacterDNA:

        prompt = f"""
Create a persistent Character DNA for an entertainment app called SnapTale.

Non-human visual subject:
{vision.subject}

Category:
{vision.category}

Type:
{vision.breed_or_type}

Color:
{vision.color}

Environment:
{vision.environment}

Expression:
{vision.estimated_expression}

Preferred language:
{preferred_language}

The voice should support natural conversational Telugu-English
"naatu naatu maatalu" code-switching.

DO NOT imitate living actors, comedians, celebrities or real people.

Select one original comedy archetype:

[
  confused_legend,
  deadpan_savage,
  overthinking_genius,
  overconfident_hero,
  victim_king,
  silent_killer,
  cunning_friend,
  innocent_idiot,
  mass_character,
  old_school_uncle,
  technical_fellow,
  dark_deadpan
]

Return ONLY JSON adhering to CharacterDNA.

{{
  "name": "Creative Name",
  "species_or_object": "{vision.subject}",
  "personality": [
    "trait1",
    "trait2",
    "trait3"
  ],
  "secret": "funny or absurd secret",
  "fear": "humorous fear",
  "origin": "origin lore",
  "occupation": "fictional occupation",
  "abilities": [
    "ability 1",
    "ability 2"
  ],
  "weaknesses": [
    "weakness 1"
  ],
  "appearance": {{
    "color": "{vision.color}",
    "details": "visual details"
  }},
  "comedy_archetype": "overconfident_hero",
  "humor_style": [
    "sarcasm",
    "absurdity"
  ],
  "speech_style": {{
    "language": "{preferred_language}",
    "register": "naatu",
    "slang": "naatu",
    "code_switching": 0.4
  }},
  "sarcasm_level": 0.85,
  "meme_level": 0.80,
  "dramatic_level": 0.90,
  "telugu_slang_level": 0.75,
  "english_mix": 0.35,
  "punchline_frequency": 0.85
}}
"""

        data = await self._generate_json(
            prompt
        )

        return CharacterDNA(
            **data
        )

    # ------------------------------------------------------------------------
    # STORY
    # ------------------------------------------------------------------------

    async def generate_story(
        self,
        character_dna: CharacterDNA,
        dice: StoryDiceRoll,
        mode: str = "snaptale",
        language: str = "te-en",
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, str]:

        is_mature = (
            mode == "snapplus"
        )

        structure = (
            "SETUP -> MISDIRECTION -> "
            "ESCALATION -> PUNCHLINE -> "
            "REACTION -> WHISTLE MOMENT"
            if is_mature
            else
            "SETUP -> CHARACTER -> PROBLEM -> "
            "CONFLICT -> TWIST -> CLIMAX -> ENDING"
        )

        prompt = f"""
You are the master entertainment writer for SnapTale.

Character:
{character_dna.name}

Species/Object:
{character_dna.species_or_object}

Personality:
{", ".join(character_dna.personality)}

Comedy archetype:
{character_dna.comedy_archetype}

Mode:
{mode}

SnapTale:
General entertainment, comedy, memes, absurdity,
sarcasm, chaos, adventure and cinematic storytelling.

SnapTale+:
Mature, darker comedy, savage humor, horror,
thriller and sophisticated mature themes.

Setting:
{dice.setting}

Goal:
{dice.goal}

Twist:
{dice.twist}

Chaos Mode:
{dice.chaos_mode}

Language:
{language}

Tone:
Natural conversational Telugu-English,
"naatu naatu maatalu" code-switching.

Do not write textbook Telugu.
Do not mechanically translate English.
Make dialogue sound like friends actually talking.

Do not imitate any real actor or comedian.

{f"Additional custom direction: {custom_prompt}" if custom_prompt else ""}

Follow this narrative structure:

{structure}

SnapTale should NOT make every sentence a joke.
Maintain a real beginning, conflict, twist and ending.

SnapTale+ should prioritize:
setup
misdirection
escalation
punchline
reaction
whistle moment

Return ONLY JSON:

{{
  "title": "Story Title",
  "content": "Full story",
  "punchline": "Memorable short punchline"
}}
"""

        return await self._generate_json(
            prompt
        )

    # ------------------------------------------------------------------------
    # MUTATION
    # ------------------------------------------------------------------------

    async def mutate_story(
        self,
        original_story_content: str,
        character_dna: CharacterDNA,
        mutation_type: str,
        mode: str = "snaptale",
        language: str = "te-en",
        custom_instruction: Optional[str] = None,
    ) -> Dict[str, str]:

        prompt = f"""
You are branching an existing SnapTale story into an alternate version.

Never overwrite the original story.

Character:
{character_dna.name}

Species/Object:
{character_dna.species_or_object}

Archetype:
{character_dna.comedy_archetype}

Original story:

\"\"\"
{original_story_content}
\"\"\"

Mutation type:
{mutation_type}

{f"Custom instruction: {custom_instruction}" if custom_instruction else ""}

Mode:
{mode}

Language:
{language}

Keep the character's core personality intact.

Shift the tone and genre to match the mutation.

Use natural conversational Telugu-English when appropriate.

Do not imitate real actors or comedians.

Return ONLY JSON:

{{
  "title": "New branch title",
  "content": "Full mutated story",
  "punchline": "Short punchline"
}}
"""

        return await self._generate_json(
            prompt
        )

    # ------------------------------------------------------------------------
    # WHAT IF
    # ------------------------------------------------------------------------

    async def what_if_story(
        self,
        original_story_content: str,
        character_dna: CharacterDNA,
        scenario: str,
        mode: str = "snaptale",
        language: str = "te-en",
    ) -> Dict[str, str]:

        prompt = f"""
Generate a "What If" alternate-reality branch
for an existing SnapTale character.

Character:
{character_dna.name}

Species/Object:
{character_dna.species_or_object}

Archetype:
{character_dna.comedy_archetype}

Original story:

\"\"\"
{original_story_content}
\"\"\"

What if scenario:
"{scenario}"

Mode:
{mode}

Language:
{language}

Create an original alternate reality.

Keep the character recognizable.

Use natural conversational Telugu-English
when appropriate.

Return ONLY JSON:

{{
  "title": "What If: ...",
  "content": "Full alternate-reality story",
  "punchline": "Short punchline"
}}
"""

        return await self._generate_json(
            prompt
        )

    # ------------------------------------------------------------------------
    # CONTINUE STORY
    # ------------------------------------------------------------------------

    async def continue_story(
        self,
        previous_story_content: str,
        character_dna: CharacterDNA,
        direction: Optional[str] = None,
        mode: str = "snaptale",
        language: str = "te-en",
    ) -> Dict[str, str]:

        direction_text = (
            f"Requested direction: {direction}"
            if direction
            else
            "Continue the natural next beat of the story."
        )

        prompt = f"""
Continue this SnapTale story with the next chapter.

Do NOT rewrite what came before.

Character:
{character_dna.name}

Species/Object:
{character_dna.species_or_object}

Archetype:
{character_dna.comedy_archetype}

Previous chapter:

\"\"\"
{previous_story_content}
\"\"\"

{direction_text}

Mode:
{mode}

Language:
{language}

Maintain character continuity.

Use natural conversational Telugu-English
when appropriate.

Return ONLY JSON:

{{
  "title": "Next chapter title",
  "content": "Full next-chapter story",
  "punchline": "Short punchline"
}}
"""

        return await self._generate_json(
            prompt
        )

    # ------------------------------------------------------------------------
    # CHARACTER CHAT
    # ------------------------------------------------------------------------

    async def chat_response(
        self,
        character_dna: CharacterDNA,
        chat_history: List[Dict[str, str]],
        message: str,
        universe_context: Optional[str] = None,
        is_snapplus: bool = False,
    ) -> str:

        if not self.client:
            raise _unavailable(
                "Chat service is unavailable."
            )

        history_text = "\n".join(
            f"{turn.get('role', 'user')}: "
            f"{turn.get('content', '')}"
            for turn in (
                chat_history or []
            )
        )

        prompt = f"""
You are roleplaying in-character as:

Name:
{character_dna.name}

Species/Object:
{character_dna.species_or_object}

Personality:
{", ".join(character_dna.personality)}

Comedy archetype:
{character_dna.comedy_archetype}

Secret:
{character_dna.secret}

Occupation:
{character_dna.occupation}

Speak in conversational Telugu-English code-switching
matching this character's established voice.

Do not imitate a real actor, comedian or celebrity.

{f"Universe context: {universe_context}" if universe_context else ""}

Content mode:
{
    "SnapTale+ (edgier, dark comedy allowed)"
    if is_snapplus
    else
    "SnapTale (general audience)"
}

Conversation so far:

{history_text}

User's new message:

"{message}"

Respond with a single short,
in-character reply.

Plain text only.
No JSON.
No quotation marks around the whole reply.
"""

        try:

            async def call_gemini():
                return await self.client.aio.models.generate_content(
                    model=TEXT_MODEL_NAME,
                    contents=prompt,
                )

            response = await _gemini_with_retry(
                call_gemini,
                operation_name="Gemini character chat",
            )

            block_reason = _safety_block_reason(
                response
            )

            if block_reason:
                raise _unavailable(
                    "Chat response was blocked by "
                    "safety filters."
                )

            return _response_text(
                response
            ).strip()

        except HTTPException:
            raise

        except Exception as exc:
            logger.error(
                "Gemini chat response error: %s",
                exc,
                exc_info=True,
            )

            raise _unavailable(
                "Chat service failed and will not "
                "fall back to placeholder dialogue. "
                "Please try again."
            )


# ============================================================================
# IMAGE PROVIDER
# ============================================================================

class GeminiImageProvider(BaseImageProvider):
    """
    Generates a real story-specific image.

    Never returns stock or mock imagery.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = _init_client(api_key)

    async def generate_story_image(
        self,
        character_dna: CharacterDNA,
        story_title: str,
        scene_summary: str,
        mode: str = "snaptale",
    ) -> str:

        if not self.client:
            raise _unavailable(
                "Image generation service is unavailable. "
                "Story cannot be illustrated right now."
            )

        try:
            from google.genai import types

            appearance = ", ".join(
                f"{key}: {value}"
                for key, value in (
                    character_dna.appearance or {}
                ).items()
            )

            tone = (
                "moody, cinematic, slightly dark "
                "comedic thriller lighting"
                if mode == "snapplus"
                else
                "bright, playful, meme-style "
                "comedic illustration"
            )

            prompt = f"""
Create a single vivid illustration for
a short-form comedic story app.

Subject:
{character_dna.name}

Species/Object:
{character_dna.species_or_object}

Personality:
{", ".join(character_dna.personality)}

Visual appearance:
{appearance or "as photographed"}

Scene:
{scene_summary}

Story title:
"{story_title}"

Style:
{tone}

Important restrictions:

- No text
- No lettering
- No logos
- No real identifiable human beings
- Keep the protagonist non-human
- Preserve the character's visual identity
- Create an original fictional illustration
"""

            async def call_gemini():
                return await self.client.aio.models.generate_content(
                    model=IMAGE_MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"]
                    ),
                )

            response = await _gemini_with_retry(
                call_gemini,
                operation_name="Gemini image generation",
            )

            image_bytes = None
            mime_type = "image/png"

            candidates = getattr(
                response,
                "candidates",
                None,
            ) or []

            for candidate in candidates:

                content = getattr(
                    candidate,
                    "content",
                    None,
                )

                parts = getattr(
                    content,
                    "parts",
                    None,
                ) or []

                for part in parts:

                    inline_data = getattr(
                        part,
                        "inline_data",
                        None,
                    )

                    if (
                        inline_data
                        and getattr(
                            inline_data,
                            "data",
                            None,
                        )
                    ):
                        image_bytes = (
                            inline_data.data
                        )

                        mime_type = getattr(
                            inline_data,
                            "mime_type",
                            mime_type,
                        )

                        break

                if image_bytes:
                    break

            if not image_bytes:
                raise ValueError(
                    "Gemini response contained "
                    "no image data."
                )

            encoded = base64.b64encode(
                image_bytes
            ).decode("utf-8")

            return (
                f"data:{mime_type};"
                f"base64,{encoded}"
            )

        except HTTPException:
            raise

        except Exception as exc:
            logger.error(
                "Gemini image generation error: %s",
                exc,
                exc_info=True,
            )

            raise _unavailable(
                "Image generation failed and will "
                "not fall back to placeholder imagery. "
                "Please try again."
            )


# ============================================================================
# MODERATION PROVIDER
# ============================================================================

class GeminiModerationProvider(BaseModerationProvider):
    """
    Real moderation backed by Gemini.

    Fails closed:
    if moderation itself fails, content is blocked
    instead of being allowed through.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = _init_client(api_key)

    # ------------------------------------------------------------------------
    # TEXT MODERATION
    # ------------------------------------------------------------------------

    async def check_content_safety(
        self,
        text: str,
        is_snapplus: bool = False,
    ) -> Dict[str, Any]:

        if not self.client:
            raise _unavailable(
                "Moderation service is unavailable. "
                "Content cannot be safely verified."
            )

        try:

            allowance = (
                "This app (SnapTale+) permits dark comedy, "
                "mild threat/thriller themes and edgy humor "
                "aimed at fictional non-human characters, "
                "but must still block genuinely harmful content."
                if is_snapplus
                else
                "This app (SnapTale) is general-audience "
                "comedic content and should apply a stricter, "
                "family-friendly bar."
            )

            prompt = f"""
You are a content safety reviewer for an entertainment app.

{allowance}

Review the following generated story text.

Block if it contains:
- sexual content involving minors
- non-consensual sexual content
- instructions for self-harm or suicide
- credible threats or incitement of real-world violence
- hate speech targeting protected groups
- severe illegal activity instructions
- other severe safety violations

Edgy fictional comedy by itself is not automatically unsafe.

Text to review:

\"\"\"
{text}
\"\"\"

Return ONLY JSON:

{{
  "is_safe": true,
  "reason": "short explanation"
}}
"""

            async def call_gemini():
                return await self.client.aio.models.generate_content(
                    model=TEXT_MODEL_NAME,
                    contents=prompt,
                )

            response = await _gemini_with_retry(
                call_gemini,
                operation_name="Gemini text moderation",
            )

            block_reason = _safety_block_reason(
                response
            )

            if block_reason:
                return {
                    "is_safe": False,
                    "reason": block_reason,
                    "action": "block",
                }

            data = _parse_json_response(
                _response_text(response)
            )

            is_safe = bool(
                data.get(
                    "is_safe",
                    False,
                )
            )

            return {
                "is_safe": is_safe,
                "reason": data.get(
                    "reason",
                    "Reviewed by Gemini moderation",
                ),
                "action": (
                    "allow"
                    if is_safe
                    else
                    "block"
                ),
            }

        except HTTPException:
            raise

        except Exception as exc:
            logger.error(
                "Gemini content moderation error: %s",
                exc,
                exc_info=True,
            )

            return {
                "is_safe": False,
                "reason": (
                    "Moderation service error; "
                    "content blocked as a precaution."
                ),
                "action": "block",
            }

    # ------------------------------------------------------------------------
    # IMAGE MODERATION
    # ------------------------------------------------------------------------

    async def check_image_safety(
        self,
        image_bytes: bytes,
        is_snapplus: bool = False,
    ) -> Dict[str, Any]:

        if not self.client:
            return {
                "is_safe": False,
                "reason": (
                    "Image moderation service unavailable; "
                    "cannot verify image."
                ),
                "action": "block",
            }

        if not image_bytes:
            return {
                "is_safe": False,
                "reason": "Image is empty.",
                "action": "block",
            }

        try:
            from google.genai import types

            prompt = """
Review this generated image for a comedic entertainment app.

Check for:

- sexual/explicit content
- gore or graphic violence
- hate symbolry
- real identifiable human faces
- visible human beings
- severe harmful content
- other serious policy violations

SnapTale only supports fictional non-human protagonists.

Return ONLY JSON:

{
  "is_safe": true,
  "reason": "short explanation"
}
"""

            mime_type = _guess_image_mime_type(
                "",
                image_bytes,
            )

            async def call_gemini():
                return await self.client.aio.models.generate_content(
                    model=TEXT_MODEL_NAME,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=mime_type,
                        ),
                    ],
                )

            response = await _gemini_with_retry(
                call_gemini,
                operation_name="Gemini image moderation",
            )

            block_reason = _safety_block_reason(
                response
            )

            if block_reason:
                return {
                    "is_safe": False,
                    "reason": block_reason,
                    "action": "block",
                }

            data = _parse_json_response(
                _response_text(response)
            )

            is_safe = bool(
                data.get(
                    "is_safe",
                    False,
                )
            )

            return {
                "is_safe": is_safe,
                "reason": data.get(
                    "reason",
                    "Reviewed by Gemini image moderation",
                ),
                "action": (
                    "allow"
                    if is_safe
                    else
                    "block"
                ),
            }

        except Exception as exc:
            logger.error(
                "Gemini image moderation error: %s",
                exc,
                exc_info=True,
            )

            return {
                "is_safe": False,
                "reason": (
                    "Image moderation service error; "
                    "content blocked as a precaution."
                ),
                "action": "block",
            }
