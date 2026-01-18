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


class PlaySource(enum.Enum):
    """Play 원천"""

    KT = "KT"
    GROUP = "그룹사"
    EXTERNAL = "대외"
    COMMON = "공통"


class PlayChannel(enum.Enum):
    """Play 채널"""

    DESK = "데스크"
    SELF = "자사활동"
    SALES = "영업/PM"
    INBOUND = "인바운드"
    OUTBOUND = "아웃바운드"


class PlayPriority(enum.Enum):
    """Play 우선순위"""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class PlayCycle(enum.Enum):
    """Play 주기"""

    WEEKLY = "주간"
    BIWEEKLY = "격주"
    MONTHLY = "월간"
    QUARTERLY = "분기"
    ALWAYS = "상시"


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

    # 원천/채널/주기 (Phase 1 확장)
    source: Mapped[str | None] = mapped_column(String(20))  # KT/그룹사/대외/공통
    channel: Mapped[str | None] = mapped_column(
        String(20)
    )  # 데스크/자사활동/영업PM/인바운드/아웃바운드
    cycle: Mapped[str | None] = mapped_column(String(20))  # 주간/월간/분기/격주/상시
    priority: Mapped[str | None] = mapped_column(String(5))  # P0/P1/P2
    quarter: Mapped[str | None] = mapped_column(String(10))  # 2026Q1 등

    # 상태
    status: Mapped[PlayStatus] = mapped_column(
        String(1),  # G/Y/R
        nullable=False,
    )

    # 분기별 목표
    activity_goal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signal_goal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    brief_goal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    s2_goal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 분기별 실적
    activity_qtd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signal_qtd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    brief_qtd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    s2_qtd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    s3_qtd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 리드타임 목표 (Phase 1 확장)
    lead_time_target: Mapped[str | None] = mapped_column(String(200))  # "A→S0≤1d / S0→S1≤7d"

    # 액션 및 일정
    next_action: Mapped[str | None] = mapped_column(String(500))
    due_date: Mapped[Date | None] = mapped_column(Date)
    last_activity_date: Mapped[Date | None] = mapped_column(Date)

    # 블로커 (Phase 1 확장)
    blocker: Mapped[str | None] = mapped_column(String(500))

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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PlayRecord(play_id='{self.play_id}', play_name='{self.play_name}', status='{self.status}')>"

    def calculate_rag_status(self) -> str:
        """목표 달성률 기반 RAG 상태 자동 계산"""
        # 목표 대비 실적률 계산
        rates = []
        if self.signal_goal > 0:
            rates.append(self.signal_qtd / self.signal_goal)
        if self.brief_goal > 0:
            rates.append(self.brief_qtd / self.brief_goal)

        if not rates:
            return "G"

        avg_rate = sum(rates) / len(rates)

        # 50% 미만: Red, 50~80%: Yellow, 80% 이상: Green
        if avg_rate >= 0.8:
            return "G"
        elif avg_rate >= 0.5:
            return "Y"
        else:
            return "R"
