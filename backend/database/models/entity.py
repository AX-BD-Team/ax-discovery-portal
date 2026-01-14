"""
Entity 모델

온톨로지 그래프의 노드(엔티티)를 저장하는 테이블 정의
"""

import enum
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Enum, Index, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class EntityType(enum.Enum):
    """엔티티 유형 (12종)"""
    # Core Entities
    SIGNAL = "Signal"
    TOPIC = "Topic"
    SCORECARD = "Scorecard"
    BRIEF = "Brief"

    # Context Entities
    CUSTOMER = "Customer"
    TECHNOLOGY = "Technology"
    COMPETITOR = "Competitor"
    INDUSTRY = "Industry"

    # Evidence Entities
    EVIDENCE = "Evidence"
    SOURCE = "Source"
    REASONING_STEP = "ReasoningStep"

    # Operational Entities
    PLAY = "Play"


class Entity(Base):
    """
    Entity 테이블

    온톨로지 그래프의 노드를 저장하는 테이블
    Subject-Predicate-Object 구조에서 Subject/Object 역할
    """

    __tablename__ = "entities"

    # Primary Key
    entity_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # 엔티티 유형
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType),
        nullable=False
    )

    # 기본 정보
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # 임베딩 (벡터 검색용) - JSON으로 저장, 실제 검색은 Vectorize 사용
    embedding: Mapped[Optional[list]] = mapped_column(JSON)

    # 신뢰도 (0.0 ~ 1.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # 메타데이터 (유형별 추가 속성)
    properties: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # 외부 참조 ID (기존 테이블과의 연결)
    # 예: Signal 엔티티면 signals 테이블의 signal_id
    external_ref_id: Mapped[Optional[str]] = mapped_column(String(100))

    # 생성/수정 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 생성자 (user_id 또는 agent_id)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))

    # Indexes
    __table_args__ = (
        Index("idx_entity_type", "entity_type"),
        Index("idx_entity_name", "name"),
        Index("idx_entity_external_ref", "external_ref_id"),
        Index("idx_entity_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Entity(entity_id='{self.entity_id}', type='{self.entity_type.value}', name='{self.name}')>"

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "description": self.description,
            "confidence": self.confidence,
            "properties": self.properties,
            "external_ref_id": self.external_ref_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }
