from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class EnrichInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=100)
    rating: int = Field(ge=1, le=5)
    price_gbp: float = Field(gt=0)
    availability_text: str = Field(min_length=1, max_length=200)


class Audience(str, Enum):
    children = "children"
    young_adult = "young_adult"
    general_adult = "general_adult"
    academic_or_specialist = "academic_or_specialist"


class QualityFlag(str, Enum):
    generic_title = "generic_title"
    title_genre_mismatch = "title_genre_mismatch"
    needs_review = "needs_review"


class EnrichOutput(BaseModel):
    audience: Audience
    confidence: float = Field(ge=0.0, le=1.0)
    blurb: str = Field(min_length=1, max_length=300)
    quality_flags: List[QualityFlag] = Field(default_factory=list)
    reason: str = Field(min_length=1, max_length=300)


STUB_OUTPUT = {
    "audience": "general_adult",
    "confidence": 0.5,
    "blurb": "Stub mode response -- no model was called.",
    "quality_flags": ["needs_review"],
    "reason": "LLM_STUB=1 is set; this is a hard-coded placeholder, not a real judgement.",
}
