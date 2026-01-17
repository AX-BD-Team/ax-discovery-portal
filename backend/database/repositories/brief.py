"""
OpportunityBrief 저장소

Brief CRUD 작업
"""

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.brief import BriefStatus, OpportunityBrief

from .base import CRUDBase


class BriefRepository(CRUDBase[OpportunityBrief]):
    """OpportunityBrief CRUD 저장소"""

    async def get_by_id(self, db: AsyncSession, brief_id: str) -> OpportunityBrief | None:
        """
        brief_id로 Brief 조회

        Args:
            db: 데이터베이스 세션
            brief_id: Brief ID (예: BRF-2025-001)

        Returns:
            OpportunityBrief | None
        """
        result = await db.execute(
            select(OpportunityBrief).where(OpportunityBrief.brief_id == brief_id)
        )
        return result.scalar_one_or_none()

    async def get_by_signal_id(self, db: AsyncSession, signal_id: str) -> OpportunityBrief | None:
        """
        signal_id로 Brief 조회 (1:1 관계)

        Args:
            db: 데이터베이스 세션
            signal_id: Signal ID

        Returns:
            OpportunityBrief | None
        """
        result = await db.execute(
            select(OpportunityBrief).where(OpportunityBrief.signal_id == signal_id)
        )
        return result.scalar_one_or_none()

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        status: str | None = None,
        owner: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[OpportunityBrief], int]:
        """
        필터링된 Brief 목록 조회 (+ 총 개수)

        Args:
            db: 데이터베이스 세션
            status: 상태 필터
            owner: 담당자 필터
            skip: 건너뛸 레코드 수
            limit: 가져올 레코드 수

        Returns:
            (list[OpportunityBrief], int): Brief 목록 + 총 개수
        """
        # 필터 조건 구성
        filters = []
        if status:
            filters.append(OpportunityBrief.status == status)
        if owner:
            filters.append(OpportunityBrief.owner == owner)

        # 쿼리 실행
        query = (
            select(OpportunityBrief).where(and_(*filters)) if filters else select(OpportunityBrief)
        )
        query = query.order_by(OpportunityBrief.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        items = list(result.scalars().all())

        # 총 개수 조회
        count_query = select(func.count()).select_from(OpportunityBrief)
        if filters:
            count_query = count_query.where(and_(*filters))

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def generate_brief_id(self, db: AsyncSession) -> str:
        """
        새 Brief ID 생성 (BRF-YYYY-NNN 형식)

        Args:
            db: 데이터베이스 세션

        Returns:
            str: Brief ID (예: BRF-2025-001)
        """
        current_year = datetime.now().year

        # 올해 생성된 Brief 중 가장 큰 번호 찾기
        result = await db.execute(
            select(OpportunityBrief.brief_id)
            .where(OpportunityBrief.brief_id.like(f"BRF-{current_year}-%"))
            .order_by(OpportunityBrief.brief_id.desc())
            .limit(1)
        )
        last_brief_id = result.scalar_one_or_none()

        if last_brief_id:
            last_number = int(last_brief_id.split("-")[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"BRF-{current_year}-{new_number:03d}"

    async def get_stats(self, db: AsyncSession) -> dict:
        """
        Brief 통계 조회

        Returns:
            dict: 상태별 개수 등
        """
        # 총 Brief 수
        total_result = await db.execute(select(func.count()).select_from(OpportunityBrief))
        total = total_result.scalar() or 0

        # 상태별 개수
        status_stats = {}
        for status in BriefStatus:
            count_result = await db.execute(
                select(func.count())
                .select_from(OpportunityBrief)
                .where(OpportunityBrief.status == status)
            )
            status_stats[status.value] = count_result.scalar() or 0

        return {"total": total, "by_status": status_stats}

    async def update_status(
        self,
        db: AsyncSession,
        brief_id: str,
        status: BriefStatus,
        confluence_url: str | None = None,
    ) -> OpportunityBrief | None:
        """
        Brief 상태 업데이트

        Args:
            db: 데이터베이스 세션
            brief_id: Brief ID
            status: 새 상태
            confluence_url: Confluence URL (승인 시)

        Returns:
            OpportunityBrief | None
        """
        brief = await self.get_by_id(db, brief_id)
        if not brief:
            return None

        brief.status = status
        if confluence_url:
            brief.confluence_url = confluence_url

        await db.flush()
        return brief


# 싱글톤 인스턴스
brief_repo = BriefRepository(OpportunityBrief)
