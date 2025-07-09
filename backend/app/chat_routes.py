from __future__ import annotations as _annotations

from datetime import date, datetime, timezone
from typing import Annotated, Literal, Optional, List
from pydantic import HttpUrl, BaseModel
import json
import uuid

from fastapi import APIRouter, Depends, Request, HTTPException, status, Form, Response
from fastapi.responses import StreamingResponse
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

from app.agents import chat_agent, topic_agent, BusinessInfo, ChatDependencies
from app.config import Settings
from app.db import Database
from app.models import ConversationInfo

settings = Settings()

# Router setup
router = APIRouter(prefix="/chat", tags=["chat"])


# Dependencies
async def get_db(request: Request) -> Database:
    return request.state.db


# Chat-specific models
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


# Helper functions
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


# Chat endpoints
@router.post("/new-conversation", response_model=NewConversationResponse)
async def new_conversation() -> NewConversationResponse:
    """Generate a conversation ID but do not persist yet."""
    conversation_id = str(uuid.uuid4())
    return NewConversationResponse(conversation_id=conversation_id)


@router.get("/conversations", response_model=ConversationsResponse)
async def get_conversations(
    request: Request,
    response: Response,
    database: Database = Depends(get_db),
) -> ConversationsResponse:
    """Get all conversations for the user (authenticated or anonymous)."""
    # Import from main to avoid circular imports
    from app.main import (
        get_user_id_for_conversation,
        set_anonymous_user_cookie,
        ensure_anonymous_user_exists,
    )

    user_id, is_anonymous = get_user_id_for_conversation(request)

    # Set anonymous user cookie if needed
    if is_anonymous:
        set_anonymous_user_cookie(response, user_id)

    # Ensure anonymous user exists in database
    await ensure_anonymous_user_exists(database, user_id, is_anonymous)

    conversations = await database.get_user_conversations(user_id)
    # conversations already returns List[ConversationInfo]
    return ConversationsResponse(conversations=conversations)


@router.get("/{conversation_id}")
async def get_chat(
    conversation_id: str,
    request: Request,
    response: Response,
    database: Database = Depends(get_db),
) -> Response:
    """Get messages from a specific conversation."""
    # Import from main to avoid circular imports
    from app.main import (
        get_user_id_for_conversation,
        set_anonymous_user_cookie,
        ensure_anonymous_user_exists,
    )

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


@router.post("/migrate-conversations")
async def migrate_conversations(
    request: Request,
    database: Database = Depends(get_db),
):
    """Migrate anonymous conversations to authenticated user."""
    # Import from main to avoid circular imports
    from app.main import get_authenticated_user_id, ANONYMOUS_USER_COOKIE

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


@router.post("/{conversation_id}")
async def post_chat(
    conversation_id: str,
    prompt: Annotated[str, Form()],
    request: Request,
    response: Response,
    database: Database = Depends(get_db),
    attachments: Annotated[Optional[str], Form()] = None,
) -> StreamingResponse:
    """Send a message to a specific conversation."""
    # Import from main to avoid circular imports
    from app.main import (
        get_user_id_for_conversation,
        set_anonymous_user_cookie,
        ensure_anonymous_user_exists,
    )

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
