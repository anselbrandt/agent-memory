from __future__ import annotations as _annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator


class FacebookUser(BaseModel):
    """Facebook OAuth user response model."""
    
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    id: str = Field(..., description="Facebook user ID")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    email: Optional[str] = Field(None, description="User email address")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate user name."""
        if not v or v.isspace():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()


class FacebookPage(BaseModel):
    """Facebook page model."""
    
    id: str = Field(..., description="Facebook page ID")
    name: str = Field(..., description="Page name")
    access_token: str = Field(..., description="Page access token")
    category: str = Field(..., description="Page category")
    tasks: List[str] = Field(default_factory=list, description="Page tasks/permissions")


class InstagramBusinessAccount(BaseModel):
    """Instagram Business account model."""
    
    id: str = Field(..., description="Instagram Business account ID")
    username: str = Field(..., description="Instagram username")
    name: Optional[str] = Field(None, description="Instagram account name")
    profile_picture_url: Optional[str] = Field(None, description="Profile picture URL")
    followers_count: Optional[int] = Field(None, description="Number of followers")
    media_count: Optional[int] = Field(None, description="Number of media posts")


class UserData(BaseModel):
    """Complete user data from Facebook OAuth."""
    
    facebook_user: FacebookUser
    pages: List[FacebookPage]
    instagram_accounts: List[InstagramBusinessAccount]


class FacebookCredentialsBase(BaseModel):
    """Base Facebook credentials model."""
    
    facebook_user_id: str = Field(..., description="Facebook user ID")
    facebook_user_name: str = Field(..., description="Facebook user name")
    facebook_user_email: Optional[str] = Field(None, description="Facebook user email")


class FacebookCredentialsCreate(FacebookCredentialsBase):
    """Model for creating Facebook credentials."""
    
    user_id: str = Field(..., description="User ID")
    access_token: str = Field(..., description="Facebook access token")
    pages_data: Optional[str] = Field(None, description="JSON string of Facebook pages")
    instagram_accounts_data: Optional[str] = Field(
        None, description="JSON string of Instagram accounts"
    )


class FacebookCredentialsUpdate(BaseModel):
    """Model for updating Facebook credentials."""
    
    access_token: Optional[str] = Field(None, description="Facebook access token")
    pages_data: Optional[str] = Field(None, description="JSON string of Facebook pages")
    instagram_accounts_data: Optional[str] = Field(
        None, description="JSON string of Instagram accounts"
    )


class FacebookCredentialsResponse(FacebookCredentialsBase):
    """Model for Facebook credentials API responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Credentials ID")
    user_id: str = Field(..., description="User ID")
    access_token: str = Field(..., description="Facebook access token")
    pages_data: Optional[List] = Field(None, description="Facebook pages data")
    instagram_accounts_data: Optional[List] = Field(
        None, description="Instagram accounts data"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# API Request/Response models
class InstagramPostRequest(BaseModel):
    """Model for Instagram post requests."""
    
    instagram_account_id: str = Field(..., description="Instagram account ID")
    image_url: str = Field(..., description="Image URL")
    caption: str = Field(..., description="Post caption")
    access_token: str = Field(..., description="Access token")


class FacebookPagePostRequest(BaseModel):
    """Model for Facebook page post requests."""
    
    page_id: str = Field(..., description="Facebook page ID")
    image_url: Optional[str] = Field(None, description="Image URL")
    message: str = Field(..., description="Post message")
    access_token: str = Field(..., description="Access token")