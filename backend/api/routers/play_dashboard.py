"""
Play Dashboard Router

Play 운영 대시보드 API
"""

from datetime import datetime, date
from fastapi import APIRouter, Query
from pydantic import BaseModel


router = APIRouter()


class PlayStats(BaseModel):
    """Play 통계"""
    play_id: str
    play_name: str
    owner: str | None
    status: str  # G, Y, R
    activity_qtd: int
    signal_qtd: int
    brief_qtd: int
    s2_qtd: int
    s3_qtd: int
    next_action: str | None
    due_date: date | None
    last_updated: datetime


class KPIDigest(BaseModel):
    """KPI 요약"""
    period: str
    activity_actual: int
    activity_target: int
    signal_actual: int
    signal_target: int
    brief_actual: int
    brief_target: int
    s2_actual: int
    s2_target: str  # "2~4" 형태
    avg_signal_to_brief_days: float
    avg_brief_to_s2_days: float


@router.get("")
async def list_plays(
    status: str | None = Query(None, description="G/Y/R 필터"),
    owner: str | None = None,
    page: int = 1,
    page_size: int = 50
):
    """Play 목록 조회"""
    # TODO: Confluence DB 또는 Postgres 조회
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size
    }


@router.get("/{play_id}")
async def get_play(play_id: str):
    """Play 상세 조회"""
    # TODO: DB 조회
    return PlayStats(
        play_id=play_id,
        play_name="Sample Play",
        owner=None,
        status="G",
        activity_qtd=0,
        signal_qtd=0,
        brief_qtd=0,
        s2_qtd=0,
        s3_qtd=0,
        next_action=None,
        due_date=None,
        last_updated=datetime.utcnow()
    )


@router.get("/{play_id}/timeline")
async def get_play_timeline(play_id: str, limit: int = 20):
    """Play 타임라인 (Activity/Signal/Brief 이력)"""
    return {
        "play_id": play_id,
        "events": []
    }


@router.get("/kpi/digest")
async def get_kpi_digest(
    period: str = Query("week", description="week 또는 month")
):
    """KPI 요약 리포트"""
    return KPIDigest(
        period=period,
        activity_actual=0,
        activity_target=20,
        signal_actual=0,
        signal_target=30,
        brief_actual=0,
        brief_target=6,
        s2_actual=0,
        s2_target="2~4",
        avg_signal_to_brief_days=0,
        avg_brief_to_s2_days=0
    )


@router.get("/kpi/alerts")
async def get_kpi_alerts():
    """지연/병목 경고"""
    return {
        "alerts": [],
        "yellow_plays": [],
        "red_plays": [],
        "overdue_briefs": [],
        "stale_signals": []
    }


@router.get("/leaderboard")
async def get_leaderboard(period: str = "week"):
    """Play 성과 순위"""
    return {
        "period": period,
        "top_plays": [],
        "top_contributors": []
    }


@router.post("/{play_id}/sync")
async def sync_play(play_id: str):
    """Play DB 수동 동기화"""
    # TODO: ConfluenceSync Agent 호출
    return {
        "status": "syncing",
        "play_id": play_id,
        "message": "Confluence 동기화 중..."
    }
