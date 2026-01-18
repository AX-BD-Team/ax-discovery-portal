"""
Opportunity 저장소

Opportunity/StageTransition/ApprovalRequest CRUD 작업
"""

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database.models.approval_request import ApprovalRequest, ApprovalStatus
from backend.database.models.opportunity import Opportunity, OpportunityStage
from backend.database.models.stage_transition import StageTransition

from .base import CRUDBase


class OpportunityRepository(CRUDBase[Opportunity]):
    """Opportunity CRUD 저장소"""

    async def get_by_id(
        self,
        db: AsyncSession,
        opportunity_id: str,
        include_relations: bool = False,
    ) -> Opportunity | None:
        """
        opportunity_id로 Opportunity 조회

        Args:
            db: 데이터베이스 세션
            opportunity_id: Opportunity ID (예: OPP-2025-001)
            include_relations: Signal, Brief 관계 포함 여부

        Returns:
            Opportunity | None
        """
        query = select(Opportunity).where(Opportunity.opportunity_id == opportunity_id)

        if include_relations:
            query = query.options(
                selectinload(Opportunity.signal),
                selectinload(Opportunity.brief),
                selectinload(Opportunity.transitions),
                selectinload(Opportunity.approval_requests),
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        stage: str | None = None,
        bd_owner: str | None = None,
        play_id: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Opportunity], int]:
        """
        필터링된 Opportunity 목록 조회 (+ 총 개수)

        Args:
            db: 데이터베이스 세션
            stage: 단계 필터
            bd_owner: BD 담당자 필터
            play_id: Play ID 필터
            is_active: 활성 상태 필터
            skip: 건너뛸 레코드 수
            limit: 가져올 레코드 수

        Returns:
            (list[Opportunity], int): Opportunity 목록 + 총 개수
        """
        filters = []

        if stage:
            filters.append(Opportunity.current_stage == stage)
        if bd_owner:
            filters.append(Opportunity.bd_owner == bd_owner)
        if play_id:
            filters.append(Opportunity.play_id == play_id)
        if is_active is not None:
            inactive_stages = [OpportunityStage.HOLD, OpportunityStage.DROP]
            if is_active:
                filters.append(Opportunity.current_stage.notin_(inactive_stages))
            else:
                filters.append(Opportunity.current_stage.in_(inactive_stages))

        query = select(Opportunity).where(and_(*filters)) if filters else select(Opportunity)
        query = query.order_by(Opportunity.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        items = list(result.scalars().all())

        # 총 개수 조회
        count_query = select(func.count()).select_from(Opportunity)
        if filters:
            count_query = count_query.where(and_(*filters))

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def get_by_signal_id(
        self,
        db: AsyncSession,
        signal_id: str,
    ) -> Opportunity | None:
        """Signal ID로 Opportunity 조회"""
        result = await db.execute(select(Opportunity).where(Opportunity.signal_id == signal_id))
        return result.scalar_one_or_none()

    async def get_by_brief_id(
        self,
        db: AsyncSession,
        brief_id: str,
    ) -> Opportunity | None:
        """Brief ID로 Opportunity 조회"""
        result = await db.execute(select(Opportunity).where(Opportunity.brief_id == brief_id))
        return result.scalar_one_or_none()

    async def get_stage_stats(self, db: AsyncSession) -> dict:
        """
        단계별 Opportunity 통계 조회 (최적화: N개 쿼리 -> 1개 쿼리)

        Returns:
            dict: 단계별 개수 및 통계
        """
        # 단일 GROUP BY 쿼리로 모든 통계 조회
        stats_query = select(
            Opportunity.current_stage,
            func.count().label("count"),
        ).group_by(Opportunity.current_stage)
        result = await db.execute(stats_query)
        rows = result.all()

        # 결과 처리
        stage_stats = {stage.value: 0 for stage in OpportunityStage}
        total = 0
        active_count = 0
        inactive_stages = {OpportunityStage.HOLD, OpportunityStage.DROP}

        for row in rows:
            stage_stats[row.current_stage.value] = row.count
            total += row.count
            if row.current_stage not in inactive_stages:
                active_count += row.count

        return {
            "total": total,
            "active": active_count,
            "inactive": total - active_count,
            "by_stage": stage_stats,
        }

    async def get_funnel_data(self, db: AsyncSession) -> list[dict]:
        """
        파이프라인 퍼널 데이터 조회 (최적화: N개 쿼리 -> 1개 쿼리)

        Returns:
            list[dict]: 단계별 퍼널 데이터
        """
        funnel_stages = [
            (OpportunityStage.DISCOVERY, "01 발굴"),
            (OpportunityStage.IDEA_CARD, "02 수집"),
            (OpportunityStage.GATE1_SELECTION, "03 선정"),
            (OpportunityStage.MOCKUP, "04 형상화"),
            (OpportunityStage.GATE2_VALIDATION, "05 검증"),
            (OpportunityStage.BIZ_PLANNING, "06 기획"),
            (OpportunityStage.PILOT_POC, "07 파일럿"),
            (OpportunityStage.PRE_PROPOSAL, "08 선제안"),
            (OpportunityStage.HANDOFF, "09 인계"),
        ]

        # 단일 GROUP BY 쿼리로 모든 단계 개수 조회
        stats_query = select(
            Opportunity.current_stage,
            func.count().label("count"),
        ).group_by(Opportunity.current_stage)
        result = await db.execute(stats_query)
        rows = result.all()

        # 결과를 딕셔너리로 변환
        stage_counts = {row.current_stage: row.count for row in rows}

        # 퍼널 순서대로 데이터 구성
        funnel_data = []
        for stage, label in funnel_stages:
            funnel_data.append(
                {
                    "stage": stage.value,
                    "label": label,
                    "count": stage_counts.get(stage, 0),
                }
            )

        return funnel_data

    async def generate_opportunity_id(self, db: AsyncSession) -> str:
        """
        새 Opportunity ID 생성 (OPP-YYYY-NNN 형식)

        Args:
            db: 데이터베이스 세션

        Returns:
            str: Opportunity ID (예: OPP-2025-001)
        """
        current_year = datetime.now().year

        result = await db.execute(
            select(Opportunity.opportunity_id)
            .where(Opportunity.opportunity_id.like(f"OPP-{current_year}-%"))
            .order_by(Opportunity.opportunity_id.desc())
            .limit(1)
        )
        last_opp_id = result.scalar_one_or_none()

        if last_opp_id:
            last_number = int(last_opp_id.split("-")[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"OPP-{current_year}-{new_number:03d}"


class StageTransitionRepository(CRUDBase[StageTransition]):
    """StageTransition CRUD 저장소"""

    async def get_by_opportunity_id(
        self,
        db: AsyncSession,
        opportunity_id: str,
        limit: int = 50,
    ) -> list[StageTransition]:
        """특정 Opportunity의 전환 이력 조회"""
        result = await db.execute(
            select(StageTransition)
            .where(StageTransition.opportunity_id == opportunity_id)
            .order_by(StageTransition.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def generate_transition_id(self, db: AsyncSession) -> str:
        """새 Transition ID 생성"""
        current_year = datetime.now().year
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        return f"TRN-{current_year}-{timestamp}"


class ApprovalRequestRepository(CRUDBase[ApprovalRequest]):
    """ApprovalRequest CRUD 저장소"""

    async def get_by_id(
        self,
        db: AsyncSession,
        request_id: str,
    ) -> ApprovalRequest | None:
        """request_id로 ApprovalRequest 조회"""
        result = await db.execute(
            select(ApprovalRequest)
            .where(ApprovalRequest.request_id == request_id)
            .options(selectinload(ApprovalRequest.opportunity))
        )
        return result.scalar_one_or_none()

    async def get_pending_by_user(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ApprovalRequest], int]:
        """특정 사용자의 대기 중인 승인 요청 조회"""
        # approvers JSON 배열에서 user_id 검색
        # PostgreSQL의 경우: approvers @> '[{"user_id": "..."}]'
        # SQLite의 경우: JSON 함수 사용

        query = (
            select(ApprovalRequest)
            .where(ApprovalRequest.status == ApprovalStatus.PENDING)
            .order_by(ApprovalRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        items = list(result.scalars().all())

        # user_id가 승인자 목록에 있는 요청만 필터링
        filtered_items = [
            item
            for item in items
            if any(a.get("user_id") == user_id for a in (item.approvers or []))
        ]

        count_result = await db.execute(
            select(func.count())
            .select_from(ApprovalRequest)
            .where(ApprovalRequest.status == ApprovalStatus.PENDING)
        )
        total = count_result.scalar() or 0

        return filtered_items, total

    async def get_pending_all(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ApprovalRequest], int]:
        """모든 대기 중인 승인 요청 조회"""
        query = (
            select(ApprovalRequest)
            .where(ApprovalRequest.status == ApprovalStatus.PENDING)
            .options(selectinload(ApprovalRequest.opportunity))
            .order_by(ApprovalRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        items = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count())
            .select_from(ApprovalRequest)
            .where(ApprovalRequest.status == ApprovalStatus.PENDING)
        )
        total = count_result.scalar() or 0

        return items, total

    async def get_by_opportunity_id(
        self,
        db: AsyncSession,
        opportunity_id: str,
    ) -> list[ApprovalRequest]:
        """특정 Opportunity의 승인 요청 목록 조회"""
        result = await db.execute(
            select(ApprovalRequest)
            .where(ApprovalRequest.opportunity_id == opportunity_id)
            .order_by(ApprovalRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def generate_request_id(self, db: AsyncSession) -> str:
        """새 ApprovalRequest ID 생성"""
        current_year = datetime.now().year
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        return f"APR-{current_year}-{timestamp}"


# 싱글톤 인스턴스
opportunity_repo = OpportunityRepository(Opportunity)
stage_transition_repo = StageTransitionRepository(StageTransition)
approval_request_repo = ApprovalRequestRepository(ApprovalRequest)
