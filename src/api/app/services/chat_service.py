"""
Chat service factory: returns Cosmos-backed or in-memory chat service based on config.
Enables local demo without Cosmos DB.
"""
import logging

from ..config import has_cosmos_db_config

logger = logging.getLogger(__name__)

_chat_service = None


def get_chat_service():
    """Get chat service: Cosmos when configured, in-memory mock otherwise."""
    global _chat_service
    if _chat_service is not None:
        return _chat_service

    if has_cosmos_db_config():
        try:
            from ..cosmos_service import get_cosmos_service
            _chat_service = get_cosmos_service()
            logger.info("Chat service: using Cosmos DB")
            return _chat_service
        except Exception as e:
            logger.warning("Cosmos DB init failed, falling back to in-memory: %s", e)

    from .mock_chat_service import MockChatService
    _chat_service = MockChatService()
    logger.info("Chat service: using in-memory (Cosmos not configured)")
    return _chat_service
