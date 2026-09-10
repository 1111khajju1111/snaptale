from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from app.schemas.photo import HumanDetectionResult, VisionAnalysisOutput
from app.schemas.character import CharacterDNA
from app.schemas.story import StoryDiceRoll

class BaseVisionProvider(ABC):
    @abstractmethod
    async def detect_human(self, image_bytes: bytes, filename: str = "") -> HumanDetectionResult:
        """Strict server-side human detection. Must return whether a human is present."""
        pass

    @abstractmethod
    async def analyze_non_human(self, image_bytes: bytes) -> VisionAnalysisOutput:
        """Extract visible non-human attributes (subject, breed/type, color, expression, etc.)."""
        pass

class BaseStoryProvider(ABC):
    @abstractmethod
    async def generate_character_dna(self, vision: VisionAnalysisOutput, preferred_language: str = "te-en") -> CharacterDNA:
        """Create structured Character DNA based on visual non-human analysis."""
        pass

    @abstractmethod
    async def generate_story(
        self,
        character_dna: CharacterDNA,
        dice: StoryDiceRoll,
        mode: str = "snaptale", # "snaptale" vs "snapplus"
        language: str = "te-en",
        custom_prompt: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate full story with title, narrative content, and punchline."""
        pass

    @abstractmethod
    async def mutate_story(
        self,
        original_story_content: str,
        character_dna: CharacterDNA,
        mutation_type: str,
        mode: str = "snaptale",
        language: str = "te-en",
        custom_instruction: Optional[str] = None
    ) -> Dict[str, str]:
        """Create a non-destructive story branch mutation."""
        pass

    @abstractmethod
    async def what_if_story(
        self,
        original_story_content: str,
        character_dna: CharacterDNA,
        scenario: str,
        mode: str = "snaptale",
        language: str = "te-en"
    ) -> Dict[str, str]:
        """Generate What If alternate reality branch."""
        pass

    @abstractmethod
    async def continue_story(
        self,
        previous_story_content: str,
        character_dna: CharacterDNA,
        direction: Optional[str] = None,
        mode: str = "snaptale",
        language: str = "te-en"
    ) -> Dict[str, str]:
        """Generate next chapter in storyline without overwriting original."""
        pass

    @abstractmethod
    async def chat_response(
        self,
        character_dna: CharacterDNA,
        chat_history: List[Dict[str, str]],
        message: str,
        universe_context: Optional[str] = None,
        is_snapplus: bool = False
    ) -> str:
        """Generate in-character response preserving Character DNA and tone."""
        pass

class BaseImageProvider(ABC):
    @abstractmethod
    async def generate_story_image(
        self,
        character_dna: CharacterDNA,
        story_title: str,
        scene_summary: str,
        mode: str = "snaptale"
    ) -> str:
        """Generate 1 image per story preserving non-human character visual identity."""
        pass

class BaseModerationProvider(ABC):
    @abstractmethod
    async def check_content_safety(self, text: str, is_snapplus: bool = False) -> Dict[str, Any]:
        """Block disallowed harmful content while allowing dark comedy in SnapTale+."""
        pass
