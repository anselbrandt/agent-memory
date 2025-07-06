from __future__ import annotations as _annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Literal, Optional, List
import json
import uuid

from dotenv import load_dotenv
from fastapi import Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from typing_extensions import TypedDict
import fastapi
import logfire

from app.agents import chat_agent, topic_agent, ChatDependencies
from app.config import Settings
from app.db import Database, User
from app.auth_routes import auth_router
from app.auth_service import auth_service

settings = Settings()
load_dotenv()

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


THIS_DIR = Path(__file__).parent

# Mock user configuration
MOCK_USER_ID = settings.mock_user_id
MOCK_USERNAME = settings.mock_username


@asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
    async with Database.connect() as db:
        # Ensure mock user exists
        await db.get_or_create_user(MOCK_USER_ID, MOCK_USERNAME)
        yield {"db": db}


app = fastapi.FastAPI(lifespan=lifespan)
logfire.instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/")
async def root():
    return {"message": f"Visit {settings.frontend_url}"}


async def get_db(request: Request) -> Database:
    return request.state.db


def get_authenticated_user_id(request: Request) -> str:
    """Get the authenticated user ID from session, fallback to mock user"""
    try:
        from app.routes.auth import auth_service

        session_id = request.cookies.get("session_id")
        if session_id:
            user_data = auth_service.get_session_user(session_id)
            if user_data:
                return user_data.get("id", MOCK_USER_ID)
    except ImportError:
        pass

    return MOCK_USER_ID


class ChatMessage(TypedDict):
    """Format of messages sent to the browser."""

    role: Literal["user", "model"]
    timestamp: str
    content: str


class ConversationInfo(BaseModel):
    """Information about a conversation."""

    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int


class NewConversationResponse(BaseModel):
    """Response for creating a new conversation."""

    conversation_id: str


class ConversationsResponse(BaseModel):
    """Response containing list of conversations."""

    conversations: List[ConversationInfo]


def to_chat_message(m: ModelMessage) -> Optional[ChatMessage]:
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
    database: Database = Depends(get_db),
) -> ConversationsResponse:
    """Get all conversations for the authenticated user."""
    user_id = get_authenticated_user_id(request)
    conversations = await database.get_user_conversations(user_id)
    # Convert dict rows to ConversationInfo objects
    conversation_objects = [ConversationInfo(**conv) for conv in conversations]
    return ConversationsResponse(conversations=conversation_objects)


@app.get("/chat/{conversation_id}")
async def get_chat(
    conversation_id: str, database: Database = Depends(get_db)
) -> Response:
    """Get messages from a specific conversation."""
    msgs = await database.get_conversation_messages(conversation_id)
    lines = [
        json.dumps(chat_msg).encode("utf-8")
        for m in msgs
        if (chat_msg := to_chat_message(m)) is not None
    ]
    return Response(b"\n".join(lines), media_type="text/plain")


@app.post("/chat/{conversation_id}")
async def post_chat(
    conversation_id: str,
    prompt: Annotated[str, fastapi.Form()],
    request: Request,
    database: Database = Depends(get_db),
) -> StreamingResponse:
    """Send a message to a specific conversation."""

    async def stream_messages():
        user_message = {
            "role": "user",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "content": prompt,
        }
        yield json.dumps(user_message).encode("utf-8") + b"\n"

        # Get authenticated user ID
        user_id = get_authenticated_user_id(request)

        # Lazily create the conversation if it doesn't exist
        exists = await database.conversation_exists(conversation_id)
        if not exists:
            topic_result = await topic_agent.run([prompt])
            topic = topic_result.output.topic
            await database.create_conversation_with_id(conversation_id, user_id, topic)

        # fetch conversation history
        messages = await database.get_conversation_messages(conversation_id)

        # run the agent and stream output
        current_date = date.today()
        date_string = current_date.strftime("%Y-%m-%d")
        deps = ChatDependencies(todays_date=date_string)
        async with chat_agent.run_stream(
            prompt, message_history=messages, deps=deps
        ) as result:
            async for text in result.stream(debounce_by=settings.chat_debounce_delay):
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp())
                yield json.dumps(to_chat_message(m)).encode("utf-8") + b"\n"

        # persist all new messages
        await database.add_messages_to_conversation(
            conversation_id, result.new_messages_json()
        )

    return StreamingResponse(stream_messages(), media_type="text/plain")


@app.get("/me", response_model=User)
async def get_user_profile(
    request: Request,
    database: Database = Depends(get_db),
) -> User:
    """Get the authenticated user's profile."""
    try:
        # Get session from cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            # Get user data from session
            user_data = auth_service.get_session_user(session_id)
            if user_data:
                # Create User model from auth data for chat system compatibility
                # Use the user's first name as username
                first_name = (
                    user_data.get("name", "").split()[0]
                    if user_data.get("name")
                    else "User"
                )

                return User(
                    id=user_data.get("id", ""),
                    username=first_name,
                    created_at=datetime.now(tz=timezone.utc),
                    updated_at=datetime.now(tz=timezone.utc),
                )
    except ImportError:
        pass

    # Fallback to mock user
    user = await database.get_user(settings.mock_user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "pydantic_ai_examples.chat_app:app", reload=True, reload_dirs=[str(THIS_DIR)]
    )
