from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class GenerationJobResponse(BaseModel):
    job_id: str
    status: str # queued, processing, completed, failed
    stage: str # vision, character, story, image, moderation
    progress: int # 0 to 100
    story_id: Optional[str] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

class WebSocketJobPayload(BaseModel):
    job_id: str
    status: str
    stage: str
    progress: int
    message: str
    story_id: Optional[str] = None
