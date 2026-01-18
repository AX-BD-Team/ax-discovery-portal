"""
Activity 저장소

Activity CRUD 작업 및 중복 체크
외부 세미나 수집 시 사용
"""

from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.entity import Entity, EntityType

from .base import CRUDBase


class ActivityRepository(CRUDBase[Entity]):
    """Activity CRUD 저장소"""

    async def get_by_id(self, db: AsyncSession, activity_id: str) -> Entity | None:
        """
        activity_id로 Activity 조회

        Args:
            db: 데이터베이스 세션
            activity_id: Activity ID (예: ACT-2025-001)

        Returns:
            Entity | None
        """
        result = await db.execute(
            select(Entity).where(
                and_(
                    Entity.entity_id == activity_id,
                    Entity.entity_type == EntityType.ACTIVITY,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_url(self, db: AsyncSession, url: str) -> Entity | None:
        """
        URL로 Activity 조회 (중복 체크용)

        Args:
            db: 데이터베이스 세션
            url: 세미나/이벤트 URL

        Returns:
            Entity | None
        """
        # 모든 Activity 조회 후 Python에서 URL 필터링 (PostgreSQL JSON 호환성)
        result = await db.execute(select(Entity).where(Entity.entity_type == EntityType.ACTIVITY))
        all_activities = result.scalars().all()

        for activity in all_activities:
            props = activity.properties or {}
            if props.get("url") == url:
                return activity

        return None

    async def get_by_external_id(self, db: AsyncSession, external_id: str) -> Entity | None:
        """
        외부 ID로 Activity 조회 (RSS guid, Festa event_id 등)

        Args:
            db: 데이터베이스 세션
            external_id: 외부 시스템 ID

        Returns:
            Entity | None
        """
        result = await db.execute(
            select(Entity).where(
                and_(
                    Entity.entity_type == EntityType.ACTIVITY,
                    Entity.external_ref_id == external_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_play(
        self,
        db: AsyncSession,
        play_id: str,
        limit: int = 50,
        skip: int = 0,
    ) -> tuple[list[Entity], int]:
        """
        Play별 Activity 목록 조회

        Args:
            db: 데이터베이스 세션
            play_id: Play ID
            limit: 가져올 레코드 수
            skip: 건너뛸 레코드 수

        Returns:
            (list[Entity], int): Activity 목록 + 총 개수
        """
        # 모든 Activity 조회
        result = await db.execute(
            select(Entity)
            .where(Entity.entity_type == EntityType.ACTIVITY)
            .order_by(Entity.created_at.desc())
        )
        all_activities = list(result.scalars().all())

        # Python에서 play_id 필터링 (PostgreSQL JSON 호환성)
        filtered = [a for a in all_activities if (a.properties or {}).get("play_id") == play_id]

        total = len(filtered)
        items = filtered[skip : skip + limit]

        return items, total

    async def list_by_source_type(
        self,
        db: AsyncSession,
        source_type: str,
        limit: int = 50,
        skip: int = 0,
    ) -> tuple[list[Entity], int]:
        """
        소스 타입별 Activity 목록 조회

        Args:
            db: 데이터베이스 세션
            source_type: 소스 타입 (rss, festa, eventbrite)
            limit: 가져올 레코드 수
            skip: 건너뛸 레코드 수

        Returns:
            (list[Entity], int): Activity 목록 + 총 개수
        """
        # 모든 Activity 조회
        result = await db.execute(
            select(Entity)
            .where(Entity.entity_type == EntityType.ACTIVITY)
            .order_by(Entity.created_at.desc())
        )
        all_activities = list(result.scalars().all())

        # Python에서 source_type 필터링 (PostgreSQL JSON 호환성)
        filtered = [
            a for a in all_activities if (a.properties or {}).get("source_type") == source_type
        ]

        total = len(filtered)
        items = filtered[skip : skip + limit]

        return items, total

    async def check_duplicate(
        self,
        db: AsyncSession,
        url: str | None = None,
        title: str | None = None,
        date: str | None = None,
        external_id: str | None = None,
    ) -> Entity | None:
        """
        중복 Activity 체크

        외부 ID, URL, 또는 제목+날짜 조합으로 중복 확인

        Args:
            db: 데이터베이스 세션
            url: 이벤트 URL
            title: 이벤트 제목
            date: 이벤트 날짜 (YYYY-MM-DD)
            external_id: 외부 시스템 ID

        Returns:
            Entity | None: 중복된 Activity (없으면 None)
        """
        # 1. 외부 ID로 체크 (가장 정확)
        if external_id:
            existing = await self.get_by_external_id(db, external_id)
            if existing:
                return existing

        # 2. URL로 체크
        if url:
            existing = await self.get_by_url(db, url)
            if existing:
                return existing

        # 3. 제목 + 날짜 조합으로 체크 (유사 중복)
        if title and date:
            # 모든 Activity 조회 후 Python에서 필터링 (PostgreSQL JSON 호환성)
            result = await db.execute(
                select(Entity).where(Entity.entity_type == EntityType.ACTIVITY)
            )
            all_activities = result.scalars().all()

            for activity in all_activities:
                props = activity.properties or {}
                if activity.name == title and props.get("date") == date:
                    return activity

        return None

    async def create_activity(
        self,
        db: AsyncSession,
        activity_data: dict,
    ) -> Entity:
        """
        새 Activity 생성

        Args:
            db: 데이터베이스 세션
            activity_data: Activity 데이터
                - activity_id: Activity ID (선택, 없으면 자동 생성)
                - title: 제목
                - url: URL
                - date: 날짜
                - organizer: 주최자
                - description: 설명
                - play_id: Play ID
                - source_type: 소스 타입 (rss, festa, eventbrite, manual)
                - categories: 카테고리 목록
                - external_id: 외부 시스템 ID
                - raw_data: 원본 데이터

        Returns:
            Entity: 생성된 Activity
        """
        # Activity ID 생성 (없으면 자동)
        activity_id = activity_data.get("activity_id")
        if not activity_id:
            activity_id = await self.generate_activity_id(db)

        # Entity 생성
        entity = Entity(
            entity_id=activity_id,
            entity_type=EntityType.ACTIVITY,
            name=activity_data.get("title", "세미나"),
            description=activity_data.get("description"),
            external_ref_id=activity_data.get("external_id"),
            properties={
                "url": activity_data.get("url"),
                "date": activity_data.get("date"),
                "organizer": activity_data.get("organizer"),
                "play_id": activity_data.get("play_id", "EXT_Desk_D01_Seminar"),
                "source": activity_data.get("source", "대외"),
                "channel": activity_data.get("channel", "데스크리서치"),
                "source_type": activity_data.get("source_type", "manual"),
                "categories": activity_data.get("categories", []),
                "themes": activity_data.get("themes", []),
                "status": activity_data.get("status", "REGISTERED"),
                "raw_data": activity_data.get("raw_data", {}),
            },
            published_at=(
                datetime.fromisoformat(activity_data["date"]) if activity_data.get("date") else None
            ),
            ingested_at=datetime.now(UTC),
            created_by=activity_data.get("created_by", "external_scout"),
        )

        db.add(entity)
        await db.flush()
        await db.refresh(entity)
        return entity

    async def generate_activity_id(self, db: AsyncSession) -> str:
        """
        새 Activity ID 생성 (ACT-YYYY-NNNNN 형식)

        Args:
            db: 데이터베이스 세션

        Returns:
            str: Activity ID (예: ACT-2025-00001)
        """
        current_year = datetime.now().year

        # 올해 생성된 Activity 중 가장 큰 번호 찾기
        result = await db.execute(
            select(Entity.entity_id)
            .where(
                and_(
                    Entity.entity_type == EntityType.ACTIVITY,
                    Entity.entity_id.like(f"ACT-{current_year}-%"),
                )
            )
            .order_by(Entity.entity_id.desc())
            .limit(1)
        )
        last_activity_id = result.scalar_one_or_none()

        if last_activity_id:
            # 마지막 번호 추출 (ACT-2025-00001 → 00001)
            last_number = int(last_activity_id.split("-")[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"ACT-{current_year}-{new_number:05d}"

    async def get_stats(self, db: AsyncSession) -> dict:
        """
        Activity 통계 조회

        Returns:
            dict: 통계 정보
        """
        # 총 Activity 수
        total_result = await db.execute(
            select(func.count())
            .select_from(Entity)
            .where(Entity.entity_type == EntityType.ACTIVITY)
        )
        total = total_result.scalar() or 0

        # 모든 Activity 조회 후 Python에서 집계 (JSON 쿼리 호환성 문제 우회)
        all_activities_result = await db.execute(
            select(Entity).where(Entity.entity_type == EntityType.ACTIVITY)
        )
        all_activities = list(all_activities_result.scalars().all())

        # 소스 타입별 개수 (Python에서 집계)
        source_types = ["rss", "festa", "eventbrite", "manual"]
        by_source_type = dict.fromkeys(source_types, 0)
        for activity in all_activities:
            props = activity.properties or {}
            st = props.get("source_type", "manual")
            if st in by_source_type:
                by_source_type[st] += 1

        # 오늘 수집된 Activity 수
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await db.execute(
            select(func.count())
            .select_from(Entity)
            .where(
                and_(
                    Entity.entity_type == EntityType.ACTIVITY,
                    Entity.created_at >= today_start,
                )
            )
        )
        today_count = today_result.scalar() or 0

        return {
            "total": total,
            "by_source_type": by_source_type,
            "today_count": today_count,
        }


# 싱글톤 인스턴스
activity_repo = ActivityRepository(Entity)
