import asyncio
import base64
import json
import logging
import mimetypes
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

# Gemma 3 12B is the recommended SnapTale VLM.
#
# It is used for:
#   - human detection
#   - non-human image analysis
#   - generated-image moderation
#
# Provider is configured independently below.
VISION_MODEL_NAME = os.getenv(
    "HF_VISION_MODEL",
    "google/gemma-3-12b-it",
)

IMAGE_MODEL_NAME = os.getenv(
    "HF_IMAGE_MODEL",
    "black-forest-labs/FLUX.1-schnell",
)


# ============================================================================
# PROVIDERS
# ============================================================================
#
# Providers are intentionally capability-specific.
#
# Vision:
#   DeepInfra for Gemma 3 vision.
#
# Text:
#   auto lets Hugging Face select an available compatible provider.
#
# Image:
#   auto lets Hugging Face select an available image provider.
#
# IMPORTANT:
# Do not use one global HF_PROVIDER here.
# Different models may have completely different provider availability.
# ============================================================================

VISION_PROVIDER = os.getenv(
    "HF_VISION_PROVIDER",
    "deepinfra",
)

TEXT_PROVIDER = os.getenv(
    "HF_TEXT_PROVIDER",
    "auto",
)

IMAGE_PROVIDER = os.getenv(
    "HF_IMAGE_PROVIDER",
    "auto",
)


# ============================================================================
# RETRY CONFIGURATION
# ============================================================================

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
    Initialize Hugging Face InferenceClient.

    Provider is capability-specific:

        Vision -> deepinfra
        Text   -> auto
        Image  -> auto
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
            "Initialized Hugging Face client provider=%s",
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


# ============================================================================
# JSON PARSER
# ============================================================================

def _parse_json_response(
    text: str,
) -> dict:
    """
    Parse JSON from an AI response.

    Supports:

    1. Plain JSON
    2. Markdown fenced JSON
    3. JSON surrounded by small amounts of prose
    """

    if not text:
        raise ValueError(
            "Model returned an empty response."
        )

    cleaned = text.strip()

    # ------------------------------------------------------------------------
    # Remove markdown code fences
    # ------------------------------------------------------------------------

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines:
            first = lines[0].strip().lower()

            if first in (
                "```json",
                "```",
            ):
                lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    # ------------------------------------------------------------------------
    # Direct JSON
    # ------------------------------------------------------------------------

    try:
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # ------------------------------------------------------------------------
    # Extract JSON object from surrounding text
    # ------------------------------------------------------------------------

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start >= 0 and end > start:
        candidate = cleaned[start:end + 1]

        try:
            parsed = json.loads(candidate)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Model response did not contain valid JSON."
    )


# ============================================================================
# RESPONSE TEXT EXTRACTION
# ============================================================================

def _message_text(result) -> str:
    """
    Extract generated text from Hugging Face OpenAI-compatible
    ChatCompletion responses.

    Different inference providers can expose slightly different
    response structures, so this function intentionally performs
    defensive extraction.
    """

    if not result:
        raise ValueError(
            "Model returned an empty response."
        )

    choices = getattr(
        result,
        "choices",
        None,
    )

    if not choices:
        raise ValueError(
            "Model returned no choices."
        )

    choice = choices[0]

    message = getattr(
        choice,
        "message",
        None,
    )

    # ------------------------------------------------------------------------
    # Standard message.content
    # ------------------------------------------------------------------------

    if message is not None:

        content = getattr(
            message,
            "content",
            None,
        )

        if isinstance(content, str):

            if content.strip():
                return content.strip()

        # --------------------------------------------------------------------
        # Structured content blocks
        # --------------------------------------------------------------------

        if isinstance(content, list):

            parts = []

            for item in content:

                if isinstance(item, dict):

                    text = item.get("text")

                    if text:
                        parts.append(str(text))

                else:

                    text = getattr(
                        item,
                        "text",
                        None,
                    )

                    if text:
                        parts.append(str(text))

            combined = "".join(parts).strip()

            if combined:
                return combined

        # --------------------------------------------------------------------
        # Reasoning-capable providers
        #
        # Some providers/models may place generated content in one of these
        # fields rather than message.content.
        # --------------------------------------------------------------------

        for attribute in (
            "output_text",
            "reasoning_content",
            "reasoning",
            "text",
        ):

            value = getattr(
                message,
                attribute,
                None,
            )

            if isinstance(value, str):

                if value.strip():
                    return value.strip()

    # ------------------------------------------------------------------------
    # Some providers expose text directly on choice
    # ------------------------------------------------------------------------

    for attribute in (
        "text",
        "output_text",
    ):

        value = getattr(
            choice,
            attribute,
            None,
        )

        if isinstance(value, str):

            if value.strip():
                return value.strip()

    # ------------------------------------------------------------------------
    # Diagnostics without dumping the complete response
    # ------------------------------------------------------------------------

    message_attributes = []

    if message is not None:

        try:
            message_attributes = [
                attribute
                for attribute in dir(message)
                if not attribute.startswith("_")
            ]
        except Exception:
            message_attributes = []

    logger.error(
        "Hugging Face returned no usable text. "
        "result_type=%s choice_type=%s message_type=%s "
        "message_attributes=%s",
        type(result).__name__,
        type(choice).__name__,
        type(message).__name__
        if message is not None
        else "None",
        message_attributes,
    )

    raise ValueError(
        "Model returned no text content."
    )


# ============================================================================
# ERROR CLASSIFICATION
# ============================================================================

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
        "CAPACITY_EXHAUSTED",
        "CONNECTION RESET",
        "CONNECTION ERROR",
    )

    return any(
        marker in text
        for marker in retryable_markers
    )


# ============================================================================
# HUGGING FACE CHAT
# ============================================================================

async def _hf_chat(
    client,
    model: str,
    prompt: str,
    *,
    max_tokens: int = 1800,
    temperature: float = 0.8,
    image_data_uri: Optional[str] = None,
    json_mode: bool = False,
) -> str:
    """
    Execute a Hugging Face chat-completion request.

    Supports:

    - text-only prompts
    - image + text VLM prompts
    - JSON response mode
    - automatic fallback when response_format is unsupported
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

    base_kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    # ------------------------------------------------------------------------
    # JSON mode
    # ------------------------------------------------------------------------

    request_kwargs = dict(base_kwargs)

    if json_mode:
        request_kwargs["response_format"] = {
            "type": "json_object",
        }

    last_exception = None

    for attempt in range(MAX_RETRIES):

        try:

            result = await asyncio.to_thread(
                client.chat.completions.create,
                **request_kwargs,
            )

            return _message_text(result)

        except Exception as exc:

            last_exception = exc

            error_text = str(exc)

            # ----------------------------------------------------------------
            # Some providers/models do not implement response_format.
            #
            # Retry once without response_format rather than immediately
            # failing a perfectly valid JSON prompt.
            # ----------------------------------------------------------------

            if (
                json_mode
                and "response_format" in request_kwargs
                and any(
                    marker in error_text.lower()
                    for marker in (
                        "response_format",
                        "json_object",
                        "unsupported",
                        "not supported",
                    )
                )
            ):

                logger.warning(
                    "HF provider does not appear to support "
                    "response_format for model=%s. "
                    "Retrying with prompt-enforced JSON.",
                    model,
                )

                request_kwargs = dict(base_kwargs)

                continue

            retryable = _is_retryable(exc)

            logger.warning(
                "Hugging Face request failed "
                "(attempt %s/%s, retryable=%s, model=%s, provider=%s): %s",
                attempt + 1,
                MAX_RETRIES,
                retryable,
                model,
                getattr(
                    client,
                    "provider",
                    "unknown",
                ),
                exc,
            )

            if (
                not retryable
                or attempt == MAX_RETRIES - 1
            ):
                break

            await asyncio.sleep(
                RETRY_DELAYS[attempt]
            )

    if last_exception is not None:
        raise last_exception

    raise ValueError(
        "Hugging Face request failed "
        "without a specific exception."
    )


# ============================================================================
# IMAGE DATA URI
# ============================================================================

def _detect_mime_type(
    image_bytes: bytes,
) -> str:
    """
    Detect common image MIME types from magic bytes.

    Falls back to image/jpeg.
    """

    if not image_bytes:
        return "image/jpeg"

    # JPEG
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # PNG
    if image_bytes.startswith(
        b"\x89PNG\r\n\x1a\n"
    ):
        return "image/png"

    # GIF
    if image_bytes.startswith(
        b"GIF87a"
    ) or image_bytes.startswith(
        b"GIF89a"
    ):
        return "image/gif"

    # WEBP
    if (
        image_bytes.startswith(b"RIFF")
        and b"WEBP" in image_bytes[:16]
    ):
        return "image/webp"

    # BMP
    if image_bytes.startswith(b"BM"):
        return "image/bmp"

    return "image/jpeg"


def _data_uri(
    image_bytes: bytes,
) -> str:
    """
    Convert image bytes into a base64 data URI.
    """

    if not image_bytes:
        raise ValueError(
            "Cannot create data URI from empty image."
        )

    mime_type = _detect_mime_type(
        image_bytes
    )

    encoded = base64.b64encode(
        image_bytes
    ).decode("ascii")

    return (
        f"data:{mime_type};base64,"
        f"{encoded}"
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
                # Keep false for maximum compatibility
                # with multimodal provider implementations.
                json_mode=False,
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

            # Human detection must fail closed.

            raise _unavailable(
                "Vision service is temporarily "
                "unavailable. Please try again."
            )

    # ------------------------------------------------------------------------
    # HUMAN DETECTION
    # ------------------------------------------------------------------------

    async def detect_human(
        self,
        image_bytes: bytes,
        filename: str = "",
    ) -> HumanDetectionResult:

        prompt = """
You are the safety gate for SnapTale.

Analyze this image ONLY for visible real human presence.

SnapTale supports animals and non-human objects only.

Return true if ANY real human content is visible anywhere,
including:

- person
- human face
- human body
- hand
- arm
- leg
- child
- human silhouette
- person in background
- human reflection
- visible human body part

If even a small visible part of a real person is present,
return is_human_present=true.

Important:

Do NOT identify the person.

Do NOT infer:

- identity
- age
- gender
- ethnicity
- religion
- health
- personality
- socioeconomic status
- other sensitive attributes

This is a safety classification task.

Return ONLY valid JSON.

Use exactly:

{
  "is_human_present": false,
  "confidence": 0.0,
  "detected_labels": []
}

If a human is visible:

{
  "is_human_present": true,
  "confidence": 0.95,
  "detected_labels": ["person"]
}

No markdown.
No explanation.
No additional fields.
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

    # ------------------------------------------------------------------------
    # NON-HUMAN VISION ANALYSIS
    # ------------------------------------------------------------------------

    async def analyze_non_human(
        self,
        image_bytes: bytes,
    ) -> VisionAnalysisOutput:

        prompt = """
Analyze this image for SnapTale.

The image has already passed a separate human-presence
safety gate.

Analyze ONLY the primary non-human subject.

Identify:

- primary subject
- broad category
- breed/type if visually reasonable
- dominant visible color
- environment
- visible non-human objects
- visible expression or apparent mood

Do not identify or infer any human.

Do not infer sensitive human attributes.

If the image contains a person or human body part,
set:

"is_human_present": true

Otherwise set:

"is_human_present": false

Return ONLY valid JSON.

Exactly:

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

No markdown.
No explanation.
No additional fields.
"""

        data = await self._vision_json(
            image_bytes,
            prompt,
        )

        # --------------------------------------------------------------------
        # Defense-in-depth safety check
        # --------------------------------------------------------------------

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
                json_mode=True,
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
Create a persistent Character DNA for
an entertainment app called SnapTale.

The character MUST be based on a non-human
animal or object.

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

Voice requirements:

- natural conversational Telugu-English
- casual friend-group style
- "naatu naatu maatalu"
- natural code-switching
- not textbook Telugu
- not robotic translation

DO NOT imitate living actors, comedians,
celebrities or real people.

Select exactly ONE original comedy archetype:

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

Make the character memorable but original.

Return ONLY valid JSON matching CharacterDNA.

Required structure:

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

No markdown.
No explanation.
No additional fields.
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

        custom_direction = (
            f"Additional custom direction: "
            f"{custom_prompt}"
            if custom_prompt
            else ""
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
General entertainment including:

- comedy
- memes
- absurdity
- sarcasm
- chaos
- adventure
- cinematic storytelling
- unexpected twists

SnapTale+:
Mature entertainment including:

- darker comedy
- savage humor
- horror
- thriller
- sophisticated mature themes
- stronger conversational language where appropriate

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

Natural conversational Telugu-English.

Use:
"naatu naatu maatalu"

Do not write textbook Telugu.

Do not mechanically translate English.

Make dialogue sound like real friends talking.

The character must remain an original fictional
non-human character.

Do not imitate any real actor, comedian,
celebrity or public figure.

{custom_direction}

Follow this narrative structure:

{structure}

SnapTale should NOT make every sentence a joke.

Maintain:

- beginning
- conflict
- character motivation
- escalation
- twist
- ending

SnapTale+ should prioritize:

- setup
- misdirection
- escalation
- punchline
- reaction
- whistle moment

The humor should come from timing,
personality and situation rather than
constant profanity.

Return ONLY this JSON object:

{{
  "title": "Story Title",
  "content": "Full story",
  "punchline": "Memorable short punchline"
}}

No markdown.
No explanation.
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

        custom_direction = (
            f"Custom instruction: "
            f"{custom_instruction}"
            if custom_instruction
            else ""
        )

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

{custom_direction}

Mode:
{mode}

Language:
{language}

Keep the character's core personality intact.

Shift the tone and genre to match the mutation.

Use natural conversational
Telugu-English when appropriate.

Do not imitate real actors,
comedians or celebrities.

Return ONLY this JSON object:

{{
  "title": "New branch title",
  "content": "Full mutated story",
  "punchline": "Short punchline"
}}

No markdown.
No explanation.
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

Do not imitate real actors,
comedians or celebrities.

Return ONLY this JSON object:

{{
  "title": "What If: ...",
  "content": "Full alternate-reality story",
  "punchline": "Short punchline"
}}

No markdown.
No explanation.
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
            "Continue the natural next beat "
            "of the story."
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

Do not imitate real actors,
comedians or celebrities.

Return ONLY this JSON object:

{{
  "title": "Next chapter title",
  "content": "Full next-chapter story",
  "punchline": "Short punchline"
}}

No markdown.
No explanation.
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

        universe_text = (
            f"Universe context: {universe_context}"
            if universe_context
            else ""
        )

        content_mode = (
            "SnapTale+ "
            "(edgier dark comedy allowed)"
            if is_snapplus
            else
            "SnapTale "
            "(general audience)"
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

Use natural "naatu naatu maatalu".

Do not sound like a textbook.

Do not mechanically translate English.

Do not imitate a real actor,
comedian or celebrity.

{universe_text}

Content mode:
{content_mode}

Conversation so far:

{history_text}

User's new message:

"{message}"

Respond with ONE short,
in-character reply.

Plain text only.

No JSON.
No markdown.
No quotation marks around the entire reply.
"""

        try:

            response = await _hf_chat(
                self.client,
                self.text_model,
                prompt,
                max_tokens=500,
                temperature=0.9,
                json_mode=False,
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
                "thriller illustration"
            )

        else:

            tone = (
                "bright playful surreal "
                "meme-style comedic illustration"
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

- non-human protagonist only
- no humans
- no human faces
- no human bodies
- no human silhouettes
- no human body parts
- no text
- no lettering
- no logos
- no watermarks
- preserve protagonist visual identity
- original fictional artwork
"""

        try:

            image = await asyncio.to_thread(
                self.client.text_to_image,
                prompt,
                model=IMAGE_MODEL_NAME,
            )

            if image is None:

                raise ValueError(
                    "Image provider returned no image."
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

        except HTTPException:
            raise

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

        # --------------------------------------------------------------------
        # Text moderation -> TEXT provider
        # Image moderation -> VISION provider
        #
        # This prevents accidentally sending a text moderation request
        # through a VLM-only provider.
        # --------------------------------------------------------------------

        self.text_client = _init_client(
            api_key,
            provider=TEXT_PROVIDER,
        )

        self.vision_client = _init_client(
            api_key,
            provider=VISION_PROVIDER,
        )

        logger.info(
            "HFModerationProvider initialized "
            "text_provider=%s "
            "vision_provider=%s",
            TEXT_PROVIDER,
            VISION_PROVIDER,
        )

    # ------------------------------------------------------------------------
    # TEXT MODERATION
    # ------------------------------------------------------------------------

    async def check_content_safety(
        self,
        text: str,
        is_snapplus: bool = False,
    ) -> Dict[str, Any]:

        if not self.text_client:

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

Review this content:

{text!r}

Return ONLY valid JSON:

{{
  "is_safe": true,
  "reason": "short explanation"
}}

No markdown.
No additional fields.
"""

        try:

            result = await _hf_chat(
                self.text_client,
                TEXT_MODEL_NAME,
                prompt,
                max_tokens=300,
                temperature=0.0,
                json_mode=True,
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

        if not self.vision_client:

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
Review this generated image for SnapTale.

SnapTale uses fictional non-human protagonists.

Block if the generated image contains:

- explicit sexual content
- gore
- graphic violence
- hate symbols
- real identifiable human faces
- real people
- human bodies
- human body parts
- human silhouettes
- severe harmful content

The image should contain a non-human protagonist.

Return ONLY valid JSON:

{
  "is_safe": true,
  "reason": "short explanation"
}

No markdown.
No additional fields.
"""

        try:

            result = await _hf_chat(
                self.vision_client,
                VISION_MODEL_NAME,
                prompt,
                max_tokens=250,
                temperature=0.0,
                image_data_uri=_data_uri(
                    image_bytes
                ),
                json_mode=False,
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
                    "Reviewed by Hugging Face vision model",
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
