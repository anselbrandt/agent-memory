from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, HttpUrl, ConfigDict, field_validator


class Provider(str, Enum):
    """OAuth provider enumeration."""

    GOOGLE = "google"
    FACEBOOK = "facebook"
    # Add more providers as needed
    # GITHUB = "github"
    # MICROSOFT = "microsoft"


class GoogleUser(BaseModel):
    """Google OAuth user response model."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    id: str = Field(..., description="Google user ID")
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    picture: Optional[HttpUrl] = Field(None, description="Profile picture URL")
    verified_email: bool = Field(..., description="Email verification status")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate user name."""
        if not v or v.isspace():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()


class FacebookUser(BaseModel):
    """Facebook OAuth user response model."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    id: str = Field(..., description="Facebook user ID")
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    picture: Optional[dict] = Field(None, description="Profile picture data")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate user name."""
        if not v or v.isspace():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()


class User(BaseModel):
    """User model for application use."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, use_enum_values=True
    )

    provider_id: str = Field(..., description="External provider user ID")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    email: EmailStr = Field(..., description="User email address")
    provider: Provider = Field(default=Provider.GOOGLE, description="OAuth provider")
    picture: Optional[HttpUrl] = Field(None, description="Profile picture URL")

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, v: str) -> str:
        """Validate provider ID."""
        if not v or v.isspace():
            raise ValueError("Provider ID cannot be empty")
        return v.strip()


class UserInDB(User):
    """User model with database fields."""

    created_at: datetime = Field(..., description="User creation timestamp")
    last_login: datetime = Field(..., description="Last login timestamp")


class Token(BaseModel):
    """OAuth token model."""

    model_config = ConfigDict(str_strip_whitespace=True)

    access_token: str = Field(..., min_length=1, description="OAuth access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token expiration in seconds")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    scope: Optional[str] = Field(None, description="Token scope")


class AuthRequest(BaseModel):
    """Authentication request model."""

    code: str = Field(..., min_length=1, description="OAuth authorization code")
    state: Optional[str] = Field(None, description="OAuth state parameter")


class AuthResponse(BaseModel):
    """Authentication response model."""

    authenticated: bool = Field(..., description="Authentication status")
    user: Optional[User] = Field(None, description="User information")
    message: Optional[str] = Field(None, description="Response message")


class SessionData(BaseModel):
    """Session data model for storage."""

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)

    id: str = Field(..., description="User external ID")
    provider_id: str = Field(..., description="Provider user ID")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="User name")
    picture: Optional[HttpUrl] = Field(None, description="Profile picture")
    provider: Provider = Field(..., description="Auth provider")
    created_at: datetime = Field(..., description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiration time")
