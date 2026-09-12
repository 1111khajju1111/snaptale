import asyncio
import base64
import json
import logging
import os
from io import BytesIO
from typing import List, Dict, Optional, Any

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
# HUGGING FACE CONFIGURATION
# ============================================================================

TEXT_MODEL_NAME = os.getenv(
    "HF_TEXT_MODEL",
    "openai/gpt-oss-20b",
)

VISION_MODEL_NAME = os.getenv(
    "HF_VISION_MODEL",
    "Qwen/Qwen2.5-VL-3B-Instruct",
)

IMAGE_MODEL_NAME = os.getenv(
    "HF_IMAGE_MODEL",
    "black-forest-labs/FLUX.1-schnell",
)


# Providers are separated by capability.
#
# Vision:
#   Featherless AI is currently selected because the SnapTale VLM
#   Qwen/Qwen2.5-VL-3B-Instruct is currently routed there on Hugging Face.
#
# Text:
#   auto lets Hugging Face select a compatible provider.
#
# Image:
#   auto lets Hugging Face select a compatible provider.
#
VISION_PROVIDER = os.getenv(
    "HF_VISION_PROVIDER",
    "featherless-ai",
)

TEXT_PROVIDER = os.getenv(
    "HF_TEXT_PROVIDER",
    "auto",
)

IMAGE_PROVIDER = os.getenv(
    "HF_IMAGE_PROVIDER",
    "auto",
)


# Retry configuration.
RETRY_DELAYS = (
    1.0,
    2.0,
    4.0,
)

MAX_RETRIES = 3


# ============================================================================
# COMMON HELPERS
# ============================================================================

def _unavailable(detail: str) -> HTTPException:
    """
    Return a safe 503 response.

    Human detection and moderation intentionally fail closed.
    """
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=detail,
    )


def _init_client(
    api_key: str,
    provider: str = "auto",
):
    """
    Initialize a Hugging Face InferenceClient.

    Provider is capability-specific:
        Vision  -> featherless-ai
        Text    -> auto
        Image   -> auto

    Hugging Face routes the request through its infrastructure when
    using an HF token.
    """

    if not api_key:
        logger.error(
            "Hugging Face token is missing."
        )
        return None

    try:
        from huggingface_hub import InferenceClient

        client = InferenceClient(
            provider=provider,
            api_key=api_key,
        )

        logger.info(
            "Initialized Hugging Face client with provider=%s",
            provider,
        )

        return client

    except Exception as exc:
        logger.error(
            "Failed to initialize Hugging Face client: %s",
            exc,
            exc_info=True,
        )
        return None


def _parse_json_response(
    text: str,
) -> dict:
    """
    Parse JSON from an AI response.

    Handles:
    - Plain JSON
    - ```json fenced blocks
    - JSON embedded in a small amount of prose
    """

    if not text:
        raise ValueError(
            "Model returned an empty response."
        )

    cleaned = text.strip()

    # Remove Markdown code fences.
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

    # First attempt: pure JSON.
    try:
        return json.loads(cleaned)

    except json.JSONDecodeError:
        pass

    # Second attempt: locate the outer JSON object.
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start >= 0 and end > start:
        return json.loads(
            cleaned[start : end + 1]
        )

    raise ValueError(
        "Model response did not contain valid JSON."
    )


def _message_text(result) -> str:
    """
    Extract text from a Hugging Face ChatCompletion response.
    """

    if not result:
        raise ValueError(
            "Model returned an empty response."
        )

    if not getattr(result, "choices", None):
        raise ValueError(
            "Model returned no choices."
        )

    choice = result.choices[0]

    message = getattr(
        choice,
        "message",
        None,
    )

    if not message:
        raise ValueError(
            "Model returned no message."
        )

    content = getattr(
        message,
        "content",
        None,
    )

    # Some providers may return content in a slightly different form.
    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))

        content = "".join(parts)

    if not content:
        raise ValueError(
            "Model returned no text content."
        )

    return str(content)


def _is_retryable(
    exc: Exception,
) -> bool:
    """
    Determine whether an HF error is likely temporary.
    """

    text = str(exc).upper()

    retryable_markers = (
        "429",
        "500",
        "502",
        "503",
        "504",
        "TIMEOUT",
        "RATE LIMIT",
        "OVERLOAD",
        "UNAVAILABLE",
        "TEMPORARY",
        "TOO MANY REQUESTS",
        "SERVER ERROR",
        "GATEWAY",
    )

    return any(
        marker in text
        for marker in retryable_markers
    )


async def _hf_chat(
    client,
    model: str,
    prompt: str,
    *,
    max_tokens: int = 1800,
    temperature: float = 0.8,
    image_data_uri: Optional[str] = None,
) -> str:
    """
    Execute a Hugging Face chat-completion request.

    Supports both:
    - Text-only prompts
    - Image + text VLM prompts
    """

    if image_data_uri:
        content = [
            {
                "type": "text",
                "text": prompt,
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_data_uri,
                },
            },
        ]

    else:
        content = prompt

    messages = [
        {
            "role": "user",
            "content": content,
        }
    ]

    last_exception = None

    for attempt in range(MAX_RETRIES):

        try:
            result = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return _message_text(result)

        except Exception as exc:

            last_exception = exc

            logger.warning(
                "Hugging Face request failed "
                "(attempt %s/%s): %s",
                attempt + 1,
                MAX_RETRIES,
                exc,
            )

            if (
                not _is_retryable(exc)
                or attempt == MAX_RETRIES - 1
            ):
                break

            await asyncio.sleep(
                RETRY_DELAYS[attempt]
            )

    raise last_exception


def _data_uri(
    image_bytes: bytes,
) -> str:
    """
    Convert image bytes into a base64 data URI.
    """

    encoded = base64.b64encode(
        image_bytes
    ).decode("ascii")

    return (
        "data:image/jpeg;base64,"
        + encoded
    )


# ============================================================================
# VISION PROVIDER
# ============================================================================

class HFVisionProvider(
    BaseVisionProvider
):

    def __init__(
        self,
        api_key: str,
    ):
        self.client = _init_client(
            api_key,
            provider=VISION_PROVIDER,
        )

        logger.info(
            "HFVisionProvider initialized "
            "model=%s provider=%s",
            VISION_MODEL_NAME,
            VISION_PROVIDER,
        )

    async def _vision_json(
        self,
        image_bytes: bytes,
        prompt: str,
    ) -> dict:

        if not self.client:
            raise _unavailable(
                "Vision service is unavailable. "
                "Photo cannot be safely verified."
            )

        if not image_bytes:
            raise _unavailable(
                "No image data was provided."
            )

        try:

            text = await _hf_chat(
                self.client,
                VISION_MODEL_NAME,
                prompt,
                max_tokens=900,
                temperature=0.1,
                image_data_uri=_data_uri(
                    image_bytes
                ),
            )

            return _parse_json_response(
                text
            )

        except HTTPException:
            raise

        except Exception as exc:

            logger.error(
                "Hugging Face vision error: %s",
                exc,
                exc_info=True,
            )

            # IMPORTANT:
            # Human detection must fail closed.
            raise _unavailable(
                "Vision service is temporarily "
                "unavailable. Please try again."
            )

    async def detect_human(
        self,
        image_bytes: bytes,
        filename: str = "",
    ) -> HumanDetectionResult:

        prompt = """
Analyze this image STRICTLY for visible human presence.

Return true if ANY of the following is visible anywhere:

- human
- person
- face
- body
- hand
- arm
- leg
- child
- human silhouette
- person in background
- human reflection
- human body part
- human-like visible body part belonging to a real person

Return false ONLY when no human is visible.

Do not infer:
- identity
- age
- gender
- ethnicity
- religion
- health
- personality
- sensitive attributes

This is a safety gate.

Return ONLY JSON in exactly this structure:

{
  "is_human_present": false,
  "confidence": 0.0,
  "detected_labels": []
}

If a human is visible, return:

{
  "is_human_present": true,
  "confidence": 0.95,
  "detected_labels": ["person"]
}
"""

        data = await self._vision_json(
            image_bytes,
            prompt,
        )

        try:

            result = HumanDetectionResult(
                **data
            )

        except Exception as exc:

            logger.error(
                "Invalid human detection response: %s",
                exc,
                exc_info=True,
            )

            raise _unavailable(
                "Human detection returned an invalid "
                "result. Please try again."
            )

        logger.info(
            "HF human detection: "
            "present=%s confidence=%.3f labels=%s",
            result.is_human_present,
            result.confidence,
            result.detected_labels,
        )

        return result

    async def analyze_non_human(
        self,
        image_bytes: bytes,
    ) -> VisionAnalysisOutput:

        prompt = """
Analyze this NON-HUMAN image.

Identify:

- primary non-human subject
- category
- breed/type
- dominant color
- environment
- visible objects
- estimated expression/mood

The image has already passed the server-side
human detection gate.

Do NOT identify or infer humans.

Return ONLY JSON:

{
  "subject": "string",
  "category": "string",
  "breed_or_type": "string",
  "color": "string",
  "environment": "string",
  "visible_objects": [],
  "estimated_expression": "string",
  "is_human_present": false
}
"""

        data = await self._vision_json(
            image_bytes,
            prompt,
        )

        # Defense-in-depth safety check.
        if bool(
            data.get(
                "is_human_present",
                False,
            )
        ):
            raise _unavailable(
                "Human presence could not be "
                "safely ruled out."
            )

        try:

            return VisionAnalysisOutput(
                **data
            )

        except Exception as exc:

            logger.error(
                "Invalid vision analysis response: %s",
                exc,
                exc_info=True,
            )

            raise _unavailable(
                "Vision analysis returned an invalid "
                "result. Please try again."
            )


# ============================================================================
# STORY PROVIDER
# ============================================================================

class HFStoryProvider(
    BaseStoryProvider
):

    def __init__(
        self,
        api_key: str,
    ):

        self.api_key = api_key

        self.client = _init_client(
            api_key,
            provider=TEXT_PROVIDER,
        )

        self.text_model = TEXT_MODEL_NAME

        logger.info(
            "HFStoryProvider initialized "
            "model=%s provider=%s",
            self.text_model,
            TEXT_PROVIDER,
        )

    async def _generate_json(
        self,
        prompt: str,
    ) -> dict:

        if not self.client:
            raise _unavailable(
                "Hugging Face text generation "
                "service is unavailable."
            )

        try:

            text = await _hf_chat(
                self.client,
                self.text_model,
                prompt,
                max_tokens=2200,
                temperature=0.85,
            )

            return _parse_json_response(
                text
            )

        except HTTPException:
            raise

        except Exception as exc:

            logger.error(
                "Hugging Face story generation "
                "error: %s",
                exc,
                exc_info=True,
            )

            raise _unavailable(
                "Story generation failed. "
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
Create a persistent Character DNA for an
entertainment app called SnapTale.

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

The voice should support natural conversational
Telugu-English "naatu naatu maatalu" code-switching.

DO NOT imitate living actors, comedians,
celebrities or real people.

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

        try:

            return CharacterDNA(
                **data
            )

        except Exception as exc:

            logger.error(
                "Invalid CharacterDNA response: %s",
                exc,
                exc_info=True,
            )

            raise _unavailable(
                "Character generation returned "
                "an invalid result."
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
You are the master entertainment writer
for SnapTale.

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
General entertainment, comedy, memes,
absurdity, sarcasm, chaos, adventure
and cinematic storytelling.

SnapTale+:
Mature, darker comedy, savage humor,
horror, thriller and sophisticated
mature themes.

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

{
    f"Additional custom direction: {custom_prompt}"
    if custom_prompt
    else ""
}

Follow this narrative structure:

{structure}

SnapTale should NOT make every sentence
a joke.

Maintain a real beginning, conflict,
twist and ending.

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
You are branching an existing SnapTale
story into an alternate version.

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

{
    f"Custom instruction: {custom_instruction}"
    if custom_instruction
    else ""
}

Mode:
{mode}

Language:
{language}

Keep the character's core personality intact.

Shift the tone and genre to match
the mutation.

Use natural conversational
Telugu-English when appropriate.

Do not imitate real actors
or comedians.

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

Use natural conversational
Telugu-English when appropriate.

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
Continue this SnapTale story
with the next chapter.

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

Use natural conversational
Telugu-English when appropriate.

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

Speak in conversational Telugu-English
code-switching matching this character's
established voice.

Do not imitate a real actor,
comedian or celebrity.

{
    f"Universe context: {universe_context}"
    if universe_context
    else ""
}

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

            response = await _hf_chat(
                self.client,
                self.text_model,
                prompt,
                max_tokens=500,
                temperature=0.9,
            )

            return response.strip()

        except HTTPException:
            raise

        except Exception as exc:

            logger.error(
                "Hugging Face chat response error: %s",
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

class HFImageProvider(
    BaseImageProvider
):

    def __init__(
        self,
        api_key: str,
    ):

        self.client = _init_client(
            api_key,
            provider=IMAGE_PROVIDER,
        )

        logger.info(
            "HFImageProvider initialized "
            "model=%s provider=%s",
            IMAGE_MODEL_NAME,
            IMAGE_PROVIDER,
        )

    async def generate_story_image(
        self,
        character_dna: CharacterDNA,
        story_title: str,
        scene_summary: str,
        mode: str = "snaptale",
    ) -> str:

        if not self.client:
            raise _unavailable(
                "Image generation service "
                "is unavailable."
            )

        appearance = ", ".join(
            f"{key}: {value}"
            for key, value in (
                character_dna.appearance or {}
            ).items()
        )

        if mode == "snapplus":

            tone = (
                "moody cinematic dark-comedy "
                "thriller"
            )

        else:

            tone = (
                "bright playful meme-style "
                "comedic illustration"
            )

        prompt = f"""
Create one original fictional illustration
for SnapTale.

Non-human protagonist:
{character_dna.name}

Species/object:
{character_dna.species_or_object}

Personality:
{", ".join(character_dna.personality)}

Appearance:
{appearance or "as photographed"}

Scene:
{scene_summary}

Title:
{story_title}

Style:
{tone}

Requirements:

- No humans
- No human faces
- No human bodies
- No human silhouettes
- No text
- No lettering
- No logos
- No watermarks
- Keep protagonist non-human
- Preserve visual identity
- Original fictional artwork
"""

        try:

            image = await asyncio.to_thread(
                self.client.text_to_image,
                prompt,
                model=IMAGE_MODEL_NAME,
            )

            buffer = BytesIO()

            image.save(
                buffer,
                format="PNG",
            )

            encoded = base64.b64encode(
                buffer.getvalue()
            ).decode("ascii")

            return (
                "data:image/png;base64,"
                + encoded
            )

        except Exception as exc:

            logger.error(
                "Hugging Face image generation "
                "error: %s",
                exc,
                exc_info=True,
            )

            raise _unavailable(
                "Image generation failed. "
                "Please try again."
            )


# ============================================================================
# MODERATION PROVIDER
# ============================================================================

class HFModerationProvider(
    BaseModerationProvider
):

    def __init__(
        self,
        api_key: str,
    ):

        # Vision moderation uses the same VLM provider
        # as human detection.
        self.client = _init_client(
            api_key,
            provider=VISION_PROVIDER,
        )

        logger.info(
            "HFModerationProvider initialized "
            "vision_provider=%s text_model=%s",
            VISION_PROVIDER,
            TEXT_MODEL_NAME,
        )

    # ------------------------------------------------------------------------
    # TEXT MODERATION
    # ------------------------------------------------------------------------

    async def check_content_safety(
        self,
        text: str,
        is_snapplus: bool = False,
    ) -> Dict[str, Any]:

        if not self.client:
            return {
                "is_safe": False,
                "reason": (
                    "Moderation service unavailable."
                ),
                "action": "block",
            }

        if is_snapplus:

            mode_instruction = (
                "SnapTale+ permits dark comedy, "
                "edgy fictional themes and stronger "
                "language, but still blocks severe "
                "harmful content."
            )

        else:

            mode_instruction = (
                "SnapTale is general-audience and "
                "should use a family-friendly bar."
            )

        prompt = f"""
You are a strict safety reviewer
for SnapTale.

{mode_instruction}

Block:

- sexual content involving minors
- non-consensual sexual content
- self-harm instructions
- suicide instructions
- credible real-world violence
- incitement to violence
- hate speech targeting protected groups
- severe illegal instructions
- serious real-world wrongdoing instructions
- other severe safety violations

Edgy fictional comedy alone is NOT
automatically unsafe.

Review:

{text!r}

Return ONLY JSON:

{{
  "is_safe": true,
  "reason": "short explanation"
}}
"""

        try:

            result = await _hf_chat(
                self.client,
                TEXT_MODEL_NAME,
                prompt,
                max_tokens=300,
                temperature=0.0,
            )

            data = _parse_json_response(
                result
            )

            safe = bool(
                data.get(
                    "is_safe",
                    False,
                )
            )

            return {
                "is_safe": safe,
                "reason": data.get(
                    "reason",
                    "Reviewed by Hugging Face model",
                ),
                "action": (
                    "allow"
                    if safe
                    else "block"
                ),
            }

        except Exception as exc:

            logger.error(
                "HF text moderation error: %s",
                exc,
                exc_info=True,
            )

            # Fail closed.
            return {
                "is_safe": False,
                "reason": (
                    "Moderation service error; "
                    "blocked as precaution."
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
                    "Image moderation unavailable."
                ),
                "action": "block",
            }

        if not image_bytes:
            return {
                "is_safe": False,
                "reason": (
                    "No image data provided."
                ),
                "action": "block",
            }

        prompt = """
Review this generated image.

Block:

- explicit sexual content
- gore
- graphic violence
- hate symbols
- real identifiable human faces
- real people
- human bodies
- severe harmful content

SnapTale uses fictional
non-human protagonists.

Return ONLY JSON:

{
  "is_safe": true,
  "reason": "short explanation"
}
"""

        try:

            result = await _hf_chat(
                self.client,
                VISION_MODEL_NAME,
                prompt,
                max_tokens=250,
                temperature=0.0,
                image_data_uri=_data_uri(
                    image_bytes
                ),
            )

            data = _parse_json_response(
                result
            )

            safe = bool(
                data.get(
                    "is_safe",
                    False,
                )
            )

            return {
                "is_safe": safe,
                "reason": data.get(
                    "reason",
                    "Reviewed by Hugging Face "
                    "vision model",
                ),
                "action": (
                    "allow"
                    if safe
                    else "block"
                ),
            }

        except Exception as exc:

            logger.error(
                "HF image moderation error: %s",
                exc,
                exc_info=True,
            )

            # Fail closed.
            return {
                "is_safe": False,
                "reason": (
                    "Image moderation error; "
                    "blocked as precaution."
                ),
                "action": "block",
            }
