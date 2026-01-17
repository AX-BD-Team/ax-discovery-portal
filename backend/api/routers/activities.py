"""
Activities Router

Activity 조회 및 관리 API
외부 세미나 수집 결과 조회
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.database.repositories.activity import activity_repo

logger = structlog.get_logger()

router = APIRouter()


# ============================================================
# Response Models
# ============================================================


class ActivityResponse(BaseModel):
    """Activity 응답"""

    entity_id: str
    entity_type: str
    name: str
    description: str | None = None

    # Properties에서 추출
    url: str | None = None
    date: str | None = None
    organizer: str | None = None
    play_id: str | None = None
    source: str | None = None
    channel: str | None = None
    source_type: str | None = None
    categories: list[str] | None = None
    status: str | None = None

    # 타임스탬프
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_entity(cls, entity) -> "ActivityResponse":
        """Entity에서 변환"""
        props = entity.properties or {}
        return cls(
            entity_id=entity.entity_id,
            entity_type=entity.entity_type.value,
            name=entity.name,
            description=entity.description,
            url=props.get("url"),
            date=props.get("date"),
            organizer=props.get("organizer"),
            play_id=props.get("play_id"),
            source=props.get("source"),
            channel=props.get("channel"),
            source_type=props.get("source_type"),
            categories=props.get("categories", []),
            status=props.get("status"),
            created_at=entity.created_at.isoformat() if entity.created_at else None,
            updated_at=entity.updated_at.isoformat() if entity.updated_at else None,
        )


class ActivityListResponse(BaseModel):
    """Activity 목록 응답"""

    items: list[ActivityResponse]
    total: int
    page: int
    page_size: int


class ActivityStatsResponse(BaseModel):
    """Activity 통계 응답"""

    total: int
    by_source_type: dict[str, int]
    today_count: int


# ============================================================
# Activity 조회 API
# ============================================================


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    play_id: str | None = Query(None, description="Play ID 필터"),
    source_type: str | None = Query(None, description="소스 타입 필터 (rss, festa, eventbrite)"),
    status: str | None = Query(None, description="상태 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db),
):
    """
    Activity 목록 조회

    수집된 외부 세미나/이벤트 Activity 목록

    Args:
        play_id: Play ID 필터
        source_type: 소스 타입 필터 (rss, festa, eventbrite)
        status: 상태 필터
        page: 페이지 번호
        page_size: 페이지 크기

    Returns:
        ActivityListResponse: Activity 목록 + 페이지네이션 정보
    """
    skip = (page - 1) * page_size

    # 필터링 조건에 따라 조회
    if play_id:
        items, total = await activity_repo.list_by_play(
            db, play_id=play_id, limit=page_size, skip=skip
        )
    elif source_type:
        items, total = await activity_repo.list_by_source_type(
            db, source_type=source_type, limit=page_size, skip=skip
        )
    else:
        # 전체 조회 (Entity 타입이 ACTIVITY인 것만)
        from sqlalchemy import func, select

        from backend.database.models.entity import Entity, EntityType

        # 쿼리 실행
        query = (
            select(Entity)
            .where(Entity.entity_type == EntityType.ACTIVITY)
            .order_by(Entity.created_at.desc())
            .offset(skip)
            .limit(page_size)
        )
        result = await db.execute(query)
        items = list(result.scalars().all())

        # 총 개수
        count_query = (
            select(func.count())
            .select_from(Entity)
            .where(Entity.entity_type == EntityType.ACTIVITY)
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

    # 상태 필터 (post-filtering)
    if status and items:
        items = [
            item for item in items if (item.properties or {}).get("status") == status
        ]

    return ActivityListResponse(
        items=[ActivityResponse.from_entity(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=ActivityStatsResponse)
async def get_activity_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Activity 통계 조회

    Returns:
        ActivityStatsResponse: 전체 개수, 소스별 개수, 오늘 수집 개수
    """
    stats = await activity_repo.get_stats(db)

    return ActivityStatsResponse(
        total=stats["total"],
        by_source_type=stats["by_source_type"],
        today_count=stats["today_count"],
    )


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Activity 상세 조회

    Args:
        activity_id: Activity ID

    Returns:
        ActivityResponse: Activity 상세 정보
    """
    entity = await activity_repo.get_by_id(db, activity_id)

    if not entity:
        raise HTTPException(status_code=404, detail="Activity not found")

    return ActivityResponse.from_entity(entity)


@router.get("/by-url/{url:path}")
async def get_activity_by_url(
    url: str,
    db: AsyncSession = Depends(get_db),
):
    """
    URL로 Activity 조회

    중복 체크에 유용

    Args:
        url: 세미나/이벤트 URL

    Returns:
        Activity 정보 (없으면 404)
    """
    entity = await activity_repo.get_by_url(db, url)

    if not entity:
        raise HTTPException(status_code=404, detail="Activity not found for this URL")

    return ActivityResponse.from_entity(entity)


@router.post("/check-duplicate")
async def check_duplicate(
    url: str | None = None,
    title: str | None = None,
    date: str | None = None,
    external_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    중복 Activity 체크

    Args:
        url: 이벤트 URL
        title: 이벤트 제목
        date: 이벤트 날짜
        external_id: 외부 시스템 ID

    Returns:
        중복 여부 및 기존 Activity 정보
    """
    if not any([url, title, external_id]):
        raise HTTPException(
            status_code=400,
            detail="url, title, 또는 external_id 중 하나는 필수입니다",
        )

    existing = await activity_repo.check_duplicate(
        db,
        url=url,
        title=title,
        date=date,
        external_id=external_id,
    )

    if existing:
        return {
            "is_duplicate": True,
            "existing_activity": ActivityResponse.from_entity(existing),
        }
    else:
        return {
            "is_duplicate": False,
            "existing_activity": None,
        }
