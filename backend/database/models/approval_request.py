"""
ApprovalRequest 모델

HITL 승인 요청 테이블 정의
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.database.models.opportunity import Opportunity

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin


class ApprovalStatus(enum.Enum):
    """승인 상태"""

    PENDING = "PENDING"  # 대기 중
    APPROVED = "APPROVED"  # 승인됨
    REJECTED = "REJECTED"  # 거부됨
    EXPIRED = "EXPIRED"  # 만료됨


class ApprovalType(enum.Enum):
    """승인 유형"""

    GATE1 = "GATE1"  # Gate1 선정 승인
    GATE2 = "GATE2"  # Gate2 사용자검증 승인
    BIZ_APPROVAL = "BIZ_APPROVAL"  # 사업기획 임원 승인
    PRE_PROPOSAL = "PRE_PROPOSAL"  # 선제안 승인
    HANDOFF = "HANDOFF"  # 인계 승인
    STAGE_ADVANCE = "STAGE_ADVANCE"  # 일반 단계 전환 승인


class ApprovalRequest(Base, TimestampMixin):
    """
    ApprovalRequest 테이블

    HITL(Human-in-the-Loop) 승인 요청 관리
    """

    __tablename__ = "approval_requests"

    # Primary Key
    request_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign Key
    opportunity_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("opportunities.opportunity_id", ondelete="CASCADE"),
        nullable=False,
    )

    # 승인 대상 단계
    target_stage: Mapped[str] = mapped_column(String(50), nullable=False)

    # 승인 유형
    approval_type: Mapped[ApprovalType] = mapped_column(
        Enum(ApprovalType),
        default=ApprovalType.STAGE_ADVANCE,
        nullable=False,
    )

    # 상태
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus),
        default=ApprovalStatus.PENDING,
        nullable=False,
    )

    # 승인자 목록 (JSON 배열)
    # [{"user_id": "...", "role": "BD_OWNER", "required": true}, ...]
    approvers: Mapped[list] = mapped_column(JSON, nullable=False)

    # 승인 응답 기록 (JSON 배열)
    # [{"user_id": "...", "decision": "APPROVED", "responded_at": "...", "comments": "..."}, ...]
    responses: Mapped[list | None] = mapped_column(JSON)

    # 요청 정보
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    request_reason: Mapped[str | None] = mapped_column(Text)

    # 관련 아티팩트 (JSON)
    # {"scorecard_id": "...", "brief_id": "...", "attachments": [...]}
    artifacts: Mapped[dict | None] = mapped_column(JSON)

    # 만료 시간
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 완료 시간
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[str | None] = mapped_column(String(100))

    # 결과 코멘트
    final_comments: Mapped[str | None] = mapped_column(Text)

    # Relationships
    opportunity: Mapped[Opportunity] = relationship(
        "Opportunity",
        back_populates="approval_requests",
    )

    # Indexes
    __table_args__ = (
        Index("idx_approval_opportunity_id", "opportunity_id"),
        Index("idx_approval_status", "status"),
        Index("idx_approval_type", "approval_type"),
        Index("idx_approval_target_stage", "target_stage"),
        Index("idx_approval_requested_by", "requested_by"),
        Index("idx_approval_expires_at", "expires_at"),
        Index("idx_approval_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalRequest(request_id='{self.request_id}', target_stage='{self.target_stage}', status='{self.status.value}')>"

    @property
    def is_pending(self) -> bool:
        """대기 중 여부"""
        return self.status == ApprovalStatus.PENDING

    @property
    def is_completed(self) -> bool:
        """완료 여부"""
        return self.status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED)

    @property
    def required_approvals_count(self) -> int:
        """필수 승인 수"""
        return sum(1 for a in (self.approvers or []) if a.get("required", False))

    @property
    def approved_count(self) -> int:
        """승인된 수"""
        return sum(1 for r in (self.responses or []) if r.get("decision") == "APPROVED")
