"""
Signal 저장소

Signal CRUD 작업
"""

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.signal import Signal, SignalSource, SignalStatus

from .base import CRUDBase


class SignalRepository(CRUDBase[Signal]):
    """Signal CRUD 저장소"""

    async def get_by_id(self, db: AsyncSession, signal_id: str) -> Signal | None:
        """
        signal_id로 Signal 조회

        Args:
            db: 데이터베이스 세션
            signal_id: Signal ID (예: SIG-2025-001)

        Returns:
            Signal | None
        """
        result = await db.execute(select(Signal).where(Signal.signal_id == signal_id))
        return result.scalar_one_or_none()

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        source: str | None = None,
        channel: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Signal], int]:
        """
        필터링된 Signal 목록 조회 (+ 총 개수)

        Args:
            db: 데이터베이스 세션
            source: 원천 필터 (KT/그룹사/대외)
            channel: 채널 필터 (데스크리서치/자사활동/영업PM/인바운드/아웃바운드)
            status: 상태 필터
            skip: 건너뛸 레코드 수
            limit: 가져올 레코드 수

        Returns:
            (list[Signal], int): Signal 목록 + 총 개수
        """
        # 필터 조건 구성
        filters = []
        if source:
            filters.append(Signal.source == source)
        if channel:
            filters.append(Signal.channel == channel)
        if status:
            filters.append(Signal.status == status)

        # 쿼리 실행
        query = select(Signal).where(and_(*filters)) if filters else select(Signal)
        query = query.order_by(Signal.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        items = list(result.scalars().all())

        # 총 개수 조회
        count_query = select(func.count()).select_from(Signal)
        if filters:
            count_query = count_query.where(and_(*filters))

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def get_stats(self, db: AsyncSession) -> dict:
        """
        Signal 통계 조회

        Returns:
            dict: 상태별 개수 등
        """
        # 총 Signal 수
        total_result = await db.execute(select(func.count()).select_from(Signal))
        total = total_result.scalar()

        # 상태별 개수
        status_stats = {}
        for status in SignalStatus:
            count_result = await db.execute(
                select(func.count()).select_from(Signal).where(Signal.status == status)
            )
            status_stats[status.value] = count_result.scalar()

        # 원천별 개수
        source_stats = {}
        for source in SignalSource:
            count_result = await db.execute(
                select(func.count()).select_from(Signal).where(Signal.source == source)
            )
            source_stats[source.value] = count_result.scalar()

        return {"total": total, "by_status": status_stats, "by_source": source_stats}

    async def generate_signal_id(self, db: AsyncSession) -> str:
        """
        새 Signal ID 생성 (SIG-YYYY-NNN 형식)

        Args:
            db: 데이터베이스 세션

        Returns:
            str: Signal ID (예: SIG-2025-001)
        """
        current_year = datetime.now().year

        # 올해 생성된 Signal 중 가장 큰 번호 찾기
        result = await db.execute(
            select(Signal.signal_id)
            .where(Signal.signal_id.like(f"SIG-{current_year}-%"))
            .order_by(Signal.signal_id.desc())
            .limit(1)
        )
        last_signal_id = result.scalar_one_or_none()

        if last_signal_id:
            # 마지막 번호 추출 (SIG-2025-001 → 001)
            last_number = int(last_signal_id.split("-")[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"SIG-{current_year}-{new_number:03d}"


# 싱글톤 인스턴스
signal_repo = SignalRepository(Signal)
