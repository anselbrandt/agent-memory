from __future__ import annotations as _annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal, Optional, List
import uuid

import fastapi
import logfire
from fastapi import Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from typing_extensions import TypedDict
from pydantic import BaseModel

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from dotenv import load_dotenv

from app.config import Settings
from app.db import Database, User

settings = Settings()
load_dotenv()

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()

agent = Agent("openai:gpt-4o")
THIS_DIR = Path(__file__).parent

# Mock user configuration
MOCK_USER_ID = "9000"
MOCK_USERNAME = "Dave"


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
    allow_origins=["http://localhost:3000"],  # or ["*"] for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Visit localhost:3000"}


async def get_db(request: Request) -> Database:
    return request.state.db


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


def to_chat_message(m: ModelMessage) -> ChatMessage:
    first_part = m.parts[0]
    if isinstance(m, ModelRequest):
        if isinstance(first_part, UserPromptPart):
            assert isinstance(first_part.content, str)
            return {
                "role": "user",
                "timestamp": first_part.timestamp.isoformat(),
                "content": first_part.content,
            }
    elif isinstance(m, ModelResponse):
        if isinstance(first_part, TextPart):
            return {
                "role": "model",
                "timestamp": m.timestamp.isoformat(),
                "content": first_part.content,
            }
    raise UnexpectedModelBehavior(f"Unexpected message type for chat app: {m}")


@app.post("/chat/new-conversation", response_model=NewConversationResponse)
async def new_conversation() -> NewConversationResponse:
    """Generate a conversation ID but do not persist yet."""
    conversation_id = str(uuid.uuid4())
    return NewConversationResponse(conversation_id=conversation_id)


@app.get("/chat/conversations", response_model=ConversationsResponse)
async def get_conversations(
    database: Database = Depends(get_db),
) -> ConversationsResponse:
    """Get all conversations for the mock user."""
    conversations = await database.get_user_conversations(MOCK_USER_ID)
    # Convert dict rows to ConversationInfo objects
    conversation_objects = [ConversationInfo(**conv) for conv in conversations]
    return ConversationsResponse(conversations=conversation_objects)


@app.get("/chat/{conversation_id}")
async def get_chat(
    conversation_id: str, database: Database = Depends(get_db)
) -> Response:
    """Get messages from a specific conversation."""
    msgs = await database.get_conversation_messages(conversation_id)
    return Response(
        b"\n".join(json.dumps(to_chat_message(m)).encode("utf-8") for m in msgs),
        media_type="text/plain",
    )


@app.post("/chat/{conversation_id}")
async def post_chat(
    conversation_id: str,
    prompt: Annotated[str, fastapi.Form()],
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

        # Lazily create the conversation if it doesn't exist
        exists = await database.conversation_exists(conversation_id)
        if not exists:
            await database.create_conversation_with_id(
                conversation_id, MOCK_USER_ID, "New Chat"
            )

        # fetch conversation history
        messages = await database.get_conversation_messages(conversation_id)

        # run the agent and stream output
        async with agent.run_stream(prompt, message_history=messages) as result:
            async for text in result.stream(debounce_by=0.01):
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp())
                yield json.dumps(to_chat_message(m)).encode("utf-8") + b"\n"

        # persist all new messages
        await database.add_messages_to_conversation(
            conversation_id, result.new_messages_json()
        )

    return StreamingResponse(stream_messages(), media_type="text/plain")


@app.get("/me", response_model=User)
async def get_user_profile(
    user_id: str = "9000",
    database: Database = Depends(get_db),
) -> User:
    """Get the user's profile."""
    user = await database.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "pydantic_ai_examples.chat_app:app", reload=True, reload_dirs=[str(THIS_DIR)]
    )
