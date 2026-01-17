"""
Signal 모델

사업기회 신호(Signal) 테이블 정의
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.database.models.brief import OpportunityBrief
    from backend.database.models.opportunity import Opportunity
    from backend.database.models.scorecard import Scorecard

from sqlalchemy import JSON, Enum, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin


class SignalSource(enum.Enum):
    """Signal 원천 (3원천)"""

    KT = "KT"
    GROUP = "그룹사"
    EXTERNAL = "대외"


class SignalChannel(enum.Enum):
    """Signal 채널 (5채널)"""

    DESK_RESEARCH = "데스크리서치"
    INTERNAL_ACTIVITY = "자사활동"
    SALES_PM = "영업PM"
    INBOUND = "인바운드"
    OUTBOUND = "아웃바운드"


class SignalStatus(enum.Enum):
    """Signal 상태"""

    NEW = "NEW"
    SCORING = "SCORING"
    SCORED = "SCORED"
    BRIEF_CREATED = "BRIEF_CREATED"
    VALIDATED = "VALIDATED"
    PILOT_READY = "PILOT_READY"
    ARCHIVED = "ARCHIVED"


class Signal(Base, TimestampMixin):
    """
    Signal 테이블

    사업기회 신호를 저장하는 메인 테이블
    """

    __tablename__ = "signals"

    # Primary Key
    signal_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # 기본 정보
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[SignalSource] = mapped_column(Enum(SignalSource), nullable=False)
    channel: Mapped[SignalChannel] = mapped_column(Enum(SignalChannel), nullable=False)
    play_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # 고객 및 Pain Point
    customer_segment: Mapped[str | None] = mapped_column(String(200))
    pain: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_value: Mapped[str | None] = mapped_column(Text)

    # KPI 및 근거
    kpi_hypothesis: Mapped[list | None] = mapped_column(JSON)
    evidence: Mapped[list | None] = mapped_column(JSON)
    tags: Mapped[list | None] = mapped_column(JSON)

    # 상태 및 메타데이터
    status: Mapped[SignalStatus] = mapped_column(
        Enum(SignalStatus), default=SignalStatus.NEW, nullable=False
    )
    owner: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[float | None] = mapped_column(Float)

    # Relationships
    scorecard: Mapped[Scorecard | None] = relationship(
        "Scorecard", back_populates="signal", uselist=False, cascade="all, delete-orphan"
    )

    brief: Mapped[OpportunityBrief | None] = relationship(
        "OpportunityBrief", back_populates="signal", uselist=False, cascade="all, delete-orphan"
    )

    opportunity: Mapped[Opportunity | None] = relationship(
        "Opportunity",
        back_populates="signal",
        uselist=False,
        foreign_keys="Opportunity.signal_id",
    )

    # Indexes
    __table_args__ = (
        Index("idx_signal_status", "status"),
        Index("idx_signal_source", "source"),
        Index("idx_signal_channel", "channel"),
        Index("idx_signal_play_id", "play_id"),
        Index("idx_signal_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Signal(signal_id='{self.signal_id}', title='{self.title}', status='{self.status.value}')>"
