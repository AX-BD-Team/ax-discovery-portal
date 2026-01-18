"""
Play Dashboard Router

Play 관리 및 KPI 대시보드 API (D1 HTTP API 사용)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.repositories.play_record import play_record_repo
from backend.database.repositories.task import task_repo
from backend.database.session import get_db
from backend.integrations.cloudflare_d1.repositories import play_d1_repo
from backend.services.play_sync_service import play_sync_service

router = APIRouter()


class PlayResponse(BaseModel):
    """Play 응답"""

    play_id: str
    play_name: str
    status: str  # G, Y, R
    owner: str | None = None
    confluence_live_doc_url: str | None = None
    activity_qtd: int = 0
    signal_qtd: int = 0
    brief_qtd: int = 0
    s2_qtd: int = 0
    s3_qtd: int = 0
    next_action: str | None = None
    due_date: str | None = None
    notes: str | None = None
    last_activity_date: str | None = None
    last_updated: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PlayListResponse(BaseModel):
    """Play 목록 응답"""

    items: list[PlayResponse]
    total: int
    page: int
    page_size: int


class KPIDigestResponse(BaseModel):
    """KPI 다이제스트 응답 - 프론트엔드 KPIDigest 인터페이스에 맞춤"""

    period: str
    activity_actual: int
    activity_target: int
    signal_actual: int
    signal_target: int
    brief_actual: int
    brief_target: int
    s2_actual: int
    s2_target: str  # "2~4" 형식
    avg_signal_to_brief_days: float
    avg_brief_to_s2_days: float


class KPIAlertsResponse(BaseModel):
    """KPI 알림 응답"""

    alerts: list[str]
    red_plays: list[str]
    overdue_briefs: list[str]


@router.get("", response_model=PlayListResponse)
async def list_plays(
    status: Annotated[str | None, Query(description="상태 필터 (G, Y, R)")] = None,
    page: int = 1,
    page_size: int = 20,
):
    """Play 목록 조회"""
    items, total = await play_d1_repo.get_all(
        page=page,
        page_size=page_size,
        status=status,
    )

    return PlayListResponse(
        items=[PlayResponse(**item) for item in items], total=total, page=page, page_size=page_size
    )


@router.get("/kpi/digest", response_model=KPIDigestResponse)
async def get_kpi_digest(period: str = "week"):
    """KPI 다이제스트 조회"""
    return await play_d1_repo.get_kpi_digest(period)


@router.get("/kpi/alerts")
async def get_kpi_alerts():
    """KPI 알림 조회"""
    return await play_d1_repo.get_kpi_alerts()


@router.get("/{play_id}", response_model=PlayResponse)
async def get_play(play_id: str):
    """Play 상세 조회"""
    play = await play_d1_repo.get_by_id(play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    return PlayResponse(**play)


@router.get("/{play_id}/timeline")
async def get_play_timeline(play_id: str, limit: int = 10):
    """Play 타임라인 조회"""
    play = await play_d1_repo.get_by_id(play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    # TODO: 실제 타임라인 이벤트 조회
    return {"play_id": play_id, "events": []}


@router.post("/{play_id}/sync")
async def sync_play(play_id: str):
    """Confluence에서 Play 동기화"""
    play = await play_d1_repo.get_by_id(play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    return {"status": "synced", "play_id": play_id, "message": "Play가 동기화되었습니다."}


# ============================================================
# PostgreSQL 기반 확장 엔드포인트
# ============================================================


@router.get("/{play_id}/tasks")
async def get_play_tasks(
    play_id: str,
    status: Annotated[str | None, Query(description="상태 필터")] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Play의 Task 목록 조회

    PostgreSQL DB에서 해당 Play의 모든 Task를 조회합니다.
    """
    play = await play_record_repo.get_by_id(db, play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    tasks = await task_repo.get_by_play_id(db, play_id, status)

    return {
        "play_id": play_id,
        "tasks": [
            {
                "task_id": t.task_id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "assignee": t.assignee,
                "due_date": str(t.due_date) if t.due_date else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ],
        "total": len(tasks),
    }


@router.post("/{play_id}/update-stats")
async def update_play_stats(
    play_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Play 통계 업데이트

    Signal/Brief 건수를 집계하여 Play 실적을 업데이트합니다.
    """
    play = await play_sync_service.update_play_stats_from_db(db, play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    return {
        "status": "updated",
        "play_id": play_id,
        "stats": {
            "signal_qtd": play.signal_qtd,
            "brief_qtd": play.brief_qtd,
            "s2_qtd": play.s2_qtd,
            "rag": play.status if isinstance(play.status, str) else play.status.value,
        },
    }


@router.post("/{play_id}/sync-confluence")
async def sync_play_to_confluence(
    play_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Play를 Confluence에 동기화

    DB의 Play 정보를 Confluence Play DB 페이지에 반영합니다.
    """
    result = await play_sync_service.sync_play_to_confluence(db, play_id)
    return result


@router.post("/sync-all")
async def sync_all_plays_to_confluence(
    db: AsyncSession = Depends(get_db),
):
    """
    전체 Play Confluence 동기화

    모든 Play 정보를 Confluence Play DB 페이지에 반영합니다.
    """
    result = await play_sync_service.sync_all_plays_to_confluence(db)
    return result


@router.get("/{play_id}/task-stats")
async def get_play_task_stats(
    play_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Play의 Task 통계 조회

    완료율, 상태별 개수 등을 반환합니다.
    """
    play = await play_record_repo.get_by_id(db, play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    stats = await task_repo.get_stats_by_play(db, play_id)
    return {
        "play_id": play_id,
        "play_name": play.play_name,
        **stats,
    }
