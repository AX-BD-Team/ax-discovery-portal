"""
Scorecard 저장소

Scorecard CRUD 작업
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.scorecard import Scorecard

from .base import CRUDBase


class ScorecardRepository(CRUDBase[Scorecard]):
    """Scorecard CRUD 저장소"""

    async def get_by_id(self, db: AsyncSession, scorecard_id: str) -> Scorecard | None:
        """
        scorecard_id로 Scorecard 조회

        Args:
            db: 데이터베이스 세션
            scorecard_id: Scorecard ID (예: SCR-2025-001)

        Returns:
            Scorecard | None
        """
        result = await db.execute(select(Scorecard).where(Scorecard.scorecard_id == scorecard_id))
        return result.scalar_one_or_none()

    async def get_by_signal_id(self, db: AsyncSession, signal_id: str) -> Scorecard | None:
        """
        signal_id로 Scorecard 조회 (1:1 관계)

        Args:
            db: 데이터베이스 세션
            signal_id: Signal ID

        Returns:
            Scorecard | None
        """
        result = await db.execute(select(Scorecard).where(Scorecard.signal_id == signal_id))
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

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        decision: str | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Scorecard], int]:
        """
        필터링된 Scorecard 목록 조회

        Args:
            db: 데이터베이스 세션
            decision: 판정 결과 필터 (GO, PIVOT, HOLD, NO_GO)
            min_score: 최소 점수 필터
            max_score: 최대 점수 필터
            skip: 건너뛸 레코드 수
            limit: 반환할 레코드 수

        Returns:
            tuple[list[Scorecard], int]: (Scorecard 목록, 전체 개수)
        """
        # 기본 쿼리
        query = select(Scorecard)
        count_query = select(func.count()).select_from(Scorecard)

        # 필터 적용
        if decision:
            # recommendation JSON 필드에서 decision 추출하여 필터링
            query = query.where(Scorecard.recommendation["decision"].astext == decision)
            count_query = count_query.where(Scorecard.recommendation["decision"].astext == decision)

        if min_score is not None:
            query = query.where(Scorecard.total_score >= min_score)
            count_query = count_query.where(Scorecard.total_score >= min_score)

        if max_score is not None:
            query = query.where(Scorecard.total_score <= max_score)
            count_query = count_query.where(Scorecard.total_score <= max_score)

        # 정렬 및 페이지네이션
        query = query.order_by(Scorecard.scored_at.desc()).offset(skip).limit(limit)

        # 실행
        result = await db.execute(query)
        items = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def get_stats(self, db: AsyncSession) -> dict:
        """
        Scorecard 통계 조회

        Returns:
            dict: 평균 점수, GO/NO-GO 비율 등
        """
        # 총 Scorecard 수
        total_result = await db.execute(select(func.count()).select_from(Scorecard))
        total = total_result.scalar() or 0

        # 평균 점수
        avg_score_result = await db.execute(select(func.avg(Scorecard.total_score)))
        avg_score = avg_score_result.scalar() or 0

        return {"total": total, "average_score": round(avg_score, 2)}

    async def get_distribution_stats(self, db: AsyncSession) -> dict:
        """
        Scorecard 점수 분포 및 판정 통계 조회

        Returns:
            dict: GO/PIVOT/HOLD/NO_GO 개수, 평균 점수, Red-flag 비율
        """
        # 총 Scorecard 수
        total_result = await db.execute(select(func.count()).select_from(Scorecard))
        total = total_result.scalar() or 0

        if total == 0:
            return {
                "total_scored": 0,
                "go_count": 0,
                "pivot_count": 0,
                "hold_count": 0,
                "no_go_count": 0,
                "average_score": 0,
                "red_flag_rate": 0,
            }

        # 판정별 개수 (JSON 필드에서 decision 추출)
        go_result = await db.execute(
            select(func.count())
            .select_from(Scorecard)
            .where(Scorecard.recommendation["decision"].astext == "GO")
        )
        go_count = go_result.scalar() or 0

        pivot_result = await db.execute(
            select(func.count())
            .select_from(Scorecard)
            .where(Scorecard.recommendation["decision"].astext == "PIVOT")
        )
        pivot_count = pivot_result.scalar() or 0

        hold_result = await db.execute(
            select(func.count())
            .select_from(Scorecard)
            .where(Scorecard.recommendation["decision"].astext == "HOLD")
        )
        hold_count = hold_result.scalar() or 0

        no_go_result = await db.execute(
            select(func.count())
            .select_from(Scorecard)
            .where(Scorecard.recommendation["decision"].astext == "NO_GO")
        )
        no_go_count = no_go_result.scalar() or 0

        # 평균 점수
        avg_result = await db.execute(select(func.avg(Scorecard.total_score)))
        avg_score = avg_result.scalar() or 0

        # Red-flag이 있는 Scorecard 비율
        # red_flags가 비어있지 않은 (NULL이 아니고 빈 배열이 아닌) Scorecard 수
        red_flag_result = await db.execute(
            select(func.count())
            .select_from(Scorecard)
            .where(Scorecard.red_flags.isnot(None), func.json_array_length(Scorecard.red_flags) > 0)
        )
        red_flag_count = red_flag_result.scalar() or 0
        red_flag_rate = round((red_flag_count / total) * 100, 1) if total > 0 else 0

        return {
            "total_scored": total,
            "go_count": go_count,
            "pivot_count": pivot_count,
            "hold_count": hold_count,
            "no_go_count": no_go_count,
            "average_score": round(avg_score, 1),
            "red_flag_rate": red_flag_rate,
        }


# 싱글톤 인스턴스
scorecard_repo = ScorecardRepository(Scorecard)
