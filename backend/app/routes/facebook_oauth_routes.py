from typing import Optional
from urllib.parse import urlencode
import json

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import httpx

from app.config import Settings
from app.db import Database
from app.models.facebook_models import (
    FacebookUser,
    FacebookPage,
    InstagramBusinessAccount,
    UserData,
    InstagramPostRequest,
    FacebookPagePostRequest,
    FacebookCredentialsResponse,
)
from app.services.auth_service import auth_service

settings = Settings()


async def get_db(request: Request) -> Database:
    """Get database connection from request state"""
    return request.state.db


def get_authenticated_user_id(request: Request) -> tuple[str, bool]:
    """Get the authenticated user ID from session.

    Returns:
        tuple: (user_id, is_authenticated) - user_id and whether they're actually authenticated
    """
    try:

        session_id = request.cookies.get("session_id")
        if session_id:
            user_data = auth_service.get_session_user(session_id)
            if user_data:
                return user_data.get("id"), True
    except ImportError:
        pass

    return None, False


# Facebook OAuth configuration
FACEBOOK_APP_ID = settings.facebook_app_id
FACEBOOK_APP_SECRET = settings.facebook_app_secret
FACEBOOK_REDIRECT_URI = f"{settings.host}/facebook/callback"

# We need to store the main access token for API calls
# This is different from our current implementation that stores empty string


# Facebook OAuth URLs
FACEBOOK_OAUTH_URL = "https://www.facebook.com/v23.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v23.0/oauth/access_token"
FACEBOOK_USER_URL = "https://graph.facebook.com/v23.0/me"
FACEBOOK_ACCOUNTS_URL = "https://graph.facebook.com/v23.0/me/accounts"
INSTAGRAM_BUSINESS_URL = "https://graph.facebook.com/v23.0/{}/instagram_accounts"

router = APIRouter(prefix="/facebook", tags=["facebook"])


# Response Models
class OAuthLoginResponse(BaseModel):
    """Response for OAuth login URL generation"""

    auth_url: str = Field(..., description="Facebook OAuth authorization URL")


class SaveCredentialsResponse(BaseModel):
    """Response for saving credentials"""

    message: str = Field(..., description="Success message")
    credentials: dict = Field(..., description="Saved credentials data")


class FacebookStatusResponse(BaseModel):
    """Response for Facebook connection status"""

    connected: bool = Field(..., description="Whether Facebook is connected")
    facebook_data: Optional[dict] = Field(
        None, description="Facebook data if connected"
    )


class DisconnectResponse(BaseModel):
    """Response for disconnecting Facebook"""

    message: str = Field(..., description="Success message")


class InstagramPostResponse(BaseModel):
    """Response for Instagram post creation"""

    success: bool = Field(..., description="Whether post was created successfully")
    creation_id: str = Field(..., description="Media creation ID")
    post_id: str = Field(..., description="Published post ID")
    message: str = Field(..., description="Success message")


class FacebookPostResponse(BaseModel):
    """Response for Facebook page post creation"""

    success: bool = Field(..., description="Whether post was created successfully")
    post_id: str = Field(..., description="Published post ID")
    message: str = Field(..., description="Success message")


# OAuth Endpoints
@router.get("/login", response_model=OAuthLoginResponse)
def facebook_login() -> OAuthLoginResponse:
    """Generate Facebook OAuth login URL for Instagram Business access"""

    # Check if Facebook credentials are configured
    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Facebook OAuth not configured. Please set FACEBOOK_APP_ID and FACEBOOK_APP_SECRET in environment variables.",
        )

    # Permissions needed for Instagram Business API and Facebook Page management
    permissions = [
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
        "pages_read_user_content",
        "instagram_basic",
        "instagram_manage_insights",
        "instagram_content_publish",
        "business_management",
    ]

    params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "scope": ",".join(permissions),
        "response_type": "code",
        "state": "instagram_business_auth",
    }

    auth_url = f"{FACEBOOK_OAUTH_URL}?{urlencode(params)}"
    return OAuthLoginResponse(auth_url=auth_url)


@router.get("/callback")
async def facebook_callback(
    code: str,
    state: Optional[str] = None,
    request: Request = None,
    database: Database = Depends(get_db),
):
    """Handle Facebook OAuth callback and get Instagram Business accounts"""

    # Verify state parameter for CSRF protection
    if state != "instagram_business_auth":
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Exchange authorization code for access token
    token_params = {
        "client_id": FACEBOOK_APP_ID,
        "client_secret": FACEBOOK_APP_SECRET,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        # Get access token
        token_response = await client.get(FACEBOOK_TOKEN_URL, params=token_params)

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to exchange code for token: {token_response.text}",
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="No access token received from Facebook",
            )

        # Get user information
        user_response = await client.get(
            f"{FACEBOOK_USER_URL}?fields=id,name,email&access_token={access_token}"
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get user info: {user_response.text}",
            )

        user_info = user_response.json()
        facebook_user = FacebookUser.model_validate(user_info)

        # Get user's Facebook pages
        pages_response = await client.get(
            f"{FACEBOOK_ACCOUNTS_URL}?fields=id,name,access_token,category,tasks&access_token={access_token}"
        )

        if pages_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get pages: {pages_response.text}",
            )

        pages_data = pages_response.json()
        pages = []
        instagram_accounts = []

        # Process each page and get associated Instagram Business accounts
        for page_data in pages_data.get("data", []):
            try:
                page = FacebookPage.model_validate(page_data)
                pages.append(page)

                # Get Instagram Business accounts for this page
                instagram_response = await client.get(
                    f"{INSTAGRAM_BUSINESS_URL.format(page.id)}?fields=id,username,name,profile_picture_url,followers_count,media_count&access_token={page.access_token}"
                )

                if instagram_response.status_code == 200:
                    instagram_data = instagram_response.json()
                    for ig_data in instagram_data.get("data", []):
                        try:
                            ig_account = InstagramBusinessAccount.model_validate(
                                ig_data
                            )
                            instagram_accounts.append(ig_account)
                        except Exception as e:
                            print(f"Error parsing Instagram account: {e}")

            except Exception as e:
                print(f"Error processing page: {e}")
                continue

        # Create user data object with access token
        user_data = UserData(
            facebook_user=facebook_user,
            pages=pages,
            instagram_accounts=instagram_accounts,
        )

        # Store the access token in a way we can retrieve it later
        # We'll need to modify the save endpoint to handle this
        user_data_with_token = {
            **user_data.model_dump(),
            "access_token": access_token,  # Store the main access token
        }

        # Return HTML response that sends user data to parent window
        return HTMLResponse(
            content=f"""
        <html>
            <body>
                <script>
                    const userData = {json.dumps(user_data_with_token)};
                    
                    window.opener.postMessage({{
                        type: 'OAUTH_SUCCESS',
                        user: userData
                    }}, '{settings.frontend_url}');
                    
                    window.close();
                </script>
                <p>Login successful! This window should close automatically.</p>
            </body>
        </html>
        """
        )


@router.post("/save-credentials", response_model=SaveCredentialsResponse)
async def save_facebook_credentials(
    request: Request, database: Database = Depends(get_db)
) -> SaveCredentialsResponse:
    """Save Facebook credentials to database for authenticated user"""

    user_id, is_authenticated = get_authenticated_user_id(request)

    if not is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # Get raw JSON data that includes access_token
        body = await request.json()

        facebook_user = body.get("facebook_user", {})
        access_token = body.get("access_token", "")
        pages = body.get("pages", [])
        instagram_accounts = body.get("instagram_accounts", [])

        # Save credentials to database with actual access token
        credentials_data = await database.create_or_update_facebook_credentials(
            user_id=user_id,
            facebook_user_id=facebook_user.get("id"),
            facebook_user_name=facebook_user.get("name"),
            facebook_user_email=facebook_user.get("email"),
            access_token=access_token,  # Store the actual access token
            pages_data=json.dumps(pages),
            instagram_accounts_data=json.dumps(instagram_accounts),
        )

        return SaveCredentialsResponse(
            message="Facebook credentials saved successfully",
            credentials=credentials_data.model_dump(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save credentials: {str(e)}"
        )


@router.get("/credentials", response_model=Optional[FacebookCredentialsResponse])
async def get_facebook_credentials(
    request: Request, database: Database = Depends(get_db)
) -> Optional[FacebookCredentialsResponse]:
    """Get Facebook credentials for authenticated user"""

    user_id, is_authenticated = get_authenticated_user_id(request)

    if not is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")

    credentials = await database.get_facebook_credentials(user_id)
    return credentials


@router.delete("/credentials", response_model=DisconnectResponse)
async def delete_facebook_credentials(
    request: Request, database: Database = Depends(get_db)
) -> DisconnectResponse:
    """Delete Facebook credentials for authenticated user"""

    user_id, is_authenticated = get_authenticated_user_id(request)

    if not is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")

    success = await database.delete_facebook_credentials(user_id)
    if success:
        return DisconnectResponse(message="Facebook credentials deleted successfully")
    else:
        raise HTTPException(status_code=404, detail="No Facebook credentials found")


# Add the reference app endpoints that are missing
@router.post("/save", response_model=SaveCredentialsResponse)
async def save_facebook_data(
    request: Request, database: Database = Depends(get_db)
) -> SaveCredentialsResponse:
    """Save Facebook data - alternative endpoint matching reference app"""
    # This is the same as save-credentials but with different URL
    return await save_facebook_credentials(request, database)


@router.get("/status", response_model=FacebookStatusResponse)
async def get_facebook_status(
    request: Request, database: Database = Depends(get_db)
) -> FacebookStatusResponse:
    """Get Facebook connection status and data"""

    user_id, is_authenticated = get_authenticated_user_id(request)

    if not is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")

    credentials = await database.get_facebook_credentials(user_id)

    if not credentials:
        return FacebookStatusResponse(connected=False)

    # Build facebook_data from the Pydantic model
    facebook_data = {
        "facebook_user": {
            "id": credentials.facebook_user_id,
            "name": credentials.facebook_user_name,
            "email": credentials.facebook_user_email,
        },
        "pages": credentials.pages_data or [],
        "instagram_accounts": credentials.instagram_accounts_data or [],
    }

    return FacebookStatusResponse(connected=True, facebook_data=facebook_data)


@router.post("/disconnect", response_model=DisconnectResponse)
async def disconnect_facebook(
    request: Request, database: Database = Depends(get_db)
) -> DisconnectResponse:
    """Disconnect Facebook account"""

    user_id, is_authenticated = get_authenticated_user_id(request)

    if not is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")

    success = await database.delete_facebook_credentials(user_id)
    if success:
        return DisconnectResponse(message="Facebook account disconnected successfully")
    else:
        raise HTTPException(status_code=404, detail="No Facebook credentials found")


# Instagram API endpoints
@router.get("/instagram/insights/{instagram_account_id}")
async def get_instagram_insights(instagram_account_id: str, access_token: str):
    """Get Instagram Business account insights"""
    async with httpx.AsyncClient() as client:
        insights_response = await client.get(
            f"https://graph.facebook.com/v23.0/{instagram_account_id}/insights"
            f"?metric=accounts_engaged,reach,profile_views&period=day&metric_type=total_value&access_token={access_token}"
        )

        if insights_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get insights: {insights_response.text}",
            )

        return insights_response.json()


@router.get("/instagram/media/{instagram_account_id}")
async def get_instagram_media(instagram_account_id: str, access_token: str):
    """Get Instagram Business account media"""
    async with httpx.AsyncClient() as client:
        media_response = await client.get(
            f"https://graph.facebook.com/v23.0/{instagram_account_id}/media"
            f"?fields=id,caption,media_type,media_url,thumbnail_url,timestamp,like_count,comments_count&access_token={access_token}"
        )

        if media_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get media: {media_response.text}",
            )

        return media_response.json()


@router.post("/instagram/post", response_model=InstagramPostResponse)
async def create_instagram_post(
    post_request: InstagramPostRequest,
) -> InstagramPostResponse:
    """Create a new Instagram post"""
    instagram_id = post_request.instagram_account_id
    access_token = post_request.access_token
    image_url = post_request.image_url
    caption = post_request.caption

    create_url = f"https://graph.facebook.com/v23.0/{instagram_id}/media"
    publish_url = f"https://graph.facebook.com/v23.0/{instagram_id}/media_publish"

    create_params = {
        "access_token": access_token,
        "image_url": image_url,
        "caption": caption,
        "format": "json",
    }

    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Create media object
            create_response = await client.post(
                create_url, params=create_params, timeout=10.0
            )
            create_response.raise_for_status()
            create_data = create_response.json()

            creation_id = create_data.get("id")
            if not creation_id:
                raise HTTPException(
                    status_code=400,
                    detail="No creation ID returned from Instagram API",
                )

            # Step 2: Publish media object
            publish_params = {
                "access_token": access_token,
                "creation_id": creation_id,
                "format": "json",
            }

            publish_response = await client.post(
                publish_url, params=publish_params, timeout=10.0
            )
            publish_response.raise_for_status()
            publish_data = publish_response.json()

            return InstagramPostResponse(
                success=True,
                creation_id=creation_id,
                post_id=publish_data.get("id"),
                message="Post created successfully",
            )

        except httpx.HTTPStatusError as e:
            error_detail = (
                f"Instagram API error: {e.response.status_code} - {e.response.text}"
            )
            raise HTTPException(status_code=400, detail=error_detail)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}",
            )


# Facebook Page API endpoints
@router.get("/facebook/insights/{page_id}")
async def get_facebook_page_insights(page_id: str, access_token: str):
    """Get Facebook page insights"""
    async with httpx.AsyncClient() as client:
        # Try basic page info first, then insights if page has enough data
        page_response = await client.get(
            f"https://graph.facebook.com/v23.0/{page_id}?fields=name,fan_count,followers_count&access_token={access_token}"
        )

        if page_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get page info: {page_response.text}",
            )

        page_data = page_response.json()

        # Try to get insights (works only for pages with 100+ likes)
        insights_response = await client.get(
            f"https://graph.facebook.com/v23.0/{page_id}/insights"
            f"?metric=page_fan_adds,page_views_total,page_post_engagements&date_preset=today&access_token={access_token}"
        )

        if insights_response.status_code == 200:
            # Return actual insights data if available
            insights_data = insights_response.json()
            print(f"Facebook insights API success: {insights_data}")
            return insights_data
        else:
            # Return basic page data if insights are not available (e.g., page has <100 likes)
            print(
                f"Facebook insights API failed: {insights_response.status_code} - {insights_response.text}"
            )
            print(f"Page data: {page_data}")
            fallback_data = {
                "data": [
                    {
                        "name": "page_fans",
                        "title": "Page Fans",
                        "total_value": {"value": page_data.get("fan_count", 0)},
                        "description": "Total number of people who like this page",
                    },
                    {
                        "name": "page_followers",
                        "title": "Page Followers",
                        "total_value": {"value": page_data.get("followers_count", 0)},
                        "description": "Total number of people following this page",
                    },
                ],
                "note": "Limited insights available. Full insights require 100+ page likes.",
            }
            print(f"Returning fallback data: {fallback_data}")
            return fallback_data


@router.get("/facebook/posts/{page_id}")
async def get_facebook_page_posts(page_id: str, access_token: str):
    """Get Facebook page posts"""
    async with httpx.AsyncClient() as client:
        posts_response = await client.get(
            f"https://graph.facebook.com/v23.0/{page_id}/posts"
            f"?fields=id,message,created_time,full_picture,likes.summary(true),comments.summary(true),shares&limit=10&access_token={access_token}"
        )

        if posts_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get page posts: {posts_response.text}",
            )

        return posts_response.json()


@router.post("/facebook/post", response_model=FacebookPostResponse)
async def create_facebook_page_post(
    post_request: FacebookPagePostRequest,
) -> FacebookPostResponse:
    """Create a new Facebook page post"""
    page_id = post_request.page_id
    access_token = post_request.access_token
    image_url = post_request.image_url
    message = post_request.message

    # Choose endpoint based on whether there's an image
    if image_url and image_url.strip():
        # Post with image
        post_url = f"https://graph.facebook.com/v23.0/{page_id}/photos"
        post_params = {
            "access_token": access_token,
            "url": image_url,
            "message": message,
            "format": "json",
        }
    else:
        # Text-only post
        post_url = f"https://graph.facebook.com/v23.0/{page_id}/feed"
        post_params = {
            "access_token": access_token,
            "message": message,
            "format": "json",
        }

    async with httpx.AsyncClient() as client:
        try:
            post_response = await client.post(
                post_url, params=post_params, timeout=10.0
            )
            post_response.raise_for_status()
            post_data = post_response.json()

            return FacebookPostResponse(
                success=True,
                post_id=post_data.get("id"),
                message="Facebook post created successfully",
            )

        except httpx.HTTPStatusError as e:
            error_detail = (
                f"Facebook API error: {e.response.status_code} - {e.response.text}"
            )
            raise HTTPException(status_code=400, detail=error_detail)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}",
            )
