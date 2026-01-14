"""
Play Dashboard Router

Play 운영 대시보드 API - DB 연동
"""

from datetime import datetime, date
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.database.repositories.play_record import play_record_repo


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
    confluence_live_doc_url: str | None
    last_updated: datetime

    class Config:
        from_attributes = True


class PlayListResponse(BaseModel):
    """Play 목록 응답"""
    items: list[PlayStats]
    total: int
    page: int
    page_size: int


class PlayCreate(BaseModel):
    """Play 생성 요청"""
    play_id: str
    play_name: str
    owner: str | None = None
    status: str = "G"
    confluence_live_doc_url: str | None = None


class PlayUpdate(BaseModel):
    """Play 업데이트 요청"""
    status: str | None = None
    next_action: str | None = None
    due_date: date | None = None
    owner: str | None = None


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
    status_summary: dict
    avg_signal_to_brief_days: float
    avg_brief_to_s2_days: float


@router.get("", response_model=PlayListResponse)
async def list_plays(
    db: AsyncSession = Depends(get_db),
    status: Annotated[str | None, Query(description="G/Y/R 필터")] = None,
    owner: Annotated[str | None, Query(description="담당자 필터")] = None,
    page: int = 1,
    page_size: int = 50
):
    """Play 목록 조회"""
    skip = (page - 1) * page_size
    items, total = await play_record_repo.get_multi_filtered(
        db, status, owner, skip, page_size
    )

    return PlayListResponse(
        items=[
            PlayStats(
                play_id=item.play_id,
                play_name=item.play_name,
                owner=item.owner,
                status=item.status if isinstance(item.status, str) else item.status.value if hasattr(item.status, 'value') else str(item.status),
                activity_qtd=item.activity_qtd,
                signal_qtd=item.signal_qtd,
                brief_qtd=item.brief_qtd,
                s2_qtd=item.s2_qtd,
                s3_qtd=item.s3_qtd,
                next_action=item.next_action,
                due_date=item.due_date,
                confluence_live_doc_url=item.confluence_live_doc_url,
                last_updated=item.last_updated
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/kpi/digest", response_model=KPIDigest)
async def get_kpi_digest(
    db: AsyncSession = Depends(get_db),
    period: Annotated[str, Query(description="week 또는 month")] = "week"
):
    """KPI 요약 리포트"""
    return await play_record_repo.get_kpi_digest(db, period)


@router.get("/kpi/alerts")
async def get_kpi_alerts(db: AsyncSession = Depends(get_db)):
    """지연/병목 경고"""
    return await play_record_repo.get_alerts(db)


@router.get("/leaderboard")
async def get_leaderboard(
    db: AsyncSession = Depends(get_db),
    period: str = "week"
):
    """Play 성과 순위"""
    return await play_record_repo.get_leaderboard(db, period)


@router.get("/{play_id}", response_model=PlayStats)
async def get_play(play_id: str, db: AsyncSession = Depends(get_db)):
    """Play 상세 조회"""
    play = await play_record_repo.get_by_id(db, play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    return PlayStats(
        play_id=play.play_id,
        play_name=play.play_name,
        owner=play.owner,
        status=play.status if isinstance(play.status, str) else play.status.value if hasattr(play.status, 'value') else str(play.status),
        activity_qtd=play.activity_qtd,
        signal_qtd=play.signal_qtd,
        brief_qtd=play.brief_qtd,
        s2_qtd=play.s2_qtd,
        s3_qtd=play.s3_qtd,
        next_action=play.next_action,
        due_date=play.due_date,
        confluence_live_doc_url=play.confluence_live_doc_url,
        last_updated=play.last_updated
    )


@router.get("/{play_id}/timeline")
async def get_play_timeline(
    play_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = 20
):
    """Play 타임라인 (Activity/Signal/Brief 이력)"""
    # Play 존재 확인
    play = await play_record_repo.get_by_id(db, play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    events = await play_record_repo.get_timeline(db, play_id, limit)

    return {
        "play_id": play_id,
        "events": events
    }


@router.post("", response_model=PlayStats)
async def create_play(
    play: PlayCreate,
    db: AsyncSession = Depends(get_db)
):
    """Play 생성"""
    # 중복 확인
    existing = await play_record_repo.get_by_id(db, play.play_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Play already exists: {play.play_id}"
        )

    # DB 저장
    play_data = {
        "play_id": play.play_id,
        "play_name": play.play_name,
        "owner": play.owner,
        "status": play.status,
        "activity_qtd": 0,
        "signal_qtd": 0,
        "brief_qtd": 0,
        "s2_qtd": 0,
        "s3_qtd": 0,
        "confluence_live_doc_url": play.confluence_live_doc_url
    }

    db_play = await play_record_repo.create(db, play_data)
    await db.commit()
    await db.refresh(db_play)

    return PlayStats(
        play_id=db_play.play_id,
        play_name=db_play.play_name,
        owner=db_play.owner,
        status=db_play.status if isinstance(db_play.status, str) else str(db_play.status),
        activity_qtd=db_play.activity_qtd,
        signal_qtd=db_play.signal_qtd,
        brief_qtd=db_play.brief_qtd,
        s2_qtd=db_play.s2_qtd,
        s3_qtd=db_play.s3_qtd,
        next_action=db_play.next_action,
        due_date=db_play.due_date,
        confluence_live_doc_url=db_play.confluence_live_doc_url,
        last_updated=db_play.last_updated
    )


@router.patch("/{play_id}")
async def update_play(
    play_id: str,
    update: PlayUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Play 업데이트"""
    play = await play_record_repo.get_by_id(db, play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    # 업데이트할 필드만 적용
    if update.status is not None:
        play.status = update.status
    if update.next_action is not None:
        play.next_action = update.next_action
    if update.due_date is not None:
        play.due_date = update.due_date
    if update.owner is not None:
        play.owner = update.owner

    await db.commit()
    await db.refresh(play)

    return {
        "status": "updated",
        "play_id": play_id,
        "message": "Play가 업데이트되었습니다."
    }


@router.post("/{play_id}/increment/{metric}")
async def increment_metric(
    play_id: str,
    metric: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Play 지표 증가

    Args:
        play_id: Play ID
        metric: 증가할 지표 (activity, signal, brief, s2, s3)
    """
    play = await play_record_repo.get_by_id(db, play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    valid_metrics = ["activity", "signal", "brief", "s2", "s3"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric. Must be one of: {valid_metrics}"
        )

    # 지표 증가
    if metric == "activity":
        await play_record_repo.increment_activity(db, play_id)
    elif metric == "signal":
        await play_record_repo.increment_signal(db, play_id)
    elif metric == "brief":
        await play_record_repo.increment_brief(db, play_id)
    elif metric == "s2":
        play.s2_qtd += 1
    elif metric == "s3":
        play.s3_qtd += 1

    await db.commit()

    return {
        "status": "incremented",
        "play_id": play_id,
        "metric": metric,
        "message": f"{metric} 지표가 증가되었습니다."
    }


@router.post("/{play_id}/sync")
async def sync_play(
    play_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Play DB 수동 동기화"""
    play = await play_record_repo.get_by_id(db, play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")

    # TODO: ConfluenceSync Agent 호출
    return {
        "status": "syncing",
        "play_id": play_id,
        "message": "Confluence 동기화 중..."
    }
