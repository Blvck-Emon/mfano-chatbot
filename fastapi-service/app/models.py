from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    session_id: Optional[str] = Field(
        default=None, description="UUID from a previous response; omit to start a new session"
    )
    message: str = Field(..., min_length=1, max_length=1000)


class SourceRef(BaseModel):
    doc_id: int
    category: Optional[str] = None
    source_url: Optional[str] = None


class ChatQueryResponse(BaseModel):
    session_id: str
    reply: str
    is_fallback: bool
    sources: List[SourceRef] = []


class DashboardStats(BaseModel):
    date_range_days: int
    total_conversations: int
    total_messages: int
    fallback_rate: float
    resolution_rate: float
    top_unanswered: List[str] = []
