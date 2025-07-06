from fastapi import APIRouter, HTTPException, status, Request, Response, Depends
from fastapi.responses import RedirectResponse

from app.config import Settings
from app.auth_models import AuthRequest, AuthResponse
from app.auth_service import auth_service
from app.db import Database

settings = Settings()
auth_router = APIRouter(prefix="/auth", tags=["authentication"])


async def get_db_connection(request: Request):
    """Get database connection from request state"""
    database: Database = request.state.db
    async with database.pool.acquire() as connection:
        yield connection


@auth_router.get("/google")
async def get_google_auth_url():
    """Get Google OAuth login URL as JSON"""
    google_login_url = auth_service.get_google_login_url()
    return {"auth_url": google_login_url}


@auth_router.get("/google/login")
async def google_login():
    """Redirect to Google OAuth login"""
    google_login_url = auth_service.get_google_login_url()
    return RedirectResponse(url=google_login_url, status_code=status.HTTP_302_FOUND)


@auth_router.get("/google/callback")
async def google_callback(
    code: str, response: Response = Response(), db=Depends(get_db_connection)
):
    """Handle Google OAuth callback"""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required",
        )

    try:
        # Exchange code for user information
        user = await auth_service.get_google_user(code, db)

        # Create session
        session_id = auth_service.create_session(user)

        # Set session cookie - configured for localhost cross-port access
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=False,  # Allow JavaScript access for debugging
            secure=False,  # Must be False for localhost HTTP
            samesite="lax",  # Allows cross-port same-site requests
            domain=None,  # No domain restriction for localhost
            path="/",  # Ensure cookie is sent for all paths
            max_age=settings.session_expires_days * 24 * 60 * 60,
        )

        # Redirect to frontend with session ID as URL parameter (temporary)
        # The frontend will then set this as a cookie on the correct domain
        return RedirectResponse(
            url=f"{settings.frontend_url}/?session_id={session_id}",
            status_code=status.HTTP_302_FOUND,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}",
        )


@auth_router.post("/login", response_model=AuthResponse)
async def login(
    auth_request: AuthRequest, response: Response, db=Depends(get_db_connection)
):
    """Manual login endpoint for testing"""
    try:
        user = await auth_service.get_google_user(auth_request.code, db)
        session_id = auth_service.create_session(user)

        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=False,  # Allow JavaScript access for debugging
            secure=False,  # Must be False for localhost HTTP
            samesite="lax",  # Allows cross-port same-site requests
            domain=None,  # No domain restriction for localhost
            path="/",  # Ensure cookie is sent for all paths
            max_age=settings.session_expires_days * 24 * 60 * 60,
        )

        return AuthResponse(authenticated=True, user=user, message="Login successful")
    except Exception as e:
        return AuthResponse(
            authenticated=False, user=None, message=f"Login failed: {str(e)}"
        )


@auth_router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout endpoint"""
    session_id = request.cookies.get("session_id")

    if session_id:
        auth_service.delete_session(session_id)

    response.delete_cookie(key="session_id")

    return {"message": "Logged out successfully"}


@auth_router.get("/status")
async def get_auth_status(request: Request):
    """Check authentication status"""
    session_id = request.cookies.get("session_id")

    if not session_id:
        return {"authenticated": False}

    user_data = auth_service.get_session_user(session_id)

    if not user_data:
        return {"authenticated": False}

    return {
        "authenticated": True,
        "user": {
            "id": user_data.get("id"),
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "picture": user_data.get("picture"),
            "provider": user_data.get("provider"),
        },
    }


@auth_router.get("/me")
async def get_current_user(request: Request):
    """Get current authenticated user"""
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user_data = auth_service.get_session_user(session_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        )

    return {
        "id": user_data.get("id"),
        "email": user_data.get("email"),
        "name": user_data.get("name"),
        "picture": user_data.get("picture"),
        "provider": user_data.get("provider"),
    }


@auth_router.post("/refresh")
async def refresh_session(request: Request):
    """Refresh session expiration"""
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    success = auth_service.refresh_session(session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session refresh failed"
        )

    return {"message": "Session refreshed successfully"}
