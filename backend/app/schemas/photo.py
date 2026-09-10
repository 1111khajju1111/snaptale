from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class HumanDetectionResult(BaseModel):
    is_human_present: bool
    confidence: float
    detected_labels: List[str]

class HumanRejectionResponse(BaseModel):
    status: str = "rejected"
    reason: str = "human_detected"
    message: str = "🚫 SnapTale can't use photos containing people. Try photographing an animal, object, vehicle, food, or anything else!"
    action_button: str = "📸 Try Again"

class VisionAnalysisOutput(BaseModel):
    subject: str
    category: str # animal, object, vehicle, food, plant, etc.
    breed_or_type: Optional[str] = "unknown"
    color: str
    environment: str
    visible_objects: List[str]
    estimated_expression: str
    is_human_present: bool = False
