"""
PlayRecord 저장소

Play 진행현황 CRUD 작업
"""

from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.play_record import PlayRecord
from .base import CRUDBase


class PlayRecordRepository(CRUDBase[PlayRecord]):
    """PlayRecord CRUD 저장소"""

    async def get_by_id(
        self,
        db: AsyncSession,
        play_id: str
    ) -> Optional[PlayRecord]:
        """
        play_id로 PlayRecord 조회

        Args:
            db: 데이터베이스 세션
            play_id: Play ID

        Returns:
            PlayRecord | None
        """
        result = await db.execute(
            select(PlayRecord).where(PlayRecord.play_id == play_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession) -> list[PlayRecord]:
        """
        모든 PlayRecord 조회

        Args:
            db: 데이터베이스 세션

        Returns:
            list[PlayRecord]
        """
        result = await db.execute(select(PlayRecord))
        return result.scalars().all()

    async def increment_activity(
        self,
        db: AsyncSession,
        play_id: str
    ) -> Optional[PlayRecord]:
        """
        Play의 activity_qtd 증가

        Args:
            db: 데이터베이스 세션
            play_id: Play ID

        Returns:
            PlayRecord | None
        """
        play_record = await self.get_by_id(db, play_id)
        if play_record:
            play_record.activity_qtd += 1
            await db.flush()
            await db.refresh(play_record)
        return play_record

    async def increment_signal(
        self,
        db: AsyncSession,
        play_id: str
    ) -> Optional[PlayRecord]:
        """
        Play의 signal_qtd 증가

        Args:
            db: 데이터베이스 세션
            play_id: Play ID

        Returns:
            PlayRecord | None
        """
        play_record = await self.get_by_id(db, play_id)
        if play_record:
            play_record.signal_qtd += 1
            await db.flush()
            await db.refresh(play_record)
        return play_record

    async def increment_brief(
        self,
        db: AsyncSession,
        play_id: str
    ) -> Optional[PlayRecord]:
        """
        Play의 brief_qtd 증가

        Args:
            db: 데이터베이스 세션
            play_id: Play ID

        Returns:
            PlayRecord | None
        """
        play_record = await self.get_by_id(db, play_id)
        if play_record:
            play_record.brief_qtd += 1
            await db.flush()
            await db.refresh(play_record)
        return play_record

    async def get_stats(self, db: AsyncSession) -> dict:
        """
        Play 통계 조회

        Returns:
            dict: 총 Play 수, 총 Activity 수 등
        """
        # 총 Play 수
        total_result = await db.execute(select(func.count()).select_from(PlayRecord))
        total = total_result.scalar()

        # 총 Activity 수
        total_activity_result = await db.execute(select(func.sum(PlayRecord.activity_qtd)))
        total_activity = total_activity_result.scalar() or 0

        # 총 Signal 수
        total_signal_result = await db.execute(select(func.sum(PlayRecord.signal_qtd)))
        total_signal = total_signal_result.scalar() or 0

        # 총 Brief 수
        total_brief_result = await db.execute(select(func.sum(PlayRecord.brief_qtd)))
        total_brief = total_brief_result.scalar() or 0

        return {
            "total_plays": total,
            "total_activity": total_activity,
            "total_signal": total_signal,
            "total_brief": total_brief
        }


# 싱글톤 인스턴스
play_record_repo = PlayRecordRepository(PlayRecord)
