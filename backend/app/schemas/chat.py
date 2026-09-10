from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ChatCreate(BaseModel):
    character_id: str
    title: str
    topic: Optional[str] = "Random Talks"
    universe_id: Optional[str] = None
    is_protected: bool = False # SnapTale+ private chat protection
    language: str = "te-en"

class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageResponse(BaseModel):
    id: str
    chat_id: str
    sender_type: str # user or character
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    id: str
    user_id: str
    character_id: str
    character_name: Optional[str] = None
    universe_id: Optional[str] = None
    title: str
    topic: Optional[str]
    is_protected: bool
    is_pinned: bool
    language: str
    last_message_at: datetime
    created_at: datetime
    messages: List[ChatMessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
