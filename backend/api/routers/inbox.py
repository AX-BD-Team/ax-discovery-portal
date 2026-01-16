"""
Signal Inbox Router

Signal 생성/조회/필터링 API (D1 HTTP API 사용)
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.integrations.cloudflare_d1.repositories import signal_d1_repo

router = APIRouter()


class SignalCreate(BaseModel):
    """Signal 생성 요청"""

    title: str
    source: str = "대외"
    channel: str = "데스크리서치"
    play_id: str = "UNKNOWN"
    pain: str
    customer_segment: str | None = None
    proposed_value: str | None = None
    kpi_hypothesis: list[str] | None = None
    evidence: list[dict] | None = None
    tags: list[str] | None = None
    owner: str | None = None


class SignalResponse(BaseModel):
    """Signal 응답"""

    signal_id: str
    title: str
    source: str
    channel: str
    play_id: str
    pain: str
    status: str
    customer_segment: str | None = None
    proposed_value: str | None = None
    owner: str | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


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
    items, total = await signal_d1_repo.get_all(
        page=page,
        page_size=page_size,
        status=status,
    )

    return SignalListResponse(
        items=[SignalResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats/summary")
async def get_inbox_stats():
    """Inbox 통계 요약"""
    stats = await signal_d1_repo.get_stats()

    return {
        "total": stats["total"],
        "by_status": stats["by_status"],
        "by_source": stats["by_source"],
    }


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(signal_id: str):
    """Signal 상세 조회"""
    signal = await signal_d1_repo.get_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    return SignalResponse(**signal)


@router.post("", response_model=SignalResponse)
async def create_signal(signal: SignalCreate):
    """Signal 생성"""
    signal_data = signal.model_dump()
    db_signal = await signal_d1_repo.create(signal_data)

    return SignalResponse(**db_signal)


@router.post("/{signal_id}/triage")
async def triage_signal(signal_id: str):
    """Signal Scorecard 평가 시작"""
    # 상태 업데이트
    await signal_d1_repo.update_status(signal_id, "S1")

    return {
        "status": "queued",
        "signal_id": signal_id,
        "message": "Scorecard 평가가 시작되었습니다.",
    }


@router.post("/seminar", response_model=dict)
async def seminar_add_command(
    url: str, themes: str | None = None, play_id: str = "EXT_Desk_D01_Seminar"
):
    """
    /ax:seminar-add 커맨드 핸들러

    Usage: /ax:seminar-add <URL> [--theme <themes>] [--play <play_id>]
    """
    from backend.agent_runtime.runner import runtime

    # themes를 리스트로 변환
    theme_list = [t.strip() for t in themes.split(",")] if themes else None

    # WF-01 실행
    result = await runtime.run_workflow(
        "WF-01", {"url": url, "themes": theme_list, "play_id": play_id}
    )

    # Activity 정보 추출
    activity = result["activity"]

    # 사용자 친화적 출력
    output = f"""✅ Activity 생성 완료

📅 세미나: {activity.title}
📍 일시: {activity.date or "TBD"}

📝 Activity ID: {activity.activity_id}
📂 Play: {activity.play_id}
📋 AAR 템플릿이 준비되었습니다.

➡️ 참석 후 AAR 작성을 시작하세요.
"""

    return {
        "status": "success",
        "activity_id": activity.activity_id,
        "message": output,
        "confluence_updated": result.get("confluence_updated", False),
    }
