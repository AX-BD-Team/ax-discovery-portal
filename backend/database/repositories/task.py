"""
Task 저장소

Task CRUD 작업
"""

from datetime import UTC, date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.task import Task, TaskStatus

from .base import CRUDBase


class TaskRepository(CRUDBase[Task]):
    """Task CRUD 저장소"""

    async def get_by_id(self, db: AsyncSession, task_id: str) -> Task | None:
        """
        task_id로 Task 조회

        Args:
            db: 데이터베이스 세션
            task_id: Task ID

        Returns:
            Task | None
        """
        result = await db.execute(select(Task).where(Task.task_id == task_id))
        return result.scalar_one_or_none()

    async def get_by_play_id(
        self,
        db: AsyncSession,
        play_id: str,
        status: str | None = None,
    ) -> list[Task]:
        """
        Play ID로 Task 목록 조회

        Args:
            db: 데이터베이스 세션
            play_id: Play ID
            status: 상태 필터

        Returns:
            list[Task]
        """
        query = select(Task).where(Task.play_id == play_id)

        if status:
            query = query.where(Task.status == status)

        query = query.order_by(Task.order_index, Task.created_at)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_pending_tasks(
        self,
        db: AsyncSession,
        play_id: str | None = None,
        limit: int = 50,
    ) -> list[Task]:
        """
        미완료 Task 목록 조회

        Args:
            db: 데이터베이스 세션
            play_id: Play ID 필터 (선택)
            limit: 최대 반환 개수

        Returns:
            list[Task]
        """
        query = select(Task).where(
            Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value])
        )

        if play_id:
            query = query.where(Task.play_id == play_id)

        query = query.order_by(Task.priority, Task.due_date, Task.created_at).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_overdue_tasks(self, db: AsyncSession) -> list[Task]:
        """
        기한 초과 Task 목록 조회

        Args:
            db: 데이터베이스 세션

        Returns:
            list[Task]
        """
        today = date.today()
        query = select(Task).where(
            and_(
                Task.due_date.isnot(None),
                Task.due_date < today,
                Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]),
            )
        )
        query = query.order_by(Task.due_date)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_blocked_tasks(self, db: AsyncSession) -> list[Task]:
        """
        블로킹된 Task 목록 조회

        Args:
            db: 데이터베이스 세션

        Returns:
            list[Task]
        """
        result = await db.execute(
            select(Task)
            .where(Task.status == TaskStatus.BLOCKED.value)
            .order_by(Task.updated_at.desc())
        )
        return list(result.scalars().all())

    async def create_task(
        self,
        db: AsyncSession,
        task_id: str,
        play_id: str,
        title: str,
        description: str | None = None,
        priority: str = "P1",
        assignee: str | None = None,
        due_date: date | None = None,
        order_index: int = 0,
        source_text: str | None = None,
    ) -> Task:
        """
        새 Task 생성

        Args:
            db: 데이터베이스 세션
            task_id: Task ID
            play_id: Play ID
            title: 작업 제목
            description: 상세 설명
            priority: 우선순위 (P0/P1/P2)
            assignee: 담당자
            due_date: 기한
            order_index: 순서
            source_text: 원본 텍스트

        Returns:
            Task
        """
        task = Task(
            task_id=task_id,
            play_id=play_id,
            title=title,
            description=description,
            status=TaskStatus.PENDING.value,
            priority=priority,
            assignee=assignee,
            due_date=due_date,
            order_index=order_index,
            source_text=source_text,
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task

    async def update_status(
        self,
        db: AsyncSession,
        task_id: str,
        status: str,
        blocker_note: str | None = None,
    ) -> Task | None:
        """
        Task 상태 업데이트

        Args:
            db: 데이터베이스 세션
            task_id: Task ID
            status: 새 상태
            blocker_note: 블로커 메모 (blocked 상태일 때)

        Returns:
            Task | None
        """
        task = await self.get_by_id(db, task_id)
        if not task:
            return None

        task.status = status
        if status == TaskStatus.COMPLETED.value:
            task.completed_at = datetime.now(UTC)
        if blocker_note:
            task.blocker_note = blocker_note

        await db.flush()
        await db.refresh(task)
        return task

    async def complete_task(self, db: AsyncSession, task_id: str) -> Task | None:
        """
        Task 완료 처리

        Args:
            db: 데이터베이스 세션
            task_id: Task ID

        Returns:
            Task | None
        """
        return await self.update_status(db, task_id, TaskStatus.COMPLETED.value)

    async def get_stats_by_play(self, db: AsyncSession, play_id: str) -> dict:
        """
        Play별 Task 통계

        Args:
            db: 데이터베이스 세션
            play_id: Play ID

        Returns:
            dict: 상태별 Task 개수
        """
        # 전체 Task 수
        total_result = await db.execute(
            select(func.count()).select_from(Task).where(Task.play_id == play_id)
        )
        total = total_result.scalar() or 0

        # 완료된 Task 수
        completed_result = await db.execute(
            select(func.count())
            .select_from(Task)
            .where(and_(Task.play_id == play_id, Task.status == TaskStatus.COMPLETED.value))
        )
        completed = completed_result.scalar() or 0

        # 진행 중 Task 수
        in_progress_result = await db.execute(
            select(func.count())
            .select_from(Task)
            .where(and_(Task.play_id == play_id, Task.status == TaskStatus.IN_PROGRESS.value))
        )
        in_progress = in_progress_result.scalar() or 0

        # 블로킹된 Task 수
        blocked_result = await db.execute(
            select(func.count())
            .select_from(Task)
            .where(and_(Task.play_id == play_id, Task.status == TaskStatus.BLOCKED.value))
        )
        blocked = blocked_result.scalar() or 0

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": total - completed - in_progress - blocked,
            "blocked": blocked,
            "completion_rate": completed / total if total > 0 else 0,
        }

    async def delete_by_play_id(self, db: AsyncSession, play_id: str) -> int:
        """
        Play의 모든 Task 삭제

        Args:
            db: 데이터베이스 세션
            play_id: Play ID

        Returns:
            int: 삭제된 Task 수
        """
        tasks = await self.get_by_play_id(db, play_id)
        count = len(tasks)
        for task in tasks:
            await db.delete(task)
        await db.flush()
        return count

    async def get_next_task_id(self, db: AsyncSession) -> str:
        """
        다음 Task ID 생성

        형식: TASK-YYYY-NNNNN (예: TASK-2026-00001)

        Args:
            db: 데이터베이스 세션

        Returns:
            str: 새 Task ID
        """
        year = datetime.now(UTC).year

        # 현재 연도의 마지막 Task ID 조회
        result = await db.execute(
            select(Task.task_id)
            .where(Task.task_id.like(f"TASK-{year}-%"))
            .order_by(Task.task_id.desc())
            .limit(1)
        )
        last_task_id = result.scalar_one_or_none()

        if last_task_id:
            # TASK-2026-00123 형식에서 숫자 부분 추출
            last_num = int(last_task_id.split("-")[-1])
            next_num = last_num + 1
        else:
            next_num = 1

        return f"TASK-{year}-{next_num:05d}"


# 싱글톤 인스턴스
task_repo = TaskRepository(Task)
