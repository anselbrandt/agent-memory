from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import uuid

from pydantic import ValidationError

from ..db import get_redis
from ..models.auth import SessionData


class SessionService:
    def __init__(self):
        self._redis = None
        self._use_redis = True
        self._memory_store = {}  # Fallback in-memory store
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"

    @property
    def redis(self):
        if self._redis is None and self._use_redis:
            try:
                self._redis = get_redis()
                # Test the connection
                self._redis.ping()
            except Exception as e:
                self._use_redis = False
                self._redis = None
        return self._redis

    def _get_session_key(self, session_id: str) -> str:
        return f"{self.session_prefix}{session_id}"

    def _set_data(self, key: str, value: str, expire_seconds: int = None):
        """Set data in Redis or memory store"""
        if self._use_redis and self.redis:
            redis_client = self.redis
            if expire_seconds:
                redis_client.setex(key, expire_seconds, value)
            else:
                redis_client.set(key, value)
        else:
            # Use memory store with expiration
            expire_at = (
                datetime.utcnow() + timedelta(seconds=expire_seconds)
                if expire_seconds
                else None
            )
            self._memory_store[key] = {"value": value, "expire_at": expire_at}

    def _get_data(self, key: str) -> Optional[str]:
        """Get data from Redis or memory store"""
        if self._use_redis and self.redis:
            redis_client = self.redis
            return redis_client.get(key)
        else:
            # Check memory store
            if key in self._memory_store:
                item = self._memory_store[key]
                if item["expire_at"] and datetime.utcnow() > item["expire_at"]:
                    del self._memory_store[key]
                    return None
                return item["value"]
            return None

    def _delete_data(self, key: str) -> bool:
        """Delete data from Redis or memory store"""
        if self._use_redis and self.redis:
            redis_client = self.redis
            return bool(redis_client.delete(key))
        else:
            if key in self._memory_store:
                del self._memory_store[key]
                return True
            return False

    def generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return str(uuid.uuid4())

    def create_session(
        self, user_data: Dict[str, Any], expires_in_days: int = 7
    ) -> str:
        """Create a new session and store it"""
        session_id = self.generate_session_id()
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create validated session data using Pydantic model
        session_data = SessionData(
            id=user_data.get("id"),
            provider_id=user_data.get("provider_id"),
            email=user_data.get("email"),
            name=user_data.get("name"),
            picture=user_data.get("picture"),
            provider=user_data.get("provider"),
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )

        # Store session data
        session_key = self._get_session_key(session_id)
        expire_seconds = expires_in_days * 24 * 60 * 60
        self._set_data(
            session_key, session_data.model_dump_json(), expire_seconds
        )

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data"""
        session_key = self._get_session_key(session_id)
        session_data = self._get_data(session_key)

        if not session_data:
            return None

        # Parse and validate session data using Pydantic model
        try:
            parsed_data = SessionData.model_validate_json(session_data)
        except ValidationError:
            self.delete_session(session_id)
            return None

        # Check if session is expired
        if datetime.utcnow() > parsed_data.expires_at:
            self.delete_session(session_id)
            return None

        return parsed_data.model_dump()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        session_key = self._get_session_key(session_id)
        return self._delete_data(session_key)

    async def delete_user_sessions(self, provider_id: str) -> int:
        """Delete all sessions for a user"""
        if not (self._use_redis and await self.redis):
            return 0

        redis_client = await self.redis
        user_sessions_key = f"{self.user_sessions_prefix}{provider_id}"
        session_ids = await redis_client.smembers(user_sessions_key)

        deleted_count = 0
        for session_id in session_ids:
            session_key = f"{self.session_prefix}{session_id}"
            if await redis_client.delete(session_key):
                deleted_count += 1

        # Clear the user sessions set
        await redis_client.delete(user_sessions_key)

        return deleted_count

    def refresh_session(self, session_id: str, expires_in_days: int = 7) -> bool:
        """Refresh session expiration"""
        session_data = self.get_session(session_id)
        if not session_data:
            return False

        # Update expiration
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        session_data["expires_at"] = expires_at.isoformat()

        if not (self._use_redis and self.redis):
            return False

        redis_client = self.redis
        session_key = f"{self.session_prefix}{session_id}"
        expire_seconds = expires_in_days * 24 * 60 * 60
        redis_client.setex(
            session_key, expire_seconds, json.dumps(session_data)
        )

        return True

    async def get_user_sessions(self, provider_id: str) -> list:
        """Get all active sessions for a user"""
        if not (self._use_redis and await self.redis):
            return []

        redis_client = await self.redis
        user_sessions_key = f"{self.user_sessions_prefix}{provider_id}"
        session_ids = await redis_client.smembers(user_sessions_key)

        active_sessions = []
        for session_id in session_ids:
            session_data = await self.get_session(session_id)
            if session_data:
                active_sessions.append(
                    {
                        "session_id": session_id,
                        "created_at": session_data.get("created_at"),
                        "expires_at": session_data.get("expires_at"),
                    }
                )

        return active_sessions


# Global instance
session_service = SessionService()
