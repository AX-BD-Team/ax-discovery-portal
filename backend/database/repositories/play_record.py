"""
PlayRecord 저장소

Play 진행현황 CRUD 작업
"""

from datetime import date, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.play_record import PlayRecord

from .base import CRUDBase


class PlayRecordRepository(CRUDBase[PlayRecord]):
    """PlayRecord CRUD 저장소"""

    async def get_by_id(self, db: AsyncSession, play_id: str) -> PlayRecord | None:
        """
        play_id로 PlayRecord 조회

        Args:
            db: 데이터베이스 세션
            play_id: Play ID

        Returns:
            PlayRecord | None
        """
        result = await db.execute(select(PlayRecord).where(PlayRecord.play_id == play_id))
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
        return list(result.scalars().all())

    async def increment_activity(self, db: AsyncSession, play_id: str) -> PlayRecord | None:
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

    async def increment_signal(self, db: AsyncSession, play_id: str) -> PlayRecord | None:
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

    async def increment_brief(self, db: AsyncSession, play_id: str) -> PlayRecord | None:
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

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        status: str | None = None,
        owner: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PlayRecord], int]:
        """
        필터링된 PlayRecord 목록 조회

        Args:
            db: 데이터베이스 세션
            status: 상태 필터 (G/Y/R)
            owner: 담당자 필터
            skip: 건너뛸 레코드 수
            limit: 반환할 레코드 수

        Returns:
            tuple[list[PlayRecord], int]: (PlayRecord 목록, 전체 개수)
        """
        # 기본 쿼리
        query = select(PlayRecord)
        count_query = select(func.count()).select_from(PlayRecord)

        # 필터 조건
        filters = []
        if status:
            filters.append(PlayRecord.status == status)
        if owner:
            filters.append(PlayRecord.owner == owner)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # 정렬 및 페이지네이션
        query = query.order_by(PlayRecord.last_updated.desc()).offset(skip).limit(limit)

        # 실행
        result = await db.execute(query)
        items = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def get_stats(self, db: AsyncSession) -> dict:
        """
        Play 통계 조회

        Returns:
            dict: 총 Play 수, 총 Activity 수 등
        """
        # 총 Play 수
        total_result = await db.execute(select(func.count()).select_from(PlayRecord))
        total = total_result.scalar() or 0

        # 총 Activity 수
        total_activity_result = await db.execute(select(func.sum(PlayRecord.activity_qtd)))
        total_activity = total_activity_result.scalar() or 0

        # 총 Signal 수
        total_signal_result = await db.execute(select(func.sum(PlayRecord.signal_qtd)))
        total_signal = total_signal_result.scalar() or 0

        # 총 Brief 수
        total_brief_result = await db.execute(select(func.sum(PlayRecord.brief_qtd)))
        total_brief = total_brief_result.scalar() or 0

        # 총 S2 수
        total_s2_result = await db.execute(select(func.sum(PlayRecord.s2_qtd)))
        total_s2 = total_s2_result.scalar() or 0

        # 총 S3 수
        total_s3_result = await db.execute(select(func.sum(PlayRecord.s3_qtd)))
        total_s3 = total_s3_result.scalar() or 0

        return {
            "total_plays": total,
            "total_activity": total_activity,
            "total_signal": total_signal,
            "total_brief": total_brief,
            "total_s2": total_s2,
            "total_s3": total_s3,
        }

    async def get_kpi_digest(self, db: AsyncSession, period: str = "week") -> dict:
        """
        KPI 요약 리포트

        Args:
            db: 데이터베이스 세션
            period: "week" 또는 "month"

        Returns:
            dict: KPI 요약 통계
        """
        # 전체 통계 가져오기
        stats = await self.get_stats(db)

        # 주간 목표 (PoC 기준)
        targets = {
            "activity_target": 20,
            "signal_target": 30,
            "brief_target": 6,
            "s2_target": "2~4",
        }

        # 상태별 Play 수
        green_result = await db.execute(
            select(func.count()).select_from(PlayRecord).where(PlayRecord.status == "G")
        )
        yellow_result = await db.execute(
            select(func.count()).select_from(PlayRecord).where(PlayRecord.status == "Y")
        )
        red_result = await db.execute(
            select(func.count()).select_from(PlayRecord).where(PlayRecord.status == "R")
        )

        return {
            "period": period,
            "activity_actual": stats["total_activity"],
            "activity_target": targets["activity_target"],
            "signal_actual": stats["total_signal"],
            "signal_target": targets["signal_target"],
            "brief_actual": stats["total_brief"],
            "brief_target": targets["brief_target"],
            "s2_actual": stats["total_s2"],
            "s2_target": targets["s2_target"],
            "status_summary": {
                "green": green_result.scalar() or 0,
                "yellow": yellow_result.scalar() or 0,
                "red": red_result.scalar() or 0,
            },
            "avg_signal_to_brief_days": 0,  # TODO: 실제 리드타임 계산
            "avg_brief_to_s2_days": 0,  # TODO: 실제 리드타임 계산
        }

    async def get_alerts(self, db: AsyncSession) -> dict:
        """
        지연/경고 Play 조회

        Returns:
            dict: Yellow/Red Play, 기한 초과 항목
        """
        today = date.today()

        # Yellow Play 목록
        yellow_result = await db.execute(select(PlayRecord).where(PlayRecord.status == "Y"))
        yellow_plays = [p.play_id for p in yellow_result.scalars().all()]

        # Red Play 목록
        red_result = await db.execute(select(PlayRecord).where(PlayRecord.status == "R"))
        red_plays = [p.play_id for p in red_result.scalars().all()]

        # 기한 초과 Play (due_date < today)
        overdue_result = await db.execute(
            select(PlayRecord).where(
                and_(PlayRecord.due_date.isnot(None), PlayRecord.due_date < today)
            )
        )
        overdue_plays = [
            {"play_id": p.play_id, "due_date": str(p.due_date), "next_action": p.next_action}
            for p in overdue_result.scalars().all()
        ]

        # 7일 이상 활동 없는 Play
        stale_date = today - timedelta(days=7)
        stale_result = await db.execute(
            select(PlayRecord).where(
                or_(
                    PlayRecord.last_activity_date.is_(None),
                    PlayRecord.last_activity_date < stale_date,
                )
            )
        )
        stale_plays = [p.play_id for p in stale_result.scalars().all()]

        return {
            "alerts": [],  # 상위 레벨 알림 메시지
            "yellow_plays": yellow_plays,
            "red_plays": red_plays,
            "overdue_plays": overdue_plays,
            "stale_plays": stale_plays,
        }

    async def update_status(
        self,
        db: AsyncSession,
        play_id: str,
        status: str,
        next_action: str | None = None,
        due_date: date | None = None,
    ) -> PlayRecord | None:
        """
        Play 상태 업데이트

        Args:
            db: 데이터베이스 세션
            play_id: Play ID
            status: 새 상태 (G/Y/R)
            next_action: 다음 액션
            due_date: 기한

        Returns:
            PlayRecord | None
        """
        play_record = await self.get_by_id(db, play_id)
        if not play_record:
            return None

        play_record.status = status  # type: ignore[assignment]
        if next_action is not None:
            play_record.next_action = next_action
        if due_date is not None:
            play_record.due_date = due_date  # type: ignore[assignment]

        await db.flush()
        return play_record

    async def get_timeline(self, db: AsyncSession, play_id: str, limit: int = 20) -> list[dict]:
        """
        Play 타임라인 조회 (Activity/Signal/Brief 이력)

        Note: 실제 구현은 ActionLog 테이블을 조회해야 함
        """
        # TODO: ActionLog 테이블에서 play_id 관련 이벤트 조회
        return []

    async def get_leaderboard(self, db: AsyncSession, period: str = "week") -> dict:
        """
        Play 성과 순위

        Returns:
            dict: 상위 Play, 상위 기여자
        """
        # Signal 수 기준 상위 Play
        top_plays_result = await db.execute(
            select(PlayRecord).order_by(PlayRecord.signal_qtd.desc()).limit(10)
        )
        top_plays = [
            {
                "play_id": p.play_id,
                "play_name": p.play_name,
                "signal_qtd": p.signal_qtd,
                "brief_qtd": p.brief_qtd,
            }
            for p in top_plays_result.scalars().all()
        ]

        return {
            "period": period,
            "top_plays": top_plays,
            "top_contributors": [],  # TODO: 담당자별 집계
        }


# 싱글톤 인스턴스
play_record_repo = PlayRecordRepository(PlayRecord)
