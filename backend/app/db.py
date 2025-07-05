from __future__ import annotations as _annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional, List, Dict

import asyncpg
import logfire
from pydantic import BaseModel, Field

from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
)

from app.models import ChatMessage, User


class Database(BaseModel):
    """Database to store chat messages in PostgreSQL using asyncpg."""

    pool: asyncpg.Pool = Field(exclude=True)

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    @asynccontextmanager
    async def connect(cls) -> AsyncIterator[Database]:
        with logfire.span("connect to DB"):
            pool = await asyncpg.create_pool(
                user="postgres",
                password="postgres",
                database="agentmemory",
                host="0.0.0.0",
                port=5432,
                min_size=1,
                max_size=10,
            )

            # Create improved schema
            async with pool.acquire() as connection:
                connection: asyncpg.Connection
                await connection.execute(
                    """
                    -- Users table
                    CREATE TABLE IF NOT EXISTS users (
                        id VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255) UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    -- Conversations table
                    CREATE TABLE IF NOT EXISTS conversations (
                        id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    );

                    -- Messages table (keeping original structure but adding conversation_id)
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        conversation_id VARCHAR(255) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                        message_list TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    -- Indexes for better performance
                    CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
                    CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
                    CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

                    -- Function to generate conversation IDs
                    CREATE OR REPLACE FUNCTION generate_conversation_id() 
                    RETURNS TEXT AS $$
                    BEGIN
                        RETURN 'conv_' || extract(epoch from now())::bigint || '_' || floor(random() * 1000)::int;
                    END;
                    $$ LANGUAGE plpgsql;
                """
                )

            slf = cls(pool=pool)

        try:
            yield slf
        finally:
            await pool.close()

    async def add_chat_messages_to_conversation(
        self, conversation_id: str, messages: List[ChatMessage]
    ):
        """Add ChatMessage objects to a specific conversation."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            # Convert ChatMessage objects to JSON
            messages_json = [msg.model_dump() for msg in messages]
            await connection.execute(
                "INSERT INTO messages (conversation_id, message_list) VALUES ($1, $2)",
                conversation_id,
                ModelMessagesTypeAdapter.dump_json(messages_json).decode("utf-8"),
            )

            # Update conversation timestamp
            await connection.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                conversation_id,
            )

    async def get_conversation_chat_messages(
        self, conversation_id: str
    ) -> List[ChatMessage]:
        """Get all messages for a specific conversation as ChatMessage objects."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            rows = await connection.fetch(
                """SELECT message_list FROM messages 
                   WHERE conversation_id = $1 
                   ORDER BY id""",
                conversation_id,
            )

            messages: List[ChatMessage] = []
            for row in rows:
                # Parse the JSON message list
                message_data = ModelMessagesTypeAdapter.validate_json(
                    row["message_list"]
                )
                # Convert to ChatMessage objects
                for msg_dict in message_data:
                    messages.append(ChatMessage.model_validate(msg_dict))
            return messages

    async def get_or_create_user(self, user_id: str, username: str) -> User:
        """Get existing user or create new one, returning a User model."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            # Try to find existing user
            existing_user = await connection.fetchrow(
                "SELECT id, username, created_at, updated_at FROM users WHERE id = $1",
                user_id,
            )

            if existing_user:
                return User.model_validate(dict(existing_user))

            # Create new user
            await connection.execute(
                "INSERT INTO users (id, username) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING",
                user_id,
                username,
            )

            # Fetch the created user with timestamps
            new_user = await connection.fetchrow(
                "SELECT id, username, created_at, updated_at FROM users WHERE id = $1",
                user_id,
            )
            return User.model_validate(dict(new_user))

    async def get_user(self, user_id: str) -> User | None:
        """Get existing user details as a User model."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            user = await connection.fetchrow(
                "SELECT id, username, created_at, updated_at FROM users WHERE id = $1",
                user_id,
            )
            if user:
                return User.model_validate(dict(user))
            return None

    async def create_conversation(
        self, user_id: str, title: Optional[str] = None
    ) -> str:
        """Create a new conversation for a user."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            conversation_id = await connection.fetchval(
                "SELECT generate_conversation_id()"
            )
            await connection.execute(
                "INSERT INTO conversations (id, user_id, title) VALUES ($1, $2, $3)",
                conversation_id,
                user_id,
                title,
            )
            return conversation_id

    async def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get all conversations for a user."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            rows = await connection.fetch(
                """SELECT c.id, c.title, c.created_at, c.updated_at,
                          COUNT(m.id) as message_count
                   FROM conversations c
                   LEFT JOIN messages m ON c.id = m.conversation_id
                   WHERE c.user_id = $1 AND c.is_active = TRUE
                   GROUP BY c.id, c.title, c.created_at, c.updated_at
                   ORDER BY c.updated_at DESC
                   LIMIT $2""",
                user_id,
                limit,
            )

            return [dict(row) for row in rows]

    async def get_conversation_messages(
        self, conversation_id: str
    ) -> List[ModelMessage]:
        """Get all messages for a specific conversation."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            rows = await connection.fetch(
                """SELECT message_list FROM messages 
                   WHERE conversation_id = $1 
                   ORDER BY id""",
                conversation_id,
            )

            messages: List[ModelMessage] = []
            for row in rows:
                messages.extend(
                    ModelMessagesTypeAdapter.validate_json(row["message_list"])
                )
            return messages

    async def add_messages_to_conversation(self, conversation_id: str, messages: bytes):
        """Add messages to a specific conversation."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            await connection.execute(
                "INSERT INTO messages (conversation_id, message_list) VALUES ($1, $2)",
                conversation_id,
                messages.decode("utf-8"),
            )

            # Update conversation timestamp
            await connection.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                conversation_id,
            )

    async def conversation_exists(self, conversation_id: str) -> bool:
        """Check if a conversation exists."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            row = await connection.fetchrow(
                "SELECT 1 FROM conversations WHERE id = $1", conversation_id
            )
            return row is not None

    async def create_conversation_with_id(
        self, conversation_id: str, user_id: str, title: str
    ):
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            await connection.execute(
                """
                INSERT INTO conversations (id, user_id, title)
                VALUES ($1, $2, $3)
                """,
                conversation_id,
                user_id,
                title,
            )
