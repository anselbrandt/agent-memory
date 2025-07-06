from __future__ import annotations as _annotations

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

from pydantic import BaseModel


class MessagePart(BaseModel):
    """Individual part of a message."""

    content: str
    timestamp: Optional[datetime] = None
    part_kind: str


class UsageDetails(BaseModel):
    """Token usage details."""

    accepted_prediction_tokens: int = 0
    audio_tokens: int = 0
    reasoning_tokens: int = 0
    rejected_prediction_tokens: int = 0
    cached_tokens: int = 0


class Usage(BaseModel):
    """Usage information for API calls."""

    requests: int
    request_tokens: int
    response_tokens: int
    total_tokens: int
    details: UsageDetails


class ChatMessage(BaseModel):
    """Individual message in a conversation."""

    parts: List[MessagePart]
    instructions: Optional[str] = None
    kind: Literal["request", "response"]
    usage: Optional[Usage] = None
    model_name: Optional[str] = None
    timestamp: Optional[datetime] = None
    vendor_details: Optional[Dict[str, Any]] = None
    vendor_id: Optional[str] = None


class User(BaseModel):
    """User model for representing user data."""

    id: str
    username: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Rebuild the models to resolve forward references
ChatMessage.model_rebuild()
User.model_rebuild()
