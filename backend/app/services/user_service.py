from datetime import datetime
from typing import Optional, Dict, Any, List
import asyncpg

from ..models.auth import User
from ..models.database import UserResponse


class UserService:
    def __init__(self):
        pass

    async def create_or_update_user(
        self, user_data: User, db: asyncpg.Connection
    ) -> UserResponse:
        """Create a new user or update existing user in PostgreSQL"""
        # Check if user already exists
        existing_user = await db.fetchrow(
            "SELECT * FROM users WHERE provider_id = $1", user_data.provider_id
        )

        if existing_user:
            # Update existing user
            updated_user = await db.fetchrow(
                """
                UPDATE users 
                SET name = $1, email = $2, picture = $3, last_login = $4, updated_at = $5
                WHERE provider_id = $6
                RETURNING *
                """,
                user_data.name,
                user_data.email,
                str(user_data.picture) if user_data.picture else None,
                datetime.utcnow(),
                datetime.utcnow(),
                user_data.provider_id,
            )
            return UserResponse(**dict(updated_user))
        else:
            # Create new user
            new_user = await db.fetchrow(
                """
                INSERT INTO users (id, provider_id, email, name, picture, provider, is_active, created_at, updated_at, last_login)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
                """,
                user_data.provider_id,  # Use provider_id as the main id
                user_data.provider_id,
                user_data.email,
                user_data.name,
                str(user_data.picture) if user_data.picture else None,
                user_data.provider,
                True,
                datetime.utcnow(),
                datetime.utcnow(),
                datetime.utcnow(),
            )
            return UserResponse(**dict(new_user))

    async def get_user_by_provider_id(
        self, provider_id: str, db: asyncpg.Connection
    ) -> Optional[asyncpg.Record]:
        """Get user by provider ID"""
        return await db.fetchrow(
            "SELECT * FROM users WHERE provider_id = $1 AND is_active = true",
            provider_id,
        )

    async def get_user_by_email(
        self, email: str, db: asyncpg.Connection
    ) -> Optional[asyncpg.Record]:
        """Get user by email"""
        return await db.fetchrow(
            "SELECT * FROM users WHERE email = $1 AND is_active = true", email
        )

    async def get_user_by_id(
        self, user_id: int, db: asyncpg.Connection
    ) -> Optional[asyncpg.Record]:
        """Get user by internal ID"""
        return await db.fetchrow(
            "SELECT * FROM users WHERE id = $1 AND is_active = true", user_id
        )

    async def update_last_login(self, provider_id: str, db: asyncpg.Connection) -> bool:
        """Update user's last login timestamp"""
        result = await db.execute(
            """
            UPDATE users 
            SET last_login = $1, updated_at = $2
            WHERE provider_id = $3 AND is_active = true
            """,
            datetime.utcnow(),
            datetime.utcnow(),
            provider_id,
        )
        return result != "UPDATE 0"

    async def deactivate_user(self, provider_id: str, db: asyncpg.Connection) -> bool:
        """Deactivate a user (soft delete)"""
        result = await db.execute(
            """
            UPDATE users 
            SET is_active = false, updated_at = $1
            WHERE provider_id = $2
            """,
            datetime.utcnow(),
            provider_id,
        )
        return result != "UPDATE 0"

    async def get_user_stats(
        self, provider_id: str, db: asyncpg.Connection
    ) -> Optional[Dict[str, Any]]:
        """Get user statistics"""
        user = await db.fetchrow(
            "SELECT * FROM users WHERE provider_id = $1", provider_id
        )

        if not user:
            return None

        return {
            "user_id": user["id"],
            "provider_id": user["provider_id"],
            "email": user["email"],
            "name": user["name"],
            "provider": user["provider"],
            "created_at": (
                user["created_at"].isoformat() if user["created_at"] else None
            ),
            "last_login": (
                user["last_login"].isoformat() if user["last_login"] else None
            ),
            "is_active": user["is_active"],
            "days_since_signup": (
                (datetime.utcnow() - user["created_at"]).days
                if user["created_at"]
                else 0
            ),
        }

    async def list_users(
        self,
        db: asyncpg.Connection,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> List[UserResponse]:
        """List users with pagination"""
        if active_only:
            query = "SELECT * FROM users WHERE is_active = true OFFSET $1 LIMIT $2"
        else:
            query = "SELECT * FROM users OFFSET $1 LIMIT $2"

        users = await db.fetch(query, skip, limit)
        return [UserResponse(**dict(user)) for user in users]

    async def count_users(
        self, db: asyncpg.Connection, active_only: bool = True
    ) -> int:
        """Count total users"""
        if active_only:
            query = "SELECT COUNT(*) FROM users WHERE is_active = true"
        else:
            query = "SELECT COUNT(*) FROM users"

        result = await db.fetchval(query)
        return result or 0


# Global instance
user_service = UserService()
