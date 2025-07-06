from __future__ import annotations as _annotations

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


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


# Additional models from db_models.py for API serialization
class UserBase(BaseModel):
    """Base user model for shared fields."""

    provider_id: str = Field(..., description="External provider user ID")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    picture: Optional[str] = Field(None, description="User profile picture URL")
    provider: str = Field(default="google", description="Authentication provider")


class UserResponse(UserBase):
    """Model for user API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal user ID")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: datetime = Field(..., description="Last login timestamp")


class SessionBase(BaseModel):
    """Base session model."""

    user_id: int = Field(..., description="User ID")
    provider_id: str = Field(..., description="Provider user ID")
    expires_at: datetime = Field(..., description="Session expiration time")


class SessionResponse(SessionBase):
    """Model for session API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Session ID")
    created_at: datetime = Field(..., description="Session creation timestamp")

    def is_expired(self) -> bool:
        """Check if session is expired."""
        from datetime import timezone
        return datetime.now(timezone.utc) > self.expires_at


class BusinessBase(BaseModel):
    """Base business model for shared fields."""

    name: str = Field(..., description="Business name")
    url: str = Field(..., description="Business URL")
    description: str = Field(..., description="Business description")


class BusinessResponse(BusinessBase):
    """Model for business API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Business ID")
    user_id: int = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Business creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Rebuild the models to resolve forward references
ChatMessage.model_rebuild()
User.model_rebuild()
UserResponse.model_rebuild()
SessionResponse.model_rebuild()
BusinessResponse.model_rebuild()
