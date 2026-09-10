from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LibrarySearchItem(BaseModel):
    id: str
    type: str # character, story, chat, universe, mutation
    title: str
    subtitle: Optional[str] = None
    preview_text: Optional[str] = None
    image_url: Optional[str] = None
    is_pinned: bool = False
    created_at: datetime

class LibrarySearchResult(BaseModel):
    query: str
    total_count: int
    page: int
    results: List[LibrarySearchItem] = Field(default_factory=list)
