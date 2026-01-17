"""
OpportunityBrief 모델

1-Page Opportunity Brief 테이블 정의
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.database.models.opportunity import Opportunity
    from backend.database.models.signal import Signal

from sqlalchemy import JSON, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin


class ValidationMethod(enum.Enum):
    """검증 방법"""

    FIVE_DAY_SPRINT = "5DAY_SPRINT"
    INTERVIEW = "INTERVIEW"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    BUYER_REVIEW = "BUYER_REVIEW"
    POC = "POC"


class BriefStatus(enum.Enum):
    """Brief 상태"""

    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    VALIDATED = "VALIDATED"
    PILOT_READY = "PILOT_READY"
    ARCHIVED = "ARCHIVED"


class OpportunityBrief(Base, TimestampMixin):
    """
    OpportunityBrief 테이블

    1-Page Opportunity Brief 문서
    """

    __tablename__ = "opportunity_briefs"

    # Primary Key
    brief_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign Key
    signal_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("signals.signal_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1:1 관계
    )

    # 기본 정보
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # 고객 정보 (JSON)
    customer: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 문제 정의 (JSON)
    problem: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 솔루션 가설 (JSON)
    solution_hypothesis: Mapped[dict] = mapped_column(JSON, nullable=False)

    # KPI 및 근거
    kpis: Mapped[list] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False)

    # 검증 계획 (JSON)
    validation_plan: Mapped[dict] = mapped_column(JSON, nullable=False)

    # MVP 범위 (JSON, optional)
    mvp_scope: Mapped[dict | None] = mapped_column(JSON)

    # 리스크
    risks: Mapped[list | None] = mapped_column(JSON)

    # 상태 및 메타데이터
    status: Mapped[BriefStatus] = mapped_column(
        Enum(BriefStatus), default=BriefStatus.DRAFT, nullable=False
    )
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    confluence_url: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    signal: Mapped[Signal] = relationship("Signal", back_populates="brief")

    opportunity: Mapped[Opportunity | None] = relationship(
        "Opportunity",
        back_populates="brief",
        uselist=False,
        foreign_keys="Opportunity.brief_id",
    )

    # Indexes
    __table_args__ = (
        Index("idx_brief_signal_id", "signal_id"),
        Index("idx_brief_status", "status"),
        Index("idx_brief_owner", "owner"),
        Index("idx_brief_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<OpportunityBrief(brief_id='{self.brief_id}', title='{self.title}', status='{self.status.value}')>"
