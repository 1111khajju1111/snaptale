from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

class StoryDiceRoll(BaseModel):
    genre: str
    setting: str
    goal: str
    conflict: Optional[str] = None
    twist: str
    chaos_mode: bool = False

class StoryCreate(BaseModel):
    character_id: Optional[str] = None
    experience_mode: str = "snaptale" # snaptale or snapplus
    language: str = "te-en"
    dice: Optional[StoryDiceRoll] = None
    custom_prompt: Optional[str] = None
    parent_story_id: Optional[str] = None
    idempotency_key: Optional[str] = None

class StoryMutationRequest(BaseModel):
    mutation_type: str # funny, horror, dark, weird, space, royal, mysterious, happy_ending, evil_hero
    custom_instruction: Optional[str] = None

class WhatIfRequest(BaseModel):
    scenario: str # "What if Dogesh Bhai ruled Mars?"

class ContinueStoryRequest(BaseModel):
    direction: Optional[str] = None

class StoryResponse(BaseModel):
    id: str
    user_id: str
    character_id: str
    character_name: Optional[str] = None
    universe_id: Optional[str] = None
    title: str
    content: str
    punchline: Optional[str]
    experience_mode: str
    language: str
    dice_roll: Optional[Dict[str, Any]]
    generated_image_url: Optional[str]
    privacy: str
    moderation_status: str
    like_count: int
    remix_count: int
    is_pinned: bool
    created_at: datetime

    class Config:
        from_attributes = True

class LoreTreeNode(BaseModel):
    id: str
    title: str
    character_name: str
    mutation_type: Optional[str]
    created_at: datetime
    parent_id: Optional[str]
    children_ids: List[str] = Field(default_factory=list)
