from __future__ import annotations as _annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional, List, Dict
import json

import asyncpg
import logfire
from pydantic import BaseModel, Field
import redis


from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
)

from app.models.models import ChatMessage, ChatUser, BusinessResponse, ConversationInfo
from app.config import Settings
from app.models.facebook_models import FacebookCredentialsResponse

settings = Settings()

# Redis client
redis_client = redis.from_url(str(settings.redis_url), decode_responses=True)


def get_redis() -> redis.Redis:
    """Get Redis client"""
    return redis_client


class Database(BaseModel):
    """Database to store chat messages in PostgreSQL using asyncpg."""

    pool: asyncpg.Pool = Field(exclude=True)

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    @asynccontextmanager
    async def connect(cls) -> AsyncIterator[Database]:
        with logfire.span("connect to DB"):
            pool = await asyncpg.create_pool(settings.database_url)

            # Create improved schema
            async with pool.acquire() as connection:
                connection: asyncpg.Connection
                await connection.execute(
                    """
                    -- Users table with enhanced schema
                    CREATE TABLE IF NOT EXISTS users (
                        id VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255) UNIQUE,
                        provider_id VARCHAR(255) UNIQUE,
                        email VARCHAR(255) UNIQUE,
                        name VARCHAR(255),
                        picture TEXT,
                        provider VARCHAR(50) DEFAULT 'google',
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_login TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    
                    -- Add missing columns to existing users table if they don't exist
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS provider_id VARCHAR(255) UNIQUE;
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE;
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255);
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS picture TEXT;
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS provider VARCHAR(50) DEFAULT 'google';
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE DEFAULT NOW();

                    -- Sessions table for auth management
                    CREATE TABLE IF NOT EXISTS sessions (
                        id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        provider_id VARCHAR(255) NOT NULL,
                        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );

                    -- Conversations table
                    CREATE TABLE IF NOT EXISTS conversations (
                        id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(500),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        is_active BOOLEAN DEFAULT TRUE
                    );

                    -- Messages table 
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        conversation_id VARCHAR(255) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                        message_list TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );

                    -- Businesses table
                    CREATE TABLE IF NOT EXISTS businesses (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        url TEXT NOT NULL,
                        description TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );

                    -- Facebook credentials table
                    CREATE TABLE IF NOT EXISTS facebook_credentials (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        facebook_user_id VARCHAR(255) NOT NULL,
                        facebook_user_name VARCHAR(255) NOT NULL,
                        facebook_user_email VARCHAR(255),
                        access_token TEXT NOT NULL,
                        pages_data TEXT,
                        instagram_accounts_data TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        UNIQUE(user_id)
                    );

                    -- Indexes for better performance
                    CREATE INDEX IF NOT EXISTS idx_users_provider_id ON users(provider_id);
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                    CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
                    CREATE INDEX IF NOT EXISTS idx_sessions_provider_id ON sessions(provider_id);
                    CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
                    CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
                    CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
                    CREATE INDEX IF NOT EXISTS idx_businesses_user_id ON businesses(user_id);
                    CREATE INDEX IF NOT EXISTS idx_facebook_credentials_user_id ON facebook_credentials(user_id);
                    CREATE INDEX IF NOT EXISTS idx_facebook_credentials_facebook_user_id ON facebook_credentials(facebook_user_id);

                    -- Trigger to update updated_at timestamp
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = NOW();
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql';

                    DROP TRIGGER IF EXISTS update_users_updated_at ON users;
                    CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

                    DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
                    CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

                    DROP TRIGGER IF EXISTS update_businesses_updated_at ON businesses;
                    CREATE TRIGGER update_businesses_updated_at BEFORE UPDATE ON businesses
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

                    DROP TRIGGER IF EXISTS update_facebook_credentials_updated_at ON facebook_credentials;
                    CREATE TRIGGER update_facebook_credentials_updated_at BEFORE UPDATE ON facebook_credentials
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

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

    async def get_or_create_user(self, user_id: str, username: str) -> ChatUser:
        """Get existing user or create new one, returning a User model."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            # Try to find existing user
            existing_user = await connection.fetchrow(
                "SELECT id, username, created_at, updated_at FROM users WHERE id = $1",
                user_id,
            )

            if existing_user:
                return ChatUser.model_validate(dict(existing_user))

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
            return ChatUser.model_validate(dict(new_user))

    async def get_user(self, user_id: str) -> ChatUser | None:
        """Get existing user details as a User model."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            user = await connection.fetchrow(
                "SELECT id, username, created_at, updated_at FROM users WHERE id = $1",
                user_id,
            )
            if user:
                return ChatUser.model_validate(dict(user))
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

    async def get_user_conversations(
        self, user_id: str, limit: int = 50
    ) -> List[ConversationInfo]:
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

            return [ConversationInfo(**dict(row)) for row in rows]

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

    async def transfer_conversations_to_user(
        self, from_user_id: str, to_user_id: str
    ) -> int:
        """Transfer all conversations from one user to another (e.g., anonymous to authenticated)."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection

            # Update conversations to new user_id
            result = await connection.execute(
                """
                UPDATE conversations 
                SET user_id = $1, updated_at = NOW()
                WHERE user_id = $2 AND is_active = TRUE
                """,
                to_user_id,
                from_user_id,
            )

            # Extract the number of affected rows
            rows_affected = (
                int(result.split()[-1]) if result.startswith("UPDATE") else 0
            )
            return rows_affected

    async def get_conversation_owner(self, conversation_id: str) -> Optional[str]:
        """Get the user_id who owns a conversation."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            row = await connection.fetchrow(
                "SELECT user_id FROM conversations WHERE id = $1", conversation_id
            )
            return row["user_id"] if row else None

    async def update_conversation_owner(
        self, conversation_id: str, new_user_id: str
    ) -> bool:
        """Update the owner of a specific conversation."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            result = await connection.execute(
                """
                UPDATE conversations 
                SET user_id = $1, updated_at = NOW()
                WHERE id = $2
                """,
                new_user_id,
                conversation_id,
            )
            return result == "UPDATE 1"

    async def user_owns_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Check if a user owns a specific conversation."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            row = await connection.fetchrow(
                "SELECT 1 FROM conversations WHERE id = $1 AND user_id = $2",
                conversation_id,
                user_id,
            )
            return row is not None

    # Business-related methods
    async def get_user_business(self, user_id: str) -> Optional[BusinessResponse]:
        """Get business information for a user."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            row = await connection.fetchrow(
                """
                SELECT id, user_id, name, url, description, created_at, updated_at
                FROM businesses 
                WHERE user_id = $1
                """,
                user_id,
            )
            return BusinessResponse(**dict(row)) if row else None

    async def create_or_update_business(
        self, user_id: str, name: str, url: str, description: str
    ) -> BusinessResponse:
        """Create or update business information for a user."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection

            # Check if business already exists
            existing = await connection.fetchrow(
                "SELECT id FROM businesses WHERE user_id = $1", user_id
            )

            if existing:
                # Update existing business
                row = await connection.fetchrow(
                    """
                    UPDATE businesses 
                    SET name = $2, url = $3, description = $4, updated_at = NOW()
                    WHERE user_id = $1
                    RETURNING id, user_id, name, url, description, created_at, updated_at
                    """,
                    user_id,
                    name,
                    url,
                    description,
                )
            else:
                # Create new business
                row = await connection.fetchrow(
                    """
                    INSERT INTO businesses (user_id, name, url, description)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id, user_id, name, url, description, created_at, updated_at
                    """,
                    user_id,
                    name,
                    url,
                    description,
                )

            return BusinessResponse(**dict(row))

    async def delete_user_business(self, user_id: str) -> bool:
        """Delete business information for a user."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            result = await connection.execute(
                "DELETE FROM businesses WHERE user_id = $1", user_id
            )
            return result == "DELETE 1"

    # Facebook credentials methods
    async def get_facebook_credentials(
        self, user_id: str
    ) -> Optional[FacebookCredentialsResponse]:
        """Get Facebook credentials for a user."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            row = await connection.fetchrow(
                """
                SELECT id, user_id, facebook_user_id, facebook_user_name, 
                       facebook_user_email, access_token, pages_data, 
                       instagram_accounts_data, created_at, updated_at
                FROM facebook_credentials 
                WHERE user_id = $1
                """,
                user_id,
            )
            if row:
                # Parse JSON data
                row_dict = dict(row)
                if row_dict.get("pages_data"):
                    row_dict["pages_data"] = json.loads(row_dict["pages_data"])
                if row_dict.get("instagram_accounts_data"):
                    row_dict["instagram_accounts_data"] = json.loads(
                        row_dict["instagram_accounts_data"]
                    )
                return FacebookCredentialsResponse(**row_dict)
            return None

    async def create_or_update_facebook_credentials(
        self,
        user_id: str,
        facebook_user_id: str,
        facebook_user_name: str,
        facebook_user_email: Optional[str],
        access_token: str,
        pages_data: Optional[str] = None,
        instagram_accounts_data: Optional[str] = None,
    ) -> FacebookCredentialsResponse:
        """Create or update Facebook credentials for a user."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection

            # Check if credentials already exist
            existing = await connection.fetchrow(
                "SELECT id FROM facebook_credentials WHERE user_id = $1", user_id
            )

            if existing:
                # Update existing credentials
                row = await connection.fetchrow(
                    """
                    UPDATE facebook_credentials 
                    SET facebook_user_id = $2, facebook_user_name = $3, 
                        facebook_user_email = $4, access_token = $5, 
                        pages_data = $6, instagram_accounts_data = $7, updated_at = NOW()
                    WHERE user_id = $1
                    RETURNING id, user_id, facebook_user_id, facebook_user_name, 
                              facebook_user_email, access_token, pages_data, 
                              instagram_accounts_data, created_at, updated_at
                    """,
                    user_id,
                    facebook_user_id,
                    facebook_user_name,
                    facebook_user_email,
                    access_token,
                    pages_data,
                    instagram_accounts_data,
                )
            else:
                # Create new credentials
                row = await connection.fetchrow(
                    """
                    INSERT INTO facebook_credentials 
                    (user_id, facebook_user_id, facebook_user_name, facebook_user_email, 
                     access_token, pages_data, instagram_accounts_data)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id, user_id, facebook_user_id, facebook_user_name, 
                              facebook_user_email, access_token, pages_data, 
                              instagram_accounts_data, created_at, updated_at
                    """,
                    user_id,
                    facebook_user_id,
                    facebook_user_name,
                    facebook_user_email,
                    access_token,
                    pages_data,
                    instagram_accounts_data,
                )

            # Parse JSON data
            row_dict = dict(row)
            if row_dict.get("pages_data"):
                row_dict["pages_data"] = json.loads(row_dict["pages_data"])
            if row_dict.get("instagram_accounts_data"):
                row_dict["instagram_accounts_data"] = json.loads(
                    row_dict["instagram_accounts_data"]
                )
            return FacebookCredentialsResponse(**row_dict)

    async def delete_facebook_credentials(self, user_id: str) -> bool:
        """Delete Facebook credentials for a user."""
        async with self.pool.acquire() as connection:
            connection: asyncpg.Connection
            result = await connection.execute(
                "DELETE FROM facebook_credentials WHERE user_id = $1", user_id
            )
            return result == "DELETE 1"
