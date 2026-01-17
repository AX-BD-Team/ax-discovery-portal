"""
Task 모델

Play의 Next Action을 분해한 개별 작업 정의
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class TaskStatus(enum.Enum):
    """Task 상태"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriority(enum.Enum):
    """Task 우선순위"""

    P0 = "P0"  # 긴급
    P1 = "P1"  # 높음
    P2 = "P2"  # 보통


class Task(Base):
    """
    Task 테이블

    Play의 next_action을 세분화한 작업 단위
    """

    __tablename__ = "tasks"

    # Primary Key
    task_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Play 연결
    play_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("play_records.play_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 기본 정보
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # 상태 및 우선순위
    status: Mapped[str] = mapped_column(
        String(20),
        default=TaskStatus.PENDING.value,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(5),
        default=TaskPriority.P1.value,
        nullable=False,
    )

    # 담당자
    assignee: Mapped[str | None] = mapped_column(String(100))

    # 일정
    due_date: Mapped[Date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 순서 (같은 Play 내 Task 순서)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 원본 next_action에서 추출된 텍스트
    source_text: Mapped[str | None] = mapped_column(String(500))

    # 블로커 메모
    blocker_note: Mapped[str | None] = mapped_column(String(500))

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationship
    play_record = relationship("PlayRecord", backref="tasks")

    def __repr__(self) -> str:
        return f"<Task(task_id='{self.task_id}', title='{self.title}', status='{self.status}')>"

    def mark_completed(self) -> None:
        """Task를 완료 상태로 변경"""
        self.status = TaskStatus.COMPLETED.value
        self.completed_at = datetime.now(UTC)

    def mark_blocked(self, note: str | None = None) -> None:
        """Task를 블로킹 상태로 변경"""
        self.status = TaskStatus.BLOCKED.value
        if note:
            self.blocker_note = note

    def mark_in_progress(self) -> None:
        """Task를 진행 중 상태로 변경"""
        self.status = TaskStatus.IN_PROGRESS.value
