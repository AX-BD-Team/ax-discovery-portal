"""
Triple 모델 템플릿

온톨로지 그래프의 관계(엣지)를 저장하는 테이블 정의
Subject-Predicate-Object (SPO) 구조

프로젝트에 맞게 PredicateType enum을 커스터마이징하세요.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.database.models.entity import Entity

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class PredicateType(enum.Enum):
    """
    관계 유형 정의

    프로젝트 도메인에 맞게 커스터마이징하세요.
    예시 카테고리:
    - Pipeline Flow: 파이프라인 단계 간 관계
    - Topic Relations: 주제/토픽 간 관계
    - Organization Relations: 조직/인물 간 관계
    - Evidence Relations: 근거/출처 관계
    - Operational Relations: 운영/작업 관계
    """

    # ===== Pipeline Flow Relations =====
    # {{PREDICATE_1}} = "{{predicate_1}}"
    # {{PREDICATE_2}} = "{{predicate_2}}"

    # ===== Topic Relations =====
    SIMILAR_TO = "similar_to"
    PARENT_OF = "parent_of"
    ADDRESSES = "addresses"

    # ===== Organization Relations =====
    TARGETS = "targets"
    EMPLOYS = "employs"
    PARTNERS_WITH = "partners_with"
    COMPETES_WITH = "competes_with"

    # ===== Evidence Relations =====
    SUPPORTED_BY = "supported_by"
    SOURCED_FROM = "sourced_from"
    INFERRED_FROM = "inferred_from"
    CONTRADICTS = "contradicts"

    # ===== Operational Relations =====
    SAME_AS = "same_as"


class TripleStatus(enum.Enum):
    """Triple 상태 (Lifecycle)"""

    PROPOSED = "proposed"  # 제안됨 - 검증 대기
    VERIFIED = "verified"  # 검증됨 - 신뢰 가능
    DEPRECATED = "deprecated"  # 폐기됨
    REJECTED = "rejected"  # 거부됨


class AssertionType(enum.Enum):
    """주장 유형"""

    OBSERVED = "observed"  # 증거에서 직접 관측
    INFERRED = "inferred"  # 규칙/LLM 추론 결과


class Triple(Base):
    """
    Triple 테이블

    온톨로지 그래프의 관계(엣지)를 저장하는 테이블
    Subject-Predicate-Object (SPO) 구조

    Lifecycle 관리:
    - status: proposed → verified (검증 통과) 또는 rejected (검증 실패)

    디버깅 가능성:
    - assertion_type: observed(직접 관측) vs inferred(추론)
    - evidence_ids: 근거 목록 (observed는 필수)
    - extractor_run_id: 생성한 파이프라인/모델 버전
    """

    __tablename__ = "triples"

    # Primary Key
    triple_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Subject (출발 엔티티)
    subject_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("entities.entity_id", ondelete="CASCADE"), nullable=False
    )

    # Predicate (관계 유형)
    predicate: Mapped[PredicateType] = mapped_column(Enum(PredicateType), nullable=False)

    # Object (도착 엔티티)
    object_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("entities.entity_id", ondelete="CASCADE"), nullable=False
    )

    # ===== Lifecycle 속성 =====
    status: Mapped[TripleStatus] = mapped_column(
        Enum(TripleStatus), default=TripleStatus.PROPOSED, nullable=False
    )
    assertion_type: Mapped[AssertionType] = mapped_column(
        Enum(AssertionType), default=AssertionType.OBSERVED, nullable=False
    )

    # ===== 신뢰도/강도 =====
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # ===== 근거 추적 =====
    evidence_ids: Mapped[list | None] = mapped_column(JSON, default=list)
    evidence_span: Mapped[dict | None] = mapped_column(JSON)

    # ===== 추적/디버깅 =====
    reasoning_path_id: Mapped[str | None] = mapped_column(String(50))
    extractor_run_id: Mapped[str | None] = mapped_column(String(100))
    properties: Mapped[dict | None] = mapped_column(JSON, default=dict)

    # ===== 타임스탬프 =====
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String(100))
    verified_by: Mapped[str | None] = mapped_column(String(100))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    subject: Mapped[Entity] = relationship("Entity", foreign_keys=[subject_id], lazy="joined")
    object: Mapped[Entity] = relationship("Entity", foreign_keys=[object_id], lazy="joined")

    # Indexes and Constraints
    __table_args__ = (
        Index("idx_triple_spo", "subject_id", "predicate", "object_id"),
        Index("idx_triple_pos", "predicate", "object_id", "subject_id"),
        Index("idx_triple_osp", "object_id", "subject_id", "predicate"),
        Index("idx_triple_subject", "subject_id"),
        Index("idx_triple_object", "object_id"),
        Index("idx_triple_predicate", "predicate"),
        Index("idx_triple_status", "status"),
        Index("idx_triple_status_predicate", "status", "predicate"),
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
            "status": self.status.value,
            "assertion_type": self.assertion_type.value,
            "weight": self.weight,
            "confidence": self.confidence,
            "evidence_ids": self.evidence_ids,
            "evidence_span": self.evidence_span,
            "reasoning_path_id": self.reasoning_path_id,
            "extractor_run_id": self.extractor_run_id,
            "properties": self.properties,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }

    def is_trustworthy(self) -> bool:
        """신뢰할 수 있는 관계인지"""
        return self.status == TripleStatus.VERIFIED and self.confidence >= 0.5
