from __future__ import annotations as _annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid

from dotenv import load_dotenv

# Load environment variables first, before any other imports
load_dotenv()

from fastapi import Depends, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import fastapi
import logfire

from app.config import Settings
from app.db import Database, ChatUser
from app.routes.auth_routes import auth_router
from app.services.auth_service import auth_service
from app.models.models import BusinessBase, BusinessResponse
from app.routes.facebook_oauth_routes import router as facebook_router
from app.routes.upload_routes import router as upload_router
from app.routes.chat_routes import router as chat_router

settings = Settings()

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


THIS_DIR = Path(__file__).parent

# Anonymous user management
ANONYMOUS_USER_COOKIE = "anonymous_user_id"


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    async with Database.connect() as db:
        yield {"db": db}


app = fastapi.FastAPI(lifespan=lifespan)
# logfire.instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(facebook_router)
app.include_router(upload_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {"message": f"Visit {settings.frontend_url}"}


async def get_db(request: Request) -> Database:
    return request.state.db


def get_authenticated_user_id(request: Request) -> tuple[str, bool]:
    """Get the authenticated user ID from session.

    Returns:
        tuple: (user_id, is_authenticated) - user_id and whether they're actually authenticated
    """
    try:
        from app.services.auth_service import auth_service

        session_id = request.cookies.get("session_id")
        if session_id:
            user_data = auth_service.get_session_user(session_id)
            if user_data:
                return user_data.get("id"), True
    except ImportError:
        pass

    return None, False


def get_or_create_anonymous_user_id(request: Request) -> str:
    """Get or create an anonymous user ID using cookies."""
    # Check if user has an existing anonymous ID cookie
    anonymous_id = request.cookies.get(ANONYMOUS_USER_COOKIE)
    if anonymous_id:
        return anonymous_id

    # Generate a new anonymous user ID
    return f"anon_{str(uuid.uuid4())}"


def set_anonymous_user_cookie(response: Response, user_id: str):
    """Helper function to set anonymous user cookie consistently."""
    response.set_cookie(
        key=ANONYMOUS_USER_COOKIE,
        value=user_id,
        httponly=False,  # Allow JavaScript access
        secure=False,  # For localhost development
        samesite="lax",
        path="/",
        max_age=30 * 24 * 60 * 60,  # 30 days
    )


async def ensure_anonymous_user_exists(
    database: Database, user_id: str, is_anonymous: bool
):
    """Ensure anonymous user exists in database."""
    if is_anonymous:
        # Create a unique username for each anonymous user
        username = f"Anonymous-{user_id.split('_')[-1][:8]}"
        await database.get_or_create_user(user_id, username)


def get_user_id_for_conversation(request: Request) -> tuple[str, bool]:
    """Get user ID for conversation operations.

    Returns:
        tuple: (user_id, is_anonymous) - user_id and whether they're anonymous
    """
    user_id, is_authenticated = get_authenticated_user_id(request)
    if is_authenticated:
        return user_id, False

    # Use anonymous user ID
    anonymous_id = get_or_create_anonymous_user_id(request)
    return anonymous_id, True


@app.get("/me", response_model=ChatUser)
async def get_user_profile(
    request: Request,
    response: Response,
    database: Database = Depends(get_db),
) -> ChatUser:
    """Get the user's profile (authenticated or anonymous)."""
    user_id, is_authenticated = get_authenticated_user_id(request)

    if is_authenticated:
        try:
            # Get user data from session for authenticated users
            session_id = request.cookies.get("session_id")
            user_data = auth_service.get_session_user(session_id)
            if user_data:
                # Create User model from auth data for chat system compatibility
                # Use the user's first name as username
                first_name = (
                    user_data.get("name", "").split()[0]
                    if user_data.get("name")
                    else "User"
                )

                return ChatUser(
                    id=user_data.get("id", ""),
                    username=first_name,
                    created_at=datetime.now(tz=timezone.utc),
                    updated_at=datetime.now(tz=timezone.utc),
                )
        except ImportError:
            pass

    # Handle anonymous user
    anonymous_id = get_or_create_anonymous_user_id(request)

    # Set anonymous user cookie
    set_anonymous_user_cookie(response, anonymous_id)

    # Check if anonymous user exists in database, create if not
    user = await database.get_user(anonymous_id)
    if user is None:
        username = f"Anonymous-{anonymous_id.split('_')[-1][:8]}"
        user = await database.get_or_create_user(anonymous_id, username)

    return user


@app.get("/business", response_model=Optional[BusinessResponse])
async def get_business(
    request: Request,
    database: Database = Depends(get_db),
) -> Optional[BusinessResponse]:
    """Get business information for the authenticated user."""
    user_id, is_authenticated = get_authenticated_user_id(request)

    if not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    business_data = await database.get_user_business(user_id)
    return business_data


@app.post("/business", response_model=BusinessResponse)
async def create_or_update_business(
    business: BusinessBase,
    request: Request,
    database: Database = Depends(get_db),
) -> BusinessResponse:
    """Create or update business information for the authenticated user."""
    user_id, is_authenticated = get_authenticated_user_id(request)

    if not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    business_data = await database.create_or_update_business(
        user_id=user_id,
        name=business.name,
        url=business.url,
        description=business.description,
    )

    return business_data


@app.delete("/business")
async def delete_business(
    request: Request,
    database: Database = Depends(get_db),
) -> dict:
    """Delete business information for the authenticated user."""
    user_id, is_authenticated = get_authenticated_user_id(request)

    if not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    success = await database.delete_user_business(user_id)
    if success:
        return {"message": "Business information deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business information found",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", reload=True, reload_dirs=[str(THIS_DIR)]
    )
