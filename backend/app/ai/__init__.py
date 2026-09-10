from app.core.config import settings
from app.ai.base import (
    BaseVisionProvider, BaseStoryProvider, BaseImageProvider, BaseModerationProvider
)
from app.ai.mock_provider import (
    MockVisionProvider, MockStoryProvider, MockImageProvider, MockModerationProvider
)
from app.ai.gemini_provider import GeminiVisionProvider, GeminiStoryProvider

def get_ai_providers():
    provider_type = settings.AI_PROVIDER.lower()
    api_key = settings.GEMINI_API_KEY or settings.AI_PROVIDER_API_KEY

    if provider_type == "gemini" and api_key:
        vision_provider = GeminiVisionProvider(api_key=api_key)
        story_provider = GeminiStoryProvider(api_key=api_key)
    else:
        vision_provider = MockVisionProvider()
        story_provider = MockStoryProvider()

    image_provider = MockImageProvider()
    moderation_provider = MockModerationProvider()

    return vision_provider, story_provider, image_provider, moderation_provider

vision_provider, story_provider, image_provider, moderation_provider = get_ai_providers()
