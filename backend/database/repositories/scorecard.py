"""
Scorecard 저장소

Scorecard CRUD 작업
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.scorecard import Scorecard
from .base import CRUDBase


class ScorecardRepository(CRUDBase[Scorecard]):
    """Scorecard CRUD 저장소"""

    async def get_by_id(
        self,
        db: AsyncSession,
        scorecard_id: str
    ) -> Optional[Scorecard]:
        """
        scorecard_id로 Scorecard 조회

        Args:
            db: 데이터베이스 세션
            scorecard_id: Scorecard ID (예: SCR-2025-001)

        Returns:
            Scorecard | None
        """
        result = await db.execute(
            select(Scorecard).where(Scorecard.scorecard_id == scorecard_id)
        )
        return result.scalar_one_or_none()

    async def get_by_signal_id(
        self,
        db: AsyncSession,
        signal_id: str
    ) -> Optional[Scorecard]:
        """
        signal_id로 Scorecard 조회 (1:1 관계)

        Args:
            db: 데이터베이스 세션
            signal_id: Signal ID

        Returns:
            Scorecard | None
        """
        result = await db.execute(
            select(Scorecard).where(Scorecard.signal_id == signal_id)
        )
        return result.scalar_one_or_none()

    async def generate_scorecard_id(self, db: AsyncSession) -> str:
        """
        새 Scorecard ID 생성 (SCR-YYYY-NNN 형식)

        Args:
            db: 데이터베이스 세션

        Returns:
            str: Scorecard ID (예: SCR-2025-001)
        """
        current_year = datetime.now().year

        # 올해 생성된 Scorecard 중 가장 큰 번호 찾기
        result = await db.execute(
            select(Scorecard.scorecard_id)
            .where(Scorecard.scorecard_id.like(f"SCR-{current_year}-%"))
            .order_by(Scorecard.scorecard_id.desc())
            .limit(1)
        )
        last_scorecard_id = result.scalar_one_or_none()

        if last_scorecard_id:
            last_number = int(last_scorecard_id.split("-")[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"SCR-{current_year}-{new_number:03d}"

    async def get_stats(self, db: AsyncSession) -> dict:
        """
        Scorecard 통계 조회

        Returns:
            dict: 평균 점수, GO/NO-GO 비율 등
        """
        # 총 Scorecard 수
        total_result = await db.execute(select(func.count()).select_from(Scorecard))
        total = total_result.scalar()

        # 평균 점수
        avg_score_result = await db.execute(select(func.avg(Scorecard.total_score)))
        avg_score = avg_score_result.scalar() or 0

        return {
            "total": total,
            "average_score": round(avg_score, 2)
        }


# 싱글톤 인스턴스
scorecard_repo = ScorecardRepository(Scorecard)
