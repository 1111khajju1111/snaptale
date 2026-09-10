from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

class SpeechStyle(BaseModel):
    language: str = "te-en" # en, te, te-en
    register: str = "casual" # casual, naatu, formal
    slang: str = "naatu"
    code_switching: float = 0.35

class CharacterDNA(BaseModel):
    name: str
    species_or_object: str
    personality: List[str]
    secret: str
    fear: str
    origin: str
    occupation: str
    abilities: List[str]
    weaknesses: List[str]
    appearance: Dict[str, str] = Field(default_factory=dict)
    comedy_archetype: str # e.g. "overconfident_hero", "deadpan_savage"
    humor_style: List[str] = Field(default_factory=lambda: ["sarcasm", "absurdity"])
    speech_style: SpeechStyle = Field(default_factory=SpeechStyle)
    sarcasm_level: float = 0.8
    meme_level: float = 0.75
    dramatic_level: float = 0.85
    telugu_slang_level: float = 0.7
    english_mix: float = 0.3
    punchline_frequency: float = 0.85

class CharacterCreate(BaseModel):
    name: str
    species_or_object: str
    dna: CharacterDNA
    universe_id: Optional[str] = None
    photo_url: Optional[str] = None
    origin_story: Optional[str] = None

class CharacterResponse(BaseModel):
    id: str
    user_id: str
    universe_id: Optional[str]
    name: str
    species_or_object: str
    photo_url: Optional[str]
    dna: CharacterDNA
    origin_story: Optional[str]
    story_count: int
    chat_count: int
    is_pinned: bool
    last_activity_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
