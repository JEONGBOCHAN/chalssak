# -*- coding: utf-8 -*-
"""Chat API endpoints."""

from datetime import datetime, UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistory,
    ChatMessage,
    GroundingSource,
)
from src.services.gemini import GeminiService, get_gemini_service

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory chat history storage (for simplicity)
# In production, use a database
_chat_histories: dict[str, list[ChatMessage]] = {}


@router.post(
    "",
    response_model=ChatResponse,
    summary="Send a chat message",
)
def send_message(
    channel_id: Annotated[str, Query(description="Channel ID to query")],
    request: ChatRequest,
    gemini: Annotated[GeminiService, Depends(get_gemini_service)],
) -> ChatResponse:
    """Send a question and get an AI-generated answer.

    The response includes grounding sources from the documents in the channel.
    """
    # Validate channel exists
    store = gemini.get_store(channel_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel not found: {channel_id}",
        )

    # Search and generate answer
    result = gemini.search_and_answer(channel_id, request.query)

    if "error" in result and result["error"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {result['error']}",
        )

    # Convert sources to GroundingSource models
    sources = [
        GroundingSource(
            source=s.get("source", "unknown"),
            content=s.get("content", ""),
        )
        for s in result.get("sources", [])
    ]

    response = ChatResponse(
        query=request.query,
        response=result.get("response", ""),
        sources=sources,
        created_at=datetime.now(UTC),
    )

    # Store in history
    if channel_id not in _chat_histories:
        _chat_histories[channel_id] = []

    # Add user message
    _chat_histories[channel_id].append(
        ChatMessage(
            role="user",
            content=request.query,
            sources=[],
            created_at=datetime.now(UTC),
        )
    )

    # Add assistant message
    _chat_histories[channel_id].append(
        ChatMessage(
            role="assistant",
            content=response.response,
            sources=sources,
            created_at=datetime.now(UTC),
        )
    )

    return response


@router.get(
    "/history",
    response_model=ChatHistory,
    summary="Get chat history",
)
def get_chat_history(
    channel_id: Annotated[str, Query(description="Channel ID")],
    gemini: Annotated[GeminiService, Depends(get_gemini_service)],
) -> ChatHistory:
    """Get the chat history for a channel."""
    # Validate channel exists
    store = gemini.get_store(channel_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel not found: {channel_id}",
        )

    messages = _chat_histories.get(channel_id, [])

    return ChatHistory(
        channel_id=channel_id,
        messages=messages,
        total=len(messages),
    )


@router.delete(
    "/history",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear chat history",
)
def clear_chat_history(
    channel_id: Annotated[str, Query(description="Channel ID")],
    gemini: Annotated[GeminiService, Depends(get_gemini_service)],
):
    """Clear the chat history for a channel."""
    # Validate channel exists
    store = gemini.get_store(channel_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel not found: {channel_id}",
        )

    if channel_id in _chat_histories:
        del _chat_histories[channel_id]

    return None
