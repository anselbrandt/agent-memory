from typing import Optional
from urllib.parse import urlencode

from fastapi import HTTPException, status
import asyncpg
import httpx

from app.config import Settings
from app.auth_models import GoogleUser, User, Provider
from app.session_service import session_service
from app.user_service import user_service

settings = Settings()


class AuthService:
    def __init__(self):
        self.google_client_id = settings.google_client_id
        self.google_client_secret = settings.google_client_secret
        self.host = settings.host
        self.google_redirect_uri = f"{self.host}/auth/google/callback"

        # Google OAuth URLs
        self.google_oauth_url = settings.google_oauth_url
        self.google_token_url = settings.google_token_url
        self.google_user_url = settings.google_user_url

        # JWT settings
        self.jwt_secret = settings.jwt_secret_key
        self.jwt_algorithm = settings.jwt_algorithm

        # Google OAuth parameters
        self.google_params = {
            "response_type": "code",
            "client_id": self.google_client_id,
            "redirect_uri": self.google_redirect_uri,
            "scope": "openid profile email",
            "access_type": "offline",
        }

        self.google_login_link = (
            f"{self.google_oauth_url}?{urlencode(self.google_params)}"
        )

    def get_google_login_url(self) -> str:
        """Get Google OAuth login URL"""
        return self.google_login_link

    async def get_google_user(self, code: str, db: asyncpg.Connection) -> User:
        """Exchange authorization code for user information"""
        # Exchange code for access token
        data = {
            "code": code,
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
            "redirect_uri": self.google_redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            # Get access token
            token_response = await client.post(self.google_token_url, data=data)

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code for token: {token_response.text}",
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from Google",
                )

            # Get user information
            user_response = await client.get(
                self.google_user_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to get user info from Google: {user_response.text}",
                )

            user_info = user_response.json()

        # Validate Google user data
        try:
            google_user = GoogleUser.model_validate(user_info)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user data from Google: {str(e)}",
            )

        # Create our User object
        user = User(
            provider_id=google_user.id,
            name=google_user.name,
            email=google_user.email,
            provider=Provider.GOOGLE,
            picture=google_user.picture,
        )

        # Save/update user in database
        await user_service.create_or_update_user(user, db)

        return user

    def create_session(self, user: User) -> str:
        """Create a session for the user"""
        user_data = {
            "id": user.provider_id,  # Use provider_id as external ID
            "provider_id": user.provider_id,
            "email": user.email,
            "name": user.name,
            "picture": str(user.picture) if user.picture else None,
            "provider": user.provider,  # Already a string due to use_enum_values=True
        }

        return session_service.create_session(user_data)

    def get_session_user(self, session_id: str) -> Optional[dict]:
        """Get user data from session"""
        return session_service.get_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        return session_service.delete_session(session_id)

    def refresh_session(self, session_id: str) -> bool:
        """Refresh session expiration"""
        return session_service.refresh_session(session_id)


# Global instance
auth_service = AuthService()
