"""
StageTransition 모델

단계 전환 이력 테이블 정의
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.database.models.opportunity import Opportunity

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin


class TransitionTrigger(enum.Enum):
    """전환 트리거 유형"""

    AUTO = "AUTO"  # 자동 전환 (워크플로 완료 등)
    MANUAL = "MANUAL"  # 수동 전환 (사용자 요청)
    GATE = "GATE"  # Gate 승인에 의한 전환


class GateDecision(enum.Enum):
    """Gate 판정"""

    GO = "GO"  # 통과 → 다음 단계
    HOLD = "HOLD"  # 보류 → HOLD 상태
    STOP = "STOP"  # 중단 → DROP 상태


class StageTransition(Base, TimestampMixin):
    """
    StageTransition 테이블

    Opportunity의 단계 전환 이력 추적
    """

    __tablename__ = "stage_transitions"

    # Primary Key
    transition_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign Key
    opportunity_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("opportunities.opportunity_id", ondelete="CASCADE"),
        nullable=False,
    )

    # 전환 정보
    from_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)

    # 트리거 정보
    trigger: Mapped[TransitionTrigger] = mapped_column(
        Enum(TransitionTrigger),
        default=TransitionTrigger.MANUAL,
        nullable=False,
    )

    # Gate 관련 정보 (GATE 트리거인 경우)
    gate_decision: Mapped[GateDecision | None] = mapped_column(Enum(GateDecision))
    gate_comments: Mapped[str | None] = mapped_column(Text)

    # 승인자 정보
    approver: Mapped[str | None] = mapped_column(String(100))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 메타데이터
    triggered_by: Mapped[str | None] = mapped_column(String(100))  # 전환 요청자
    notes: Mapped[str | None] = mapped_column(Text)  # 전환 사유/메모

    # Relationships
    opportunity: Mapped[Opportunity] = relationship(
        "Opportunity",
        back_populates="transitions",
    )

    # Indexes
    __table_args__ = (
        Index("idx_transition_opportunity_id", "opportunity_id"),
        Index("idx_transition_from_stage", "from_stage"),
        Index("idx_transition_to_stage", "to_stage"),
        Index("idx_transition_trigger", "trigger"),
        Index("idx_transition_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<StageTransition(transition_id='{self.transition_id}', {self.from_stage} → {self.to_stage})>"
