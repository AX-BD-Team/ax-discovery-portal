"""
Triple 모델

온톨로지 그래프의 관계(엣지)를 저장하는 테이블 정의
Subject-Predicate-Object (SPO) 구조

Triple Lifecycle:
- proposed: LLM/추출기가 생성, 검증 대기
- verified: 규칙 검증 통과 또는 사람이 승인
- deprecated: 더 이상 유효하지 않음 (대체됨)
- rejected: 검증 실패로 거부됨
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
    """관계 유형 (28종) - BD 특화 온톨로지 v2"""

    # ===== Pipeline Flow Relations (6종) =====
    GENERATES = "generates"  # v2: Activity -> Signal
    EVALUATES_TO = "evaluates_to"  # v2: Signal -> Scorecard
    SUMMARIZED_IN = "summarized_in"  # v2: Signal -> Brief
    VALIDATED_BY = "validated_by"  # v2: Brief -> Validation
    PILOTS_AS = "pilots_as"  # v2: Validation -> Pilot
    PROGRESSES_TO = "progresses_to"  # v2: 단계 전환 (일반)

    # ===== Topic Relations (4종) =====
    HAS_PAIN = "has_pain"  # Signal -> Topic
    SIMILAR_TO = "similar_to"  # Topic <-> Topic (양방향)
    PARENT_OF = "parent_of"  # Topic -> Topic (계층)
    ADDRESSES = "addresses"  # v2: Technology -> Topic (해결하는 Pain)

    # ===== Organization Relations (6종) =====
    TARGETS = "targets"  # Signal -> Organization
    EMPLOYS = "employs"  # v2: Organization -> Person
    PARTNERS_WITH = "partners_with"  # v2: Organization <-> Organization
    COMPETES_WITH = "competes_with"  # Organization <-> Organization
    SUBSIDIARY_OF = "subsidiary_of"  # v2: Organization -> Organization
    IN_INDUSTRY = "in_industry"  # Organization -> Industry

    # ===== Person Relations (4종) =====
    OWNS = "owns"  # v2: Person -> Signal/Brief (소유자)
    DECIDES = "decides"  # v2: Person -> Decision
    ATTENDED = "attended"  # v2: Person -> Meeting
    REPORTS_TO = "reports_to"  # v2: Person -> Person

    # ===== Evidence Relations (4종) =====
    SUPPORTED_BY = "supported_by"  # Any -> Evidence
    SOURCED_FROM = "sourced_from"  # Evidence -> Source
    INFERRED_FROM = "inferred_from"  # Any -> ReasoningStep
    CONTRADICTS = "contradicts"  # v2: Evidence <-> Evidence

    # ===== Operational Relations (4종) =====
    BELONGS_TO_PLAY = "belongs_to_play"  # Signal -> Play
    SCHEDULED_FOR = "scheduled_for"  # v2: Task -> Meeting
    ACHIEVES = "achieves"  # v2: Task -> Milestone
    SAME_AS = "same_as"  # Entity <-> Entity (동일 실체)

    # ===== Deprecated (하위 호환용) =====
    HAS_SCORECARD = "has_scorecard"  # deprecated: use EVALUATES_TO
    HAS_BRIEF = "has_brief"  # deprecated: use SUMMARIZED_IN
    RELATED_TO = "related_to"  # deprecated: use more specific relations
    USES_TECHNOLOGY = "uses_technology"  # deprecated: use ADDRESSES
    HAS_ROLE = "has_role"  # deprecated: use EMPLOYS + role property
    LEADS_TO = "leads_to"  # deprecated: use PROGRESSES_TO


class TripleStatus(enum.Enum):
    """Triple 상태 (Lifecycle)"""

    PROPOSED = "proposed"  # 제안됨 - 검증 대기
    VERIFIED = "verified"  # 검증됨 - 신뢰 가능
    DEPRECATED = "deprecated"  # 폐기됨 - 더 이상 유효하지 않음
    REJECTED = "rejected"  # 거부됨 - 검증 실패


class AssertionType(enum.Enum):
    """주장 유형"""

    OBSERVED = "observed"  # 증거에서 직접 관측
    INFERRED = "inferred"  # 규칙/LLM 추론 결과


class Triple(Base):
    """
    Triple 테이블

    온톨로지 그래프의 관계(엣지)를 저장하는 테이블
    Subject-Predicate-Object (SPO) 구조로 유연한 관계 표현

    Lifecycle 관리:
    - status: proposed → verified (검증 통과) 또는 rejected (검증 실패)
    - deprecated: 더 이상 유효하지 않을 때

    디버깅 가능성:
    - assertion_type: observed(직접 관측) vs inferred(추론)
    - evidence_ids: 근거 목록 (observed는 필수)
    - evidence_span: 근거 텍스트 위치/인용
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

    # ===== Lifecycle 속성 (P0) =====
    # Triple 상태 (proposed → verified/rejected)
    status: Mapped[TripleStatus] = mapped_column(
        Enum(TripleStatus), default=TripleStatus.PROPOSED, nullable=False
    )

    # 주장 유형: observed(직접 관측) vs inferred(추론)
    assertion_type: Mapped[AssertionType] = mapped_column(
        Enum(AssertionType), default=AssertionType.OBSERVED, nullable=False
    )

    # ===== 신뢰도/강도 =====
    # 관계 강도 (0.0 ~ 1.0)
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    # 신뢰도 (0.0 ~ 1.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # ===== 근거 추적 (P0: 근거 없는 관계 = 가설) =====
    # 근거 Evidence ID 목록 (observed는 최소 1개 필수)
    evidence_ids: Mapped[list | None] = mapped_column(JSON, default=list)

    # 근거 텍스트 위치/인용 (디버깅용)
    # 예: {"source_id": "src-001", "start": 100, "end": 200, "text": "..."}
    evidence_span: Mapped[dict | None] = mapped_column(JSON)

    # ===== 추적/디버깅 =====
    # 추론 경로 ID (이 관계가 어떤 추론에서 도출되었는지)
    reasoning_path_id: Mapped[str | None] = mapped_column(String(50))

    # 추출기 실행 ID (어떤 파이프라인/모델/프롬프트 버전으로 생성됐는지)
    extractor_run_id: Mapped[str | None] = mapped_column(String(100))

    # 메타데이터 (추가 속성, 역할 정보 등)
    # HAS_ROLE의 경우: {"role": "customer|competitor|partner", "context": "..."}
    properties: Mapped[dict | None] = mapped_column(JSON, default=dict)

    # ===== 타임스탬프 =====
    # 생성 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # 수정 시각
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # 생성자 (user_id 또는 agent_id)
    created_by: Mapped[str | None] = mapped_column(String(100))

    # 검증자 (verified/rejected로 변경한 사람)
    verified_by: Mapped[str | None] = mapped_column(String(100))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    subject: Mapped[Entity] = relationship("Entity", foreign_keys=[subject_id], lazy="joined")

    object: Mapped[Entity] = relationship("Entity", foreign_keys=[object_id], lazy="joined")

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
        # Lifecycle 인덱스 (P0: verified만 쿼리)
        Index("idx_triple_status", "status"),
        Index("idx_triple_assertion_type", "assertion_type"),
        # 복합 인덱스: status + predicate (BFS 안전모드용)
        Index("idx_triple_status_predicate", "status", "predicate"),
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
            # Lifecycle
            "status": self.status.value,
            "assertion_type": self.assertion_type.value,
            # 신뢰도
            "weight": self.weight,
            "confidence": self.confidence,
            # 근거
            "evidence_ids": self.evidence_ids,
            "evidence_span": self.evidence_span,
            # 추적
            "reasoning_path_id": self.reasoning_path_id,
            "extractor_run_id": self.extractor_run_id,
            "properties": self.properties,
            # 타임스탬프
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }

    def is_hypothesis(self) -> bool:
        """근거 없는 추론인지 (가설 취급)"""
        return self.assertion_type == AssertionType.INFERRED and (
            not self.evidence_ids or len(self.evidence_ids) == 0
        )

    def is_trustworthy(self) -> bool:
        """신뢰할 수 있는 관계인지 (BFS에서 사용)"""
        return self.status == TripleStatus.VERIFIED and self.confidence >= 0.5

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
