import asyncio
import asyncpg
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field, ConfigDict


# Database Schema - SQL DDL statements
DATABASE_SCHEMA = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    provider_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    picture TEXT,
    provider VARCHAR(50) NOT NULL DEFAULT 'google',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_provider_id ON users(provider_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    provider_id VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_provider_id ON sessions(provider_id);

-- Businesses table
CREATE TABLE IF NOT EXISTS businesses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_businesses_user_id ON businesses(user_id);

-- Facebook credentials table
CREATE TABLE IF NOT EXISTS facebook_credentials (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facebook_user_id VARCHAR(255) NOT NULL,
    facebook_user_name VARCHAR(255) NOT NULL,
    facebook_user_email VARCHAR(255),
    access_token TEXT NOT NULL,
    pages_data JSONB,
    instagram_accounts_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_facebook_credentials_user_id ON facebook_credentials(user_id);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_businesses_updated_at BEFORE UPDATE ON businesses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_facebook_credentials_updated_at BEFORE UPDATE ON facebook_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""


# Data Classes for internal representation
@dataclass
class User:
    id: int
    provider_id: str
    email: str
    name: str
    picture: Optional[str]
    provider: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login: datetime

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> "User":
        return cls(
            id=record["id"],
            provider_id=record["provider_id"],
            email=record["email"],
            name=record["name"],
            picture=record["picture"],
            provider=record["provider"],
            is_active=record["is_active"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            last_login=record["last_login"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.provider_id),  # Use provider_id as external ID
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "provider": self.provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


@dataclass
class Session:
    id: str
    user_id: int
    provider_id: str
    expires_at: datetime
    created_at: datetime

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> "Session":
        return cls(
            id=record["id"],
            user_id=record["user_id"],
            provider_id=record["provider_id"],
            expires_at=record["expires_at"],
            created_at=record["created_at"],
        )

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class Business:
    id: int
    user_id: int
    name: str
    url: str
    description: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> "Business":
        return cls(
            id=record["id"],
            user_id=record["user_id"],
            name=record["name"],
            url=record["url"],
            description=record["description"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class FacebookCredentials:
    id: int
    user_id: int
    facebook_user_id: str
    facebook_user_name: str
    facebook_user_email: Optional[str]
    access_token: str
    pages_data: Optional[List[Dict[str, Any]]]
    instagram_accounts_data: Optional[List[Dict[str, Any]]]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> "FacebookCredentials":
        return cls(
            id=record["id"],
            user_id=record["user_id"],
            facebook_user_id=record["facebook_user_id"],
            facebook_user_name=record["facebook_user_name"],
            facebook_user_email=record["facebook_user_email"],
            access_token=record["access_token"],
            pages_data=record["pages_data"],
            instagram_accounts_data=record["instagram_accounts_data"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "facebook_user_id": self.facebook_user_id,
            "facebook_user_name": self.facebook_user_name,
            "facebook_user_email": self.facebook_user_email,
            "pages_data": self.pages_data if self.pages_data else [],
            "instagram_accounts_data": (
                self.instagram_accounts_data if self.instagram_accounts_data else []
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Pydantic Models for API serialization (unchanged from original)
class UserBase(BaseModel):
    """Base user model for shared fields."""

    provider_id: str = Field(..., description="External provider user ID")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    picture: Optional[str] = Field(None, description="User profile picture URL")
    provider: str = Field(default="google", description="Authentication provider")


class UserCreate(UserBase):
    """Model for creating a new user."""

    pass


class UserUpdate(BaseModel):
    """Model for updating user information."""

    name: Optional[str] = Field(None, description="User full name")
    picture: Optional[str] = Field(None, description="User profile picture URL")


class UserResponse(UserBase):
    """Model for user API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal user ID")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: datetime = Field(..., description="Last login timestamp")


class SessionBase(BaseModel):
    """Base session model."""

    user_id: int = Field(..., description="User ID")
    provider_id: str = Field(..., description="Provider user ID")
    expires_at: datetime = Field(..., description="Session expiration time")


class SessionCreate(SessionBase):
    """Model for creating a new session."""

    id: str = Field(..., description="Session ID")


class SessionResponse(SessionBase):
    """Model for session API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Session ID")
    created_at: datetime = Field(..., description="Session creation timestamp")

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at


class BusinessBase(BaseModel):
    """Base business model for shared fields."""

    name: str = Field(..., description="Business name")
    url: str = Field(..., description="Business URL")
    description: str = Field(..., description="Business description")


class BusinessCreate(BusinessBase):
    """Model for creating a new business."""

    user_id: int = Field(..., description="User ID")


class BusinessUpdate(BaseModel):
    """Model for updating business information."""

    name: Optional[str] = Field(None, description="Business name")
    url: Optional[str] = Field(None, description="Business URL")
    description: Optional[str] = Field(None, description="Business description")


class BusinessResponse(BusinessBase):
    """Model for business API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Business ID")
    user_id: int = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Business creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class FacebookCredentialsBase(BaseModel):
    """Base Facebook credentials model."""

    facebook_user_id: str = Field(..., description="Facebook user ID")
    facebook_user_name: str = Field(..., description="Facebook user name")
    facebook_user_email: Optional[str] = Field(None, description="Facebook user email")


class FacebookCredentialsCreate(FacebookCredentialsBase):
    """Model for creating Facebook credentials."""

    user_id: int = Field(..., description="User ID")
    access_token: str = Field(..., description="Facebook access token")
    pages_data: Optional[List[Dict[str, Any]]] = Field(
        None, description="Facebook pages data"
    )
    instagram_accounts_data: Optional[List[Dict[str, Any]]] = Field(
        None, description="Instagram accounts data"
    )


class FacebookCredentialsUpdate(BaseModel):
    """Model for updating Facebook credentials."""

    access_token: Optional[str] = Field(None, description="Facebook access token")
    pages_data: Optional[List[Dict[str, Any]]] = Field(
        None, description="Facebook pages data"
    )
    instagram_accounts_data: Optional[List[Dict[str, Any]]] = Field(
        None, description="Instagram accounts data"
    )


class FacebookCredentialsResponse(FacebookCredentialsBase):
    """Model for Facebook credentials API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Credentials ID")
    user_id: int = Field(..., description="User ID")
    access_token: str = Field(..., description="Facebook access token")
    pages_data: Optional[List[Dict[str, Any]]] = Field(
        None, description="Facebook pages data"
    )
    instagram_accounts_data: Optional[List[Dict[str, Any]]] = Field(
        None, description="Instagram accounts data"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Database Operations Class
class DatabaseManager:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database connection pool and create tables."""
        self.pool = await asyncpg.create_pool(self.connection_string)
        await self.create_tables()

    async def create_tables(self):
        """Create all database tables."""
        async with self.pool.acquire() as conn:
            await conn.execute(DATABASE_SCHEMA)

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()

    # User operations
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO users (provider_id, email, name, picture, provider)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                user_data.provider_id,
                user_data.email,
                user_data.name,
                user_data.picture,
                user_data.provider,
            )
            return User.from_record(record)

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by internal ID."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            return User.from_record(record) if record else None

    async def get_user_by_provider_id(self, provider_id: str) -> Optional[User]:
        """Get user by provider ID."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM users WHERE provider_id = $1", provider_id
            )
            return User.from_record(record) if record else None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
            return User.from_record(record) if record else None

    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user information."""
        update_fields = []
        values = []
        param_count = 1

        if user_data.name is not None:
            update_fields.append(f"name = ${param_count}")
            values.append(user_data.name)
            param_count += 1

        if user_data.picture is not None:
            update_fields.append(f"picture = ${param_count}")
            values.append(user_data.picture)
            param_count += 1

        if not update_fields:
            return await self.get_user_by_id(user_id)

        values.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ${param_count} RETURNING *"

        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, *values)
            return User.from_record(record) if record else None

    async def update_user_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login = NOW() WHERE id = $1", user_id
            )

    # Session operations
    async def create_session(self, session_data: SessionCreate) -> Session:
        """Create a new session."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO sessions (id, user_id, provider_id, expires_at)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                session_data.id,
                session_data.user_id,
                session_data.provider_id,
                session_data.expires_at,
            )
            return Session.from_record(record)

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM sessions WHERE id = $1", session_id
            )
            return Session.from_record(record) if record else None

    async def delete_session(self, session_id: str) -> bool:
        """Delete session by ID."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM sessions WHERE id = $1", session_id
            )
            return result == "DELETE 1"

    async def delete_expired_sessions(self) -> int:
        """Delete all expired sessions."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM sessions WHERE expires_at < NOW()")
            return int(result.split()[1])

    # Business operations
    async def create_business(self, business_data: BusinessCreate) -> Business:
        """Create a new business."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO businesses (user_id, name, url, description)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                business_data.user_id,
                business_data.name,
                business_data.url,
                business_data.description,
            )
            return Business.from_record(record)

    async def get_business(self, business_id: int) -> Optional[Business]:
        """Get business by ID."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM businesses WHERE id = $1", business_id
            )
            return Business.from_record(record) if record else None

    async def get_businesses_by_user(self, user_id: int) -> List[Business]:
        """Get all businesses for a user."""
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT * FROM businesses WHERE user_id = $1", user_id
            )
            return [Business.from_record(record) for record in records]

    async def update_business(
        self, business_id: int, business_data: BusinessUpdate
    ) -> Optional[Business]:
        """Update business information."""
        update_fields = []
        values = []
        param_count = 1

        if business_data.name is not None:
            update_fields.append(f"name = ${param_count}")
            values.append(business_data.name)
            param_count += 1

        if business_data.url is not None:
            update_fields.append(f"url = ${param_count}")
            values.append(business_data.url)
            param_count += 1

        if business_data.description is not None:
            update_fields.append(f"description = ${param_count}")
            values.append(business_data.description)
            param_count += 1

        if not update_fields:
            return await self.get_business(business_id)

        values.append(business_id)
        query = f"UPDATE businesses SET {', '.join(update_fields)} WHERE id = ${param_count} RETURNING *"

        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, *values)
            return Business.from_record(record) if record else None

    async def delete_business(self, business_id: int) -> bool:
        """Delete business by ID."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM businesses WHERE id = $1", business_id
            )
            return result == "DELETE 1"

    # Facebook credentials operations
    async def create_facebook_credentials(
        self, creds_data: FacebookCredentialsCreate
    ) -> FacebookCredentials:
        """Create new Facebook credentials."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO facebook_credentials 
                (user_id, facebook_user_id, facebook_user_name, facebook_user_email, 
                 access_token, pages_data, instagram_accounts_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                creds_data.user_id,
                creds_data.facebook_user_id,
                creds_data.facebook_user_name,
                creds_data.facebook_user_email,
                creds_data.access_token,
                creds_data.pages_data,
                creds_data.instagram_accounts_data,
            )
            return FacebookCredentials.from_record(record)

    async def get_facebook_credentials_by_user(
        self, user_id: int
    ) -> Optional[FacebookCredentials]:
        """Get Facebook credentials for a user."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM facebook_credentials WHERE user_id = $1", user_id
            )
            return FacebookCredentials.from_record(record) if record else None

    async def update_facebook_credentials(
        self, user_id: int, creds_data: FacebookCredentialsUpdate
    ) -> Optional[FacebookCredentials]:
        """Update Facebook credentials."""
        update_fields = []
        values = []
        param_count = 1

        if creds_data.access_token is not None:
            update_fields.append(f"access_token = ${param_count}")
            values.append(creds_data.access_token)
            param_count += 1

        if creds_data.pages_data is not None:
            update_fields.append(f"pages_data = ${param_count}")
            values.append(creds_data.pages_data)
            param_count += 1

        if creds_data.instagram_accounts_data is not None:
            update_fields.append(f"instagram_accounts_data = ${param_count}")
            values.append(creds_data.instagram_accounts_data)
            param_count += 1

        if not update_fields:
            return await self.get_facebook_credentials_by_user(user_id)

        values.append(user_id)
        query = f"UPDATE facebook_credentials SET {', '.join(update_fields)} WHERE user_id = ${param_count} RETURNING *"

        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, *values)
            return FacebookCredentials.from_record(record) if record else None

    async def delete_facebook_credentials(self, user_id: int) -> bool:
        """Delete Facebook credentials for a user."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM facebook_credentials WHERE user_id = $1", user_id
            )
            return result == "DELETE 1"


# Example usage
async def main():
    """Example usage of the DatabaseManager."""
    # Initialize database manager
    db = DatabaseManager("postgresql://user:password@localhost/dbname")
    await db.initialize()

    try:
        # Create a user
        user_data = UserCreate(
            provider_id="google_123456",
            email="test@example.com",
            name="Test User",
            picture="https://example.com/pic.jpg",
        )
        user = await db.create_user(user_data)
        print(f"Created user: {user}")

        # Create a business
        business_data = BusinessCreate(
            user_id=user.id,
            name="Test Business",
            url="https://testbusiness.com",
            description="A test business",
        )
        business = await db.create_business(business_data)
        print(f"Created business: {business}")

        # Get user businesses
        businesses = await db.get_businesses_by_user(user.id)
        print(f"User businesses: {businesses}")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
