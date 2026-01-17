"""
Scorecard 모델

Signal 평가 스코어카드 테이블 정의
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.database.models.signal import Signal

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class Decision(enum.Enum):
    """판정 결과"""

    GO = "GO"
    PIVOT = "PIVOT"
    HOLD = "HOLD"
    NO_GO = "NO_GO"


class NextStep(enum.Enum):
    """다음 단계"""

    BRIEF = "BRIEF"
    VALIDATION = "VALIDATION"
    PILOT_READY = "PILOT_READY"
    DROP = "DROP"
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"


class Scorecard(Base):
    """
    Scorecard 테이블

    Signal 정량 평가 결과 (100점 만점, 5개 차원)
    """

    __tablename__ = "scorecards"

    # Primary Key
    scorecard_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign Key
    signal_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("signals.signal_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1:1 관계
    )

    # 점수
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    dimension_scores: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 판정
    red_flags: Mapped[list | None] = mapped_column(JSON)
    recommendation: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 메타데이터
    scored_by: Mapped[str | None] = mapped_column(String(100))
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    signal: Mapped[Signal] = relationship("Signal", back_populates="scorecard")

    # Indexes
    __table_args__ = (
        Index("idx_scorecard_signal_id", "signal_id"),
        Index("idx_scorecard_total_score", "total_score"),
        Index("idx_scorecard_scored_at", "scored_at"),
    )

    def __repr__(self) -> str:
        return f"<Scorecard(scorecard_id='{self.scorecard_id}', total_score={self.total_score})>"
