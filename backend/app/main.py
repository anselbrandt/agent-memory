from __future__ import annotations as _annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Literal, Optional, List
from pydantic import HttpUrl, BaseModel
import json
import uuid

from dotenv import load_dotenv

# Load environment variables first, before any other imports
load_dotenv()

from fastapi import Depends, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
    ImageUrl,
    DocumentUrl,
)
from typing_extensions import TypedDict
import fastapi
import logfire

from app.agents import chat_agent, topic_agent, BusinessInfo, ChatDependencies
from app.config import Settings
from app.db import Database, ChatUser
from app.auth_routes import auth_router
from app.auth_service import auth_service
from app.models import BusinessBase, BusinessResponse, ConversationInfo
from app.facebook_oauth_routes import router as facebook_router
from app.upload_routes import router as upload_router

settings = Settings()

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


THIS_DIR = Path(__file__).parent

# Anonymous user management
ANONYMOUS_USER_COOKIE = "anonymous_user_id"


@asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
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
        from app.auth_service import auth_service

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


class BrowserMessage(TypedDict):
    """Format of messages sent to the browser."""

    role: Literal["user", "model"]
    timestamp: str
    content: str


class NewConversationResponse(BaseModel):
    """Response for creating a new conversation."""

    conversation_id: str


class ConversationsResponse(BaseModel):
    """Response containing list of conversations."""

    conversations: List[ConversationInfo]


class Attachment(BaseModel):
    """Attachment with URL, file type, and friendly name."""

    url: HttpUrl
    file_type: str
    friendly_name: str


def to_chat_message(m: ModelMessage) -> Optional[BrowserMessage]:
    if isinstance(m, ModelRequest):
        for part in m.parts:
            if isinstance(part, UserPromptPart):
                return {
                    "role": "user",
                    "timestamp": part.timestamp.isoformat(),
                    "content": part.content,
                }

    elif isinstance(m, ModelResponse):
        for part in m.parts:
            if isinstance(part, TextPart):
                return {
                    "role": "model",
                    "timestamp": m.timestamp.isoformat(),
                    "content": part.content,
                }

    # Ignore system prompts, tool calls, etc.
    return None


@app.post("/chat/new-conversation", response_model=NewConversationResponse)
async def new_conversation() -> NewConversationResponse:
    """Generate a conversation ID but do not persist yet."""
    conversation_id = str(uuid.uuid4())
    return NewConversationResponse(conversation_id=conversation_id)


@app.get("/chat/conversations", response_model=ConversationsResponse)
async def get_conversations(
    request: Request,
    response: Response,
    database: Database = Depends(get_db),
) -> ConversationsResponse:
    """Get all conversations for the user (authenticated or anonymous)."""
    user_id, is_anonymous = get_user_id_for_conversation(request)

    # Set anonymous user cookie if needed
    if is_anonymous:
        set_anonymous_user_cookie(response, user_id)

    # Ensure anonymous user exists in database
    await ensure_anonymous_user_exists(database, user_id, is_anonymous)

    conversations = await database.get_user_conversations(user_id)
    # conversations already returns List[ConversationInfo]
    return ConversationsResponse(conversations=conversations)


@app.get("/chat/{conversation_id}")
async def get_chat(
    conversation_id: str,
    request: Request,
    response: Response,
    database: Database = Depends(get_db),
) -> Response:
    """Get messages from a specific conversation."""
    user_id, is_anonymous = get_user_id_for_conversation(request)

    # Set anonymous user cookie if needed
    if is_anonymous:
        set_anonymous_user_cookie(response, user_id)

    # Ensure anonymous user exists in database
    await ensure_anonymous_user_exists(database, user_id, is_anonymous)

    # Check if user owns this conversation
    if not await database.user_owns_conversation(conversation_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    msgs = await database.get_conversation_messages(conversation_id)
    lines = [
        json.dumps(chat_msg).encode("utf-8")
        for m in msgs
        if (chat_msg := to_chat_message(m)) is not None
    ]
    return Response(b"\n".join(lines), media_type="text/plain")


@app.post("/chat/migrate-conversations")
async def migrate_conversations(
    request: Request,
    database: Database = Depends(get_db),
):
    """Migrate anonymous conversations to authenticated user."""
    user_id, is_authenticated = get_authenticated_user_id(request)

    if not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User must be authenticated to migrate conversations",
        )

    # Get the anonymous user ID from cookie
    anonymous_user_id = request.cookies.get(ANONYMOUS_USER_COOKIE)
    if not anonymous_user_id:
        return {
            "migrated_conversations": 0,
            "user_id": user_id,
            "message": "No anonymous conversations to migrate",
        }

    # Transfer conversations from anonymous user to authenticated user
    transferred_count = await database.transfer_conversations_to_user(
        from_user_id=anonymous_user_id, to_user_id=user_id
    )

    return {
        "migrated_conversations": transferred_count,
        "user_id": user_id,
        "anonymous_user_id": anonymous_user_id,
    }


@app.post("/chat/{conversation_id}")
async def post_chat(
    conversation_id: str,
    prompt: Annotated[str, fastapi.Form()],
    request: Request,
    response: Response,
    database: Database = Depends(get_db),
    attachments: Annotated[Optional[str], fastapi.Form()] = None,
) -> StreamingResponse:
    """Send a message to a specific conversation."""

    # Get user ID (authenticated or anonymous)
    user_id, is_anonymous = get_user_id_for_conversation(request)

    # Set anonymous user cookie if needed
    if is_anonymous:
        set_anonymous_user_cookie(response, user_id)

    # Ensure anonymous user exists in database
    await ensure_anonymous_user_exists(database, user_id, is_anonymous)

    # Check if conversation exists and if user owns it (do this before streaming)
    exists = await database.conversation_exists(conversation_id)
    if exists:
        # Verify ownership
        if not await database.user_owns_conversation(conversation_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

    # Fetch user's business information (only for authenticated users)
    business_info = None
    if not is_anonymous:
        business_data = await database.get_user_business(user_id)
        if business_data:
            business_info = BusinessInfo(
                name=business_data.name,
                url=business_data.url,
                description=business_data.description,
            )

    # Parse and validate attachments if provided
    validated_attachments: List[Attachment] = []
    if attachments:
        try:
            attachment_data = json.loads(attachments)
            if isinstance(attachment_data, list):
                # Validate each attachment
                for item in attachment_data:
                    try:
                        if (
                            isinstance(item, dict)
                            and "url" in item
                            and "file_type" in item
                            and "friendly_name" in item
                        ):
                            attachment = Attachment(
                                url=item["url"],
                                file_type=item["file_type"],
                                friendly_name=item["friendly_name"],
                            )
                            validated_attachments.append(attachment)
                        else:
                            print(f"Invalid attachment format: {item}")
                    except Exception as e:
                        print(f"Invalid attachment: {item} - {e}")
        except json.JSONDecodeError:
            print(f"Failed to parse attachments JSON: {attachments}")

    # Print the attachments list as requested
    if validated_attachments:
        print(
            f"Attachments received: {[(str(att.url), att.file_type, att.friendly_name) for att in validated_attachments]}"
        )

    async def stream_messages():
        user_message = {
            "role": "user",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "content": prompt,
        }
        yield json.dumps(user_message).encode("utf-8") + b"\n"

        # Create conversation if it doesn't exist (we already checked ownership above)
        if not exists:
            # Use only the text prompt for topic generation
            topic_result = await topic_agent.run([prompt])
            topic = topic_result.output.topic
            await database.create_conversation_with_id(conversation_id, user_id, topic)

        # fetch conversation history
        messages = await database.get_conversation_messages(conversation_id)

        # Build prompt with attachments
        prompt_parts = [prompt]

        # Add image and document attachments to the prompt
        for attachment in validated_attachments:
            mime_type = attachment.file_type.lower()
            url_str = str(attachment.url)

            # Check if it's an image
            if mime_type.startswith("image/"):
                prompt_parts.append(ImageUrl(url=url_str))
            # Check if it's a document (PDF, text, etc.)
            elif mime_type in [
                "application/pdf",
                "text/plain",
                "text/html",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ]:
                prompt_parts.append(DocumentUrl(url=url_str))
            # Skip video and audio files as requested
            elif mime_type.startswith(("video/", "audio/")):
                print(
                    f"Skipping {attachment.file_type} attachment: {attachment.friendly_name}"
                )
                continue

        # run the agent and stream output with business context
        current_date = date.today()
        date_string = current_date.strftime("%Y-%m-%d")
        deps = ChatDependencies(todays_date=date_string, business_info=business_info)

        async with chat_agent.run_stream(
            prompt_parts, message_history=messages, deps=deps
        ) as result:
            async for text in result.stream(debounce_by=settings.chat_debounce_delay):
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp())
                yield json.dumps(to_chat_message(m)).encode("utf-8") + b"\n"

        # persist all new messages
        await database.add_messages_to_conversation(
            conversation_id, result.new_messages_json()
        )

    return StreamingResponse(stream_messages(), media_type="text/plain")


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
        "pydantic_ai_examples.chat_app:app", reload=True, reload_dirs=[str(THIS_DIR)]
    )
