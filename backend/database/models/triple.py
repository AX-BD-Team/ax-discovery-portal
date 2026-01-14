"""
Triple 모델

온톨로지 그래프의 관계(엣지)를 저장하는 테이블 정의
Subject-Predicate-Object (SPO) 구조
"""

import enum
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Enum, Index, JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class PredicateType(enum.Enum):
    """관계 유형 (15종)"""
    # 핵심 관계
    HAS_PAIN = "has_pain"                 # Signal -> Topic
    HAS_SCORECARD = "has_scorecard"       # Signal -> Scorecard
    HAS_BRIEF = "has_brief"               # Signal -> Brief
    BELONGS_TO_PLAY = "belongs_to_play"   # Signal -> Play

    # 토픽 관계
    SIMILAR_TO = "similar_to"             # Topic <-> Topic (양방향)
    PARENT_OF = "parent_of"               # Topic -> Topic (계층)
    RELATED_TO = "related_to"             # Topic -> Topic (연관)

    # 맥락 관계
    TARGETS = "targets"                   # Signal -> Customer
    USES_TECHNOLOGY = "uses_technology"   # Signal -> Technology
    COMPETES_WITH = "competes_with"       # Signal -> Competitor
    IN_INDUSTRY = "in_industry"           # Signal -> Industry

    # 증거 관계
    SUPPORTED_BY = "supported_by"         # Signal -> Evidence
    SOURCED_FROM = "sourced_from"         # Evidence -> Source
    INFERRED_FROM = "inferred_from"       # ReasoningStep -> Evidence[]
    LEADS_TO = "leads_to"                 # ReasoningStep -> ReasoningStep


class Triple(Base):
    """
    Triple 테이블

    온톨로지 그래프의 관계(엣지)를 저장하는 테이블
    Subject-Predicate-Object (SPO) 구조로 유연한 관계 표현
    """

    __tablename__ = "triples"

    # Primary Key
    triple_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Subject (출발 엔티티)
    subject_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False
    )

    # Predicate (관계 유형)
    predicate: Mapped[PredicateType] = mapped_column(
        Enum(PredicateType),
        nullable=False
    )

    # Object (도착 엔티티)
    object_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False
    )

    # 관계 강도 (0.0 ~ 1.0)
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    # 신뢰도 (0.0 ~ 1.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # 근거 Evidence ID 목록
    evidence_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # 추론 경로 ID (이 관계가 어떤 추론에서 도출되었는지)
    reasoning_path_id: Mapped[Optional[str]] = mapped_column(String(50))

    # 메타데이터 (추가 속성)
    properties: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # 생성 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 생성자 (user_id 또는 agent_id)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))

    # Relationships
    subject: Mapped["Entity"] = relationship(
        "Entity",
        foreign_keys=[subject_id],
        lazy="joined"
    )

    object: Mapped["Entity"] = relationship(
        "Entity",
        foreign_keys=[object_id],
        lazy="joined"
    )

    # Indexes and Constraints
    __table_args__ = (
        # SPO 인덱스 (특정 주어의 관계 탐색)
        Index("idx_triple_spo", "subject_id", "predicate", "object_id"),
        # POS 인덱스 (특정 관계 유형으로 대상 찾기)
        Index("idx_triple_pos", "predicate", "object_id", "subject_id"),
        # OSP 인덱스 (특정 대상을 참조하는 관계 찾기)
        Index("idx_triple_osp", "object_id", "subject_id", "predicate"),
        # 추가 인덱스
        Index("idx_triple_subject", "subject_id"),
        Index("idx_triple_object", "object_id"),
        Index("idx_triple_predicate", "predicate"),
        Index("idx_triple_created_at", "created_at"),
        Index("idx_triple_confidence", "confidence"),
        # 중복 방지 (동일 관계는 하나만)
        UniqueConstraint("subject_id", "predicate", "object_id", name="uq_triple_spo"),
    )

    def __repr__(self) -> str:
        return f"<Triple({self.subject_id} --[{self.predicate.value}]--> {self.object_id})>"

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "triple_id": self.triple_id,
            "subject_id": self.subject_id,
            "predicate": self.predicate.value,
            "object_id": self.object_id,
            "weight": self.weight,
            "confidence": self.confidence,
            "evidence_ids": self.evidence_ids,
            "reasoning_path_id": self.reasoning_path_id,
            "properties": self.properties,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }

    def to_dict_with_entities(self) -> dict:
        """엔티티 정보 포함하여 딕셔너리로 변환"""
        result = self.to_dict()
        if self.subject:
            result["subject"] = {
                "entity_id": self.subject.entity_id,
                "entity_type": self.subject.entity_type.value,
                "name": self.subject.name,
            }
        if self.object:
            result["object"] = {
                "entity_id": self.object.entity_id,
                "entity_type": self.object.entity_type.value,
                "name": self.object.name,
            }
        return result
