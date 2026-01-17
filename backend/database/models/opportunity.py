"""
Opportunity 모델

사업기회 파이프라인 단계 관리 테이블 정의
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.database.models.approval_request import ApprovalRequest
    from backend.database.models.brief import OpportunityBrief
    from backend.database.models.signal import Signal
    from backend.database.models.stage_transition import StageTransition

from sqlalchemy import JSON, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin


class OpportunityStage(enum.Enum):
    """사업기회 파이프라인 단계 (11단계)"""

    # 초기 단계 (01-05)
    DISCOVERY = "01_DISCOVERY"  # 01 발굴
    IDEA_CARD = "02_IDEA_CARD"  # 02 수집 (아이디어카드)
    GATE1_SELECTION = "03_GATE1"  # 03 선정 - HITL 필수
    MOCKUP = "04_MOCKUP"  # 04 형상화 (Mock-up)
    GATE2_VALIDATION = "05_GATE2"  # 05 사용자검증 - HITL 필수

    # 후기 단계 (06-09)
    BIZ_PLANNING = "06_BIZ_PLANNING"  # 06 사업기획·임원보고 - HITL 필수
    PILOT_POC = "07_PILOT"  # 07 파일럿/PoC
    PRE_PROPOSAL = "08_PRE_PROPOSAL"  # 08 선제안 (Pre-컨설팅) - HITL 필수
    HANDOFF = "09_HANDOFF"  # 09 실제안 (인계)

    # 비활성 상태
    HOLD = "HOLD"  # 보류
    DROP = "DROP"  # 중단


class Opportunity(Base, TimestampMixin):
    """
    Opportunity 테이블

    사업기회 파이프라인의 핵심 엔티티
    Signal, Brief를 하나의 Opportunity로 통합 관리
    """

    __tablename__ = "opportunities"

    # Primary Key
    opportunity_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # 기본 정보
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # 현재 단계
    current_stage: Mapped[OpportunityStage] = mapped_column(
        Enum(OpportunityStage),
        default=OpportunityStage.DISCOVERY,
        nullable=False,
    )

    # 관련 ID (Signal, Brief와 연결)
    signal_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("signals.signal_id", ondelete="SET NULL"),
        nullable=True,
    )

    brief_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("opportunity_briefs.brief_id", ondelete="SET NULL"),
        nullable=True,
    )

    # 소유자 및 Play 정보
    bd_owner: Mapped[str | None] = mapped_column(String(100))
    play_id: Mapped[str | None] = mapped_column(String(100))

    # 단계별 산출물 (JSON)
    # 각 단계에서 생성된 아티팩트 저장
    stage_artifacts: Mapped[dict | None] = mapped_column(JSON)

    # Gate 판정 이력 (JSON)
    # {"gate1": {"decision": "GO", "approver": "...", "approved_at": "..."}, ...}
    gate_decisions: Mapped[dict | None] = mapped_column(JSON)

    # 비활성 상태 사유
    hold_reason: Mapped[str | None] = mapped_column(Text)
    drop_reason: Mapped[str | None] = mapped_column(Text)

    # 태그
    tags: Mapped[list | None] = mapped_column(JSON)

    # Relationships
    signal: Mapped[Signal | None] = relationship(
        "Signal",
        foreign_keys=[signal_id],
        back_populates="opportunity",
    )

    brief: Mapped[OpportunityBrief | None] = relationship(
        "OpportunityBrief",
        foreign_keys=[brief_id],
        back_populates="opportunity",
    )

    transitions: Mapped[list[StageTransition]] = relationship(
        "StageTransition",
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="StageTransition.created_at.desc()",
    )

    approval_requests: Mapped[list[ApprovalRequest]] = relationship(
        "ApprovalRequest",
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="ApprovalRequest.created_at.desc()",
    )

    # Indexes
    __table_args__ = (
        Index("idx_opportunity_stage", "current_stage"),
        Index("idx_opportunity_signal_id", "signal_id"),
        Index("idx_opportunity_brief_id", "brief_id"),
        Index("idx_opportunity_bd_owner", "bd_owner"),
        Index("idx_opportunity_play_id", "play_id"),
        Index("idx_opportunity_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Opportunity(opportunity_id='{self.opportunity_id}', title='{self.title}', stage='{self.current_stage.value}')>"

    @property
    def is_active(self) -> bool:
        """활성 상태 여부"""
        return self.current_stage not in (OpportunityStage.HOLD, OpportunityStage.DROP)

    @property
    def stage_number(self) -> int | None:
        """현재 단계 번호 (01-09)"""
        stage_numbers = {
            OpportunityStage.DISCOVERY: 1,
            OpportunityStage.IDEA_CARD: 2,
            OpportunityStage.GATE1_SELECTION: 3,
            OpportunityStage.MOCKUP: 4,
            OpportunityStage.GATE2_VALIDATION: 5,
            OpportunityStage.BIZ_PLANNING: 6,
            OpportunityStage.PILOT_POC: 7,
            OpportunityStage.PRE_PROPOSAL: 8,
            OpportunityStage.HANDOFF: 9,
        }
        return stage_numbers.get(self.current_stage)
