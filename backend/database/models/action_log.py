"""
ActionLog 모델

Action Log DB 레코드 테이블 정의
"""

import enum
from typing import Optional
from sqlalchemy import String, Text, Enum, Index, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone

from backend.database.base import Base


class ActionType(enum.Enum):
    """액션 유형"""
    ACTIVITY = "ACTIVITY"
    SIGNAL = "SIGNAL"
    SCORECARD = "SCORECARD"
    BRIEF = "BRIEF"
    VALIDATION = "VALIDATION"
    PILOT = "PILOT"
    OTHER = "OTHER"


class ActionLog(Base):
    """
    ActionLog 테이블

    Play 활동 로그 (Confluence Action Log 동기화)
    """

    __tablename__ = "action_logs"

    # Primary Key
    log_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Play 및 액션 정보
    play_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(500))

    # 관련 ID들 (JSON)
    related_ids: Mapped[Optional[dict]] = mapped_column(JSON)

    # 수행자 정보
    actor: Mapped[Optional[str]] = mapped_column(String(100))
    agent_id: Mapped[Optional[str]] = mapped_column(String(100))
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    workflow_id: Mapped[Optional[str]] = mapped_column(String(100))

    # 추가 메타데이터
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("idx_action_log_play_id", "play_id"),
        Index("idx_action_log_action_type", "action_type"),
        Index("idx_action_log_created_at", "created_at"),
        Index("idx_action_log_actor", "actor"),
    )

    def __repr__(self) -> str:
        return f"<ActionLog(log_id='{self.log_id}', play_id='{self.play_id}', action_type='{self.action_type.value}')>"
