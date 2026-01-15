"""
PlayRecord 모델

Play 진행현황 DB 레코드 테이블 정의
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class PlayStatus(enum.Enum):
    """Play 상태 (Green/Yellow/Red)"""

    GREEN = "G"
    YELLOW = "Y"
    RED = "R"


class PlayRecord(Base):
    """
    PlayRecord 테이블

    Play 진행현황 추적 (Confluence DB 동기화)
    """

    __tablename__ = "play_records"

    # Primary Key
    play_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # 기본 정보
    play_name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(100))

    # 상태
    status: Mapped[PlayStatus] = mapped_column(
        String(1),  # G/Y/R
        nullable=False,
    )

    # 분기별 지표
    activity_qtd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signal_qtd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    brief_qtd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    s2_qtd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    s3_qtd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 액션 및 일정
    next_action: Mapped[str | None] = mapped_column(String(500))
    due_date: Mapped[Date | None] = mapped_column(Date)
    last_activity_date: Mapped[Date | None] = mapped_column(Date)

    # 비고 및 URL
    notes: Mapped[str | None] = mapped_column(String(1000))
    confluence_live_doc_url: Mapped[str | None] = mapped_column(String(500))

    # 타임스탬프
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PlayRecord(play_id='{self.play_id}', play_name='{self.play_name}', status='{self.status}')>"
