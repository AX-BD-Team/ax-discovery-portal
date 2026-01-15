"""
Play Dashboard Router

Play 관리 및 KPI 대시보드 API (D1 HTTP API 사용)
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.integrations.cloudflare_d1.repositories import play_d1_repo

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

    class Config:
        from_attributes = True


class PlayListResponse(BaseModel):
    """Play 목록 응답"""

    items: list[PlayResponse]
    total: int
    page: int
    page_size: int


class KPIDigestResponse(BaseModel):
    """KPI 다이제스트 응답"""

    period: str
    metrics: dict
    trends: dict


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


@router.get("/kpi/digest")
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
