"""
Single source of truth for all request/response models.

The frontend's TypeScript types in `frontend/src/types/index.ts` mirror this
file field-for-field. If you change something here, update that file too.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

ResourceType = Literal["video", "playlist"]
Role = Literal["user", "assistant"]


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: Role
    content: str


class VideoMeta(BaseModel):
    video_id: str
    title: Optional[str] = None
    channel: Optional[str] = None
    duration_seconds: Optional[float] = None
    thumbnail_url: Optional[str] = None
    transcript_available: bool
    chunk_count: int = 0
    error: Optional[str] = None  # populated if this specific video failed (e.g. no captions)


class ImportantMoment(BaseModel):
    video_id: str
    time: float
    label: str


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    resource: str = Field(..., description="A YouTube video URL, playlist URL, or raw ID")

    @field_validator("resource")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Please paste a YouTube video or playlist URL.")
        return v


class AnalyzeResponse(BaseModel):
    resource_id: str
    resource_type: ResourceType
    videos: List[VideoMeta]
    total_chunks: int
    summary: Optional[str] = None
    key_takeaways: List[str] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    important_moments: List[ImportantMoment] = Field(default_factory=list)
    status: Literal["ready", "partial"] = "ready"
    warnings: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    resource_id: str
    question: str = Field(..., min_length=1, max_length=2000)
    history: Optional[List[Message]] = None
    current_time: Optional[float] = Field(
        default=None,
        description="Playback position (seconds) the user was at when asking, for 'ask about this moment'.",
    )
    video_id: Optional[str] = Field(
        default=None,
        description="Restrict retrieval to a single video within a playlist resource.",
    )

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty.")
        return v


class SourceChunk(BaseModel):
    video_id: str
    start: float
    end: float
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    resource_id: str


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    message: str
    code: str
