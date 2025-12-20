# -*- coding: utf-8 -*-
"""Pydantic models for Chat."""

from datetime import datetime, UTC
from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


class GroundingSource(BaseModel):
    """Source information for grounded response."""

    source: str = Field(..., description="Source file name")
    page: int | None = Field(default=None, description="Page number if available")
    content: str = Field(default="", description="Relevant content snippet")


class ChatRequest(BaseModel):
    """Request model for chat query."""

    query: str = Field(..., min_length=1, max_length=2000, description="User's question")


class ChatResponse(BaseModel):
    """Response model for chat."""

    query: str = Field(..., description="Original query")
    response: str = Field(..., description="Generated response")
    sources: list[GroundingSource] = Field(default_factory=list, description="Grounding sources")
    created_at: datetime = Field(default_factory=_utc_now)


class ChatMessage(BaseModel):
    """A single chat message in history."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    sources: list[GroundingSource] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)


class ChatHistory(BaseModel):
    """Chat history for a channel."""

    channel_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    total: int = Field(default=0)
