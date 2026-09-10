from pydantic import BaseModel
from typing import List, Optional

class SnapFactItem(BaseModel):
    category: str
    fact: str
    source_reference: Optional[str] = "SnapFacts Knowledge Base"

class SnapFactsResponse(BaseModel):
    subject: str
    reality_facts: List[SnapFactItem]
    fictional_comparison: str
    label_reality: str = "🔵 REALITY — SnapFacts"
    label_imagination: str = "🟣 IMAGINATION — SnapTale"
