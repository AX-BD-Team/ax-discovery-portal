"""
Play 동기화 트리거

Event-driven 자동 동기화 훅
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.brief import OpportunityBrief
from backend.database.models.signal import Signal
from backend.database.models.task import Task
from backend.database.repositories.play_record import play_record_repo
from backend.services.play_sync_service import play_sync_service

logger = structlog.get_logger()


class PlaySyncTriggers:
    """
    Play 자동 동기화 트리거

    Signal/Brief/Task 생성/수정 시 Play 통계 자동 업데이트
    """

    def __init__(self):
        self.logger = logger.bind(service="play_sync_triggers")

    async def on_signal_created(self, db: AsyncSession, signal: Signal) -> None:
        """
        Signal 생성 시 Play 통계 업데이트

        Args:
            db: 데이터베이스 세션
            signal: 생성된 Signal
        """
        if not signal.play_id:
            return

        self.logger.info(
            "Signal created trigger", signal_id=signal.signal_id, play_id=signal.play_id
        )

        # 1. Play 통계 업데이트
        await play_sync_service.update_play_stats_from_db(db, signal.play_id)

        # 2. Confluence 동기화 (백그라운드로 실행 권장)
        await play_sync_service.sync_play_to_confluence(db, signal.play_id)

    async def on_signal_updated(self, db: AsyncSession, signal: Signal) -> None:
        """
        Signal 수정 시 Play 통계 업데이트

        Args:
            db: 데이터베이스 세션
            signal: 수정된 Signal
        """
        if not signal.play_id:
            return

        self.logger.info(
            "Signal updated trigger", signal_id=signal.signal_id, play_id=signal.play_id
        )

        await play_sync_service.update_play_stats_from_db(db, signal.play_id)

    async def on_brief_created(self, db: AsyncSession, brief: OpportunityBrief) -> None:
        """
        Brief 생성 시 Play 통계 업데이트

        Args:
            db: 데이터베이스 세션
            brief: 생성된 Brief
        """
        # Brief → Signal → Play 연결
        from backend.database.repositories.signal import signal_repo

        signal = await signal_repo.get_by_id(db, brief.signal_id)
        if not signal or not signal.play_id:
            return

        self.logger.info("Brief created trigger", brief_id=brief.brief_id, play_id=signal.play_id)

        await play_sync_service.update_play_stats_from_db(db, signal.play_id)
        await play_sync_service.sync_play_to_confluence(db, signal.play_id)

    async def on_brief_status_changed(
        self, db: AsyncSession, brief: OpportunityBrief, old_status: str, new_status: str
    ) -> None:
        """
        Brief 상태 변경 시 Play 통계 업데이트 (S2 전환 등)

        Args:
            db: 데이터베이스 세션
            brief: Brief
            old_status: 이전 상태
            new_status: 새 상태
        """
        from backend.database.repositories.signal import signal_repo

        signal = await signal_repo.get_by_id(db, brief.signal_id)
        if not signal or not signal.play_id:
            return

        self.logger.info(
            "Brief status changed trigger",
            brief_id=brief.brief_id,
            play_id=signal.play_id,
            old_status=old_status,
            new_status=new_status,
        )

        # S2 진입 시 중요 이벤트
        if new_status == "s2_validated":
            self.logger.info("Brief entered S2", brief_id=brief.brief_id, play_id=signal.play_id)

        await play_sync_service.update_play_stats_from_db(db, signal.play_id)
        await play_sync_service.sync_play_to_confluence(db, signal.play_id)

    async def on_task_completed(self, db: AsyncSession, task: Task) -> None:
        """
        Task 완료 시 Play 상태 업데이트

        Args:
            db: 데이터베이스 세션
            task: 완료된 Task
        """
        self.logger.info("Task completed trigger", task_id=task.task_id, play_id=task.play_id)

        # Play의 next_action 업데이트 고려
        play = await play_record_repo.get_by_id(db, task.play_id)
        if play:
            # 모든 Task 완료 여부 확인
            from backend.database.repositories.task import task_repo

            stats = await task_repo.get_stats_by_play(db, task.play_id)

            if stats["completion_rate"] == 1.0:
                self.logger.info("All tasks completed", play_id=task.play_id)
                # 필요시 Play 상태 업데이트

            await play_sync_service.sync_play_to_confluence(db, task.play_id)

    async def on_activity_created(self, db: AsyncSession, play_id: str) -> None:
        """
        Activity 생성 시 Play의 activity_qtd 증가

        Args:
            db: 데이터베이스 세션
            play_id: Play ID
        """
        self.logger.info("Activity created trigger", play_id=play_id)

        play = await play_record_repo.increment_activity(db, play_id)
        if play:
            await play_sync_service.sync_play_to_confluence(db, play_id)


# 싱글톤 인스턴스
play_sync_triggers = PlaySyncTriggers()


# ============================================================
# 이벤트 발행 유틸리티
# ============================================================


async def emit_signal_created(db: AsyncSession, signal: Signal) -> None:
    """Signal 생성 이벤트 발행"""
    await play_sync_triggers.on_signal_created(db, signal)


async def emit_brief_created(db: AsyncSession, brief: OpportunityBrief) -> None:
    """Brief 생성 이벤트 발행"""
    await play_sync_triggers.on_brief_created(db, brief)


async def emit_brief_status_changed(
    db: AsyncSession, brief: OpportunityBrief, old_status: str, new_status: str
) -> None:
    """Brief 상태 변경 이벤트 발행"""
    await play_sync_triggers.on_brief_status_changed(db, brief, old_status, new_status)


async def emit_task_completed(db: AsyncSession, task: Task) -> None:
    """Task 완료 이벤트 발행"""
    await play_sync_triggers.on_task_completed(db, task)


async def emit_activity_created(db: AsyncSession, play_id: str) -> None:
    """Activity 생성 이벤트 발행"""
    await play_sync_triggers.on_activity_created(db, play_id)
