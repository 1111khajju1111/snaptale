from app.core.config import settings
from app.ai.base import (
    BaseVisionProvider, BaseStoryProvider, BaseImageProvider, BaseModerationProvider
)
from app.ai.mock_provider import (
    MockVisionProvider, MockStoryProvider, MockImageProvider, MockModerationProvider
)
from app.ai.gemini_provider import (
    GeminiVisionProvider, GeminiStoryProvider, GeminiImageProvider, GeminiModerationProvider
)
from app.ai.hf_provider import (
    HFVisionProvider, HFStoryProvider, HFImageProvider, HFModerationProvider
)

def get_ai_providers():
    provider_type = settings.AI_PROVIDER.lower()
    api_key = (settings.HF_TOKEN or settings.AI_PROVIDER_API_KEY) if provider_type == "huggingface" else (settings.GEMINI_API_KEY or settings.AI_PROVIDER_API_KEY)

    if provider_type == "huggingface" and api_key:
        return (
            HFVisionProvider(api_key), HFStoryProvider(api_key),
            HFImageProvider(api_key), HFModerationProvider(api_key)
        )
    if provider_type == "gemini" and api_key:
        return (
            GeminiVisionProvider(api_key), GeminiStoryProvider(api_key),
            GeminiImageProvider(api_key), GeminiModerationProvider(api_key)
        )
    return (MockVisionProvider(), MockStoryProvider(), MockImageProvider(), MockModerationProvider())

vision_provider, story_provider, image_provider, moderation_provider = get_ai_providers()
