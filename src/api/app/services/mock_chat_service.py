"""
In-memory chat service for local development when Cosmos DB is not configured.
Enables demo/testing without Azure infrastructure.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from ..models import (
        ChatMessage,
        ChatMessageCreate,
        ChatMessageType,
        ChatSession,
        ChatSessionCreate,
    )
except ImportError:
    from app.models import (
        ChatMessage,
        ChatMessageCreate,
        ChatMessageType,
        ChatSession,
        ChatSessionCreate,
    )

logger = logging.getLogger(__name__)

# In-memory store: session_id -> ChatSession
_sessions: Dict[str, ChatSession] = {}


class MockChatService:
    """In-memory chat session store for local dev without Cosmos DB."""

    async def create_chat_session(self, session: ChatSessionCreate) -> ChatSession:
        new_session = ChatSession(
            id=str(uuid.uuid4()),
            user_id=session.user_id,
            session_name=session.session_name
            or f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            context=session.context,
            messages=[],
            message_count=0,
        )
        _sessions[new_session.id] = new_session
        logger.info("MockChatService: created session %s", new_session.id)
        return new_session

    async def get_chat_session(
        self, session_id: str, user_id: Optional[str] = None
    ) -> Optional[ChatSession]:
        session = _sessions.get(session_id)
        if session and (user_id is None or session.user_id == user_id):
            return session
        return None

    async def add_message_to_session(
        self, session_id: str, message: ChatMessageCreate, user_id: Optional[str] = None
    ) -> ChatSession:
        session = _sessions.get(session_id)
        if not session:
            session = ChatSession(
                id=session_id,
                user_id=user_id,
                session_name=f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                context={},
                messages=[],
                message_count=0,
            )
            _sessions[session_id] = session

        new_msg = ChatMessage(
            content=message.content,
            message_type=message.message_type or ChatMessageType.USER,
            user_id=user_id,
            metadata=message.metadata,
        )
        session.messages.append(new_msg)
        session.message_count = len(session.messages)
        session.last_message_at = new_msg.created_at
        return session

    async def get_chat_sessions_by_user(self, user_id: str) -> List[ChatSession]:
        return [
            s
            for s in _sessions.values()
            if s.user_id == user_id
        ]

    async def update_chat_session(
        self, session_id: str, update: Any, user_id: Optional[str] = None
    ) -> Optional[ChatSession]:
        session = _sessions.get(session_id)
        if not session or (user_id and session.user_id != user_id):
            return None
        if hasattr(update, "session_name") and update.session_name:
            session.session_name = update.session_name
        if hasattr(update, "is_active") and update.is_active is not None:
            session.is_active = update.is_active
        return session

    async def delete_chat_session(
        self, session_id: str, user_id: Optional[str] = None
    ) -> bool:
        session = _sessions.get(session_id)
        if not session or (user_id and session.user_id != user_id):
            return False
        del _sessions[session_id]
        return True
