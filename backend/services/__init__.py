"""
Services 모듈

비즈니스 로직을 처리하는 서비스 레이어
"""

from backend.services.embedding_service import EmbeddingService, embedding_service

__all__ = ["EmbeddingService", "embedding_service"]
