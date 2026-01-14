"""
Signal Inbox Router

Signal 생성/조회/필터링 API
"""

from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel


router = APIRouter()


class SignalCreate(BaseModel):
    """Signal 생성 요청"""
    title: str
    description: str
    source: str  # KT, 그룹사, 대외
    channel: str  # 데스크리서치, 자사활동, 영업PM, 인바운드, 아웃바운드
    play_id: str
    customer_segment: str | None = None
    pain: str | None = None
    evidence: list[dict] | None = None
    tags: list[str] | None = None
    owner: str | None = None


class SignalResponse(BaseModel):
    """Signal 응답"""
    signal_id: str
    title: str
    description: str
    source: str
    channel: str
    play_id: str
    status: str
    created_at: datetime


class SignalListResponse(BaseModel):
    """Signal 목록 응답"""
    items: list[SignalResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=SignalListResponse)
async def list_signals(
    source: Annotated[str | None, Query(description="원천 필터")] = None,
    channel: Annotated[str | None, Query(description="채널 필터")] = None,
    play_id: Annotated[str | None, Query(description="Play ID 필터")] = None,
    status: Annotated[str | None, Query(description="상태 필터")] = None,
    page: int = 1,
    page_size: int = 20,
):
    """Signal 목록 조회"""
    # TODO: DB 조회 구현
    return SignalListResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size
    )


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(signal_id: str):
    """Signal 상세 조회"""
    # TODO: DB 조회 구현
    raise HTTPException(status_code=404, detail="Signal not found")


@router.post("", response_model=SignalResponse)
async def create_signal(signal: SignalCreate):
    """Signal 생성"""
    # TODO: DB 저장 및 Agent 호출
    signal_id = f"SIG-{datetime.now().year}-001"
    
    return SignalResponse(
        signal_id=signal_id,
        title=signal.title,
        description=signal.description,
        source=signal.source,
        channel=signal.channel,
        play_id=signal.play_id,
        status="NEW",
        created_at=datetime.utcnow()
    )


@router.post("/{signal_id}/triage")
async def triage_signal(signal_id: str):
    """Signal Scorecard 평가 시작"""
    # TODO: ScorecardEvaluator Agent 호출
    return {
        "status": "queued",
        "signal_id": signal_id,
        "message": "Scorecard 평가가 시작되었습니다."
    }


@router.get("/stats/summary")
async def get_inbox_stats():
    """Inbox 통계 요약"""
    # TODO: 실제 통계 계산
    return {
        "total": 0,
        "new": 0,
        "scoring": 0,
        "scored": 0,
        "brief_created": 0,
        "by_source": {"KT": 0, "그룹사": 0, "대외": 0},
        "by_channel": {}
    }
