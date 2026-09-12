import base64
import logging
from typing import Optional
from app.core.config import settings
from app.ai import moderation_provider

logger = logging.getLogger(__name__)


def _extract_image_bytes(image_url: str) -> Optional[bytes]:
    """If the image "URL" is actually an inline data: URI (as returned by
    GeminiImageProvider), decode and return the raw image bytes so the
    moderation provider can inspect the real generated image."""
    if not image_url or not image_url.startswith("data:"):
        return None
    try:
        _, b64_data = image_url.split(",", 1)
        return base64.b64decode(b64_data)
    except Exception:
        return None


async def is_generated_image_safe(
    image_url: str,
    scene_summary: str,
    story_title: str,
    is_snapplus: bool = False
) -> bool:
    """Moderate the actual generated image bytes, not just a text description.

    Real (AI_PROVIDER=gemini) mode: if the image bytes can't be extracted and
    inspected, that's a moderation failure — fail closed (return False) rather
    than silently falling back to checking a text description.

    Mock/dev mode only: the mock image provider returns plain stock URLs with
    no inspectable bytes by design, so we fall back to the (also mocked) text
    check purely to keep local/dev flows running — this path never runs in
    production because AI_PROVIDER=mock is rejected at production startup.
    """
    image_bytes = _extract_image_bytes(image_url)

    if image_bytes is not None:
        try:
            safety = await moderation_provider.check_image_safety(image_bytes, is_snapplus=is_snapplus)
            return bool(safety.get("is_safe", False))
        except Exception as e:
            logger.error(f"Image safety check failed unexpectedly: {e}")
            return False

    if settings.AI_PROVIDER.lower() == "gemini":
        # Real provider mode with no inspectable image bytes is an unexpected
        # state (GeminiImageProvider always returns a data: URI on success) -
        # fail closed instead of silently degrading to text-only moderation.
        logger.error("No inspectable image bytes available under AI_PROVIDER=gemini; failing closed.")
        return False

    # Dev/test mock mode only.
    try:
        safety = await moderation_provider.check_content_safety(
            f"Generated visual scene for {story_title}: {scene_summary}",
            is_snapplus=is_snapplus
        )
        return bool(safety.get("is_safe", True))
    except Exception as e:
        logger.error(f"Mock image safety fallback check failed: {e}")
        return False
