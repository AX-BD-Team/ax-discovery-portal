"""
AG-UI Event Stream Router

SSE(Server-Sent Events) 기반 실시간 이벤트 스트리밍 엔드포인트
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from backend.agent_runtime.event_manager import (
    SessionEventManager,
    WorkflowEventEmitter,
    generate_run_id,
    generate_session_id,
)
from backend.agent_runtime.workflows.wf_inbound_triage import (
    InboundInput,
    InboundTriagePipelineWithEvents,
)
from backend.agent_runtime.workflows.wf_interview_to_brief import (
    InterviewInput,
    InterviewToBriefPipelineWithEvents,
)
from backend.agent_runtime.workflows.wf_kpi_digest import (
    KPIDigestPipelineWithEvents,
    KPIInput,
)
from backend.agent_runtime.workflows.wf_seminar_pipeline import (
    SeminarInput,
    SeminarPipelineWithEvents,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/stream", tags=["stream"])


async def event_generator(
    event_manager: SessionEventManager,
    queue: asyncio.Queue[dict[str, Any]],
) -> AsyncGenerator[dict[str, Any], None]:
    """SSE 이벤트 생성기"""
    try:
        async for event in event_manager.stream(queue):
            event_type = event.get("type", "message")
            yield {
                "event": event_type,
                "data": json.dumps(event, ensure_ascii=False),
            }
    except asyncio.CancelledError:
        logger.info("Event stream cancelled")
    except Exception as e:
        logger.error("Event stream error", error=str(e))
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)}, ensure_ascii=False),
        }


@router.get("/workflow/WF-01")
async def stream_seminar_pipeline(
    url: str = Query(..., description="세미나 URL"),
    themes: str | None = Query(None, description="테마 목록 (쉼표 구분)"),
    play_id: str = Query("EXT_Desk_D01_Seminar", description="Play ID"),
) -> EventSourceResponse:
    """
    WF-01 세미나 파이프라인 실행 및 이벤트 스트림

    SSE Content-Type: text/event-stream
    이벤트 형식: event: EVENT_TYPE\\ndata: {JSON}\\n\\n
    """
    # 세션 및 실행 ID 생성
    session_id = generate_session_id("WF-01")
    run_id = generate_run_id()

    logger.info(
        "Starting seminar pipeline stream",
        session_id=session_id,
        run_id=run_id,
        url=url,
    )

    # 이벤트 매니저 생성
    event_manager = SessionEventManager.get_or_create(session_id)
    emitter = WorkflowEventEmitter(event_manager, run_id)

    # 구독자 등록
    queue = event_manager.subscribe()

    # 테마 파싱
    theme_list = [t.strip() for t in themes.split(",")] if themes else None

    # 워크플로 실행 (비동기)
    async def run_workflow() -> None:
        try:
            pipeline = SeminarPipelineWithEvents(emitter)
            input_data = SeminarInput(
                url=url,
                themes=theme_list,
                play_id=play_id,
            )
            await pipeline.run(input_data)
        except Exception as e:
            logger.error("Workflow error", error=str(e))
            await emitter.emit_run_error(str(e), recoverable=False)
        finally:
            # 세션 정리는 스트림 종료 후
            pass

    # 워크플로를 백그라운드에서 실행
    asyncio.create_task(run_workflow())

    return EventSourceResponse(event_generator(event_manager, queue))


@router.post("/workflow/WF-02")
async def stream_interview_pipeline(
    content: str = Query(..., description="인터뷰 노트 내용"),
    play_id: str | None = Query(None, description="Play ID"),
    customer: str | None = Query(None, description="고객/세그먼트"),
    source: str = Query("KT", description="원천 (KT, 그룹사, 대외)"),
    channel: str = Query("영업PM", description="채널"),
    interviewee: str | None = Query(None, description="인터뷰 대상자"),
) -> EventSourceResponse:
    """
    WF-02 Interview-to-Brief 파이프라인 실행 및 이벤트 스트림

    인터뷰 노트 → Signal 추출 → Scorecard 평가 → Brief 생성

    SSE Content-Type: text/event-stream
    이벤트 형식: event: EVENT_TYPE\\ndata: {JSON}\\n\\n
    """
    # 세션 및 실행 ID 생성
    session_id = generate_session_id("WF-02")
    run_id = generate_run_id()

    logger.info(
        "Starting interview-to-brief pipeline stream",
        session_id=session_id,
        run_id=run_id,
        play_id=play_id,
    )

    # 이벤트 매니저 생성
    event_manager = SessionEventManager.get_or_create(session_id)
    emitter = WorkflowEventEmitter(event_manager, run_id)

    # 구독자 등록
    queue = event_manager.subscribe()

    # 워크플로 실행 (비동기)
    async def run_workflow() -> None:
        try:
            pipeline = InterviewToBriefPipelineWithEvents(emitter)
            input_data = InterviewInput(
                content=content,
                play_id=play_id,
                customer=customer,
                source=source,
                channel=channel,
                interviewee=interviewee,
            )
            await pipeline.run(input_data)
        except Exception as e:
            logger.error("Workflow error", error=str(e))
            await emitter.emit_run_error(str(e), recoverable=False)

    # 워크플로를 백그라운드에서 실행
    asyncio.create_task(run_workflow())

    return EventSourceResponse(event_generator(event_manager, queue))


@router.post("/workflow/WF-04")
async def stream_inbound_triage(
    title: str = Query(..., description="제목"),
    description: str = Query(..., description="설명"),
    customer_segment: str | None = Query(None, description="고객/세그먼트"),
    pain: str | None = Query(None, description="Pain Point"),
    submitter: str | None = Query(None, description="제출자"),
    urgency: str = Query("NORMAL", description="긴급도 (URGENT, NORMAL, LOW)"),
    source: str = Query("KT", description="원천 (KT, 그룹사, 대외)"),
) -> EventSourceResponse:
    """
    WF-04 Inbound Triage 파이프라인 실행 및 이벤트 스트림

    Intake Form → Signal 생성 → 중복 체크 → Scorecard 초안 → SLA 설정

    SSE Content-Type: text/event-stream
    이벤트 형식: event: EVENT_TYPE\\ndata: {JSON}\\n\\n

    SLA:
    - URGENT: 24시간
    - NORMAL: 48시간
    - LOW: 72시간
    """
    # 세션 및 실행 ID 생성
    session_id = generate_session_id("WF-04")
    run_id = generate_run_id()

    logger.info(
        "Starting inbound triage pipeline stream",
        session_id=session_id,
        run_id=run_id,
        title=title,
        urgency=urgency,
    )

    # 이벤트 매니저 생성
    event_manager = SessionEventManager.get_or_create(session_id)
    emitter = WorkflowEventEmitter(event_manager, run_id)

    # 구독자 등록
    queue = event_manager.subscribe()

    # 워크플로 실행 (비동기)
    async def run_workflow() -> None:
        try:
            pipeline = InboundTriagePipelineWithEvents(emitter)
            input_data = InboundInput(
                title=title,
                description=description,
                customer_segment=customer_segment,
                pain=pain,
                submitter=submitter,
                urgency=urgency,
                source=source,
            )
            await pipeline.run(input_data)
        except Exception as e:
            logger.error("Workflow error", error=str(e))
            await emitter.emit_run_error(str(e), recoverable=False)

    # 워크플로를 백그라운드에서 실행
    asyncio.create_task(run_workflow())

    return EventSourceResponse(event_generator(event_manager, queue))


@router.get("/workflow/WF-05")
async def stream_kpi_digest(
    period: str = Query("week", description="기간 (week, month)"),
    notify: bool = Query(False, description="알림 발송 여부"),
) -> EventSourceResponse:
    """
    WF-05 KPI Digest 파이프라인 실행 및 이벤트 스트림

    주간/월간 KPI 리포트 생성 + 지연 Play/Action 경고

    SSE Content-Type: text/event-stream
    이벤트 형식: event: EVENT_TYPE\\ndata: {JSON}\\n\\n

    PoC 목표:
    - Activity 20+/주, Signal 30+/주, Brief 6+/주, S2 2~4/주
    - Signal→Brief ≤7일, Brief→S2 ≤14일
    """
    # 세션 및 실행 ID 생성
    session_id = generate_session_id("WF-05")
    run_id = generate_run_id()

    logger.info(
        "Starting KPI digest pipeline stream",
        session_id=session_id,
        run_id=run_id,
        period=period,
    )

    # 이벤트 매니저 생성
    event_manager = SessionEventManager.get_or_create(session_id)
    emitter = WorkflowEventEmitter(event_manager, run_id)

    # 구독자 등록
    queue = event_manager.subscribe()

    # 워크플로 실행 (비동기)
    async def run_workflow() -> None:
        try:
            pipeline = KPIDigestPipelineWithEvents(emitter)
            input_data = KPIInput(
                period=period,
                notify=notify,
                include_recommendations=True,
            )
            await pipeline.run(input_data)
        except Exception as e:
            logger.error("Workflow error", error=str(e))
            await emitter.emit_run_error(str(e), recoverable=False)

    # 워크플로를 백그라운드에서 실행
    asyncio.create_task(run_workflow())

    return EventSourceResponse(event_generator(event_manager, queue))


@router.get("/workflow/{workflow_id}")
async def stream_workflow(
    workflow_id: str,
    params: str | None = Query(None, description="워크플로 파라미터 (JSON)"),
) -> EventSourceResponse:
    """
    범용 워크플로 실행 및 이벤트 스트림

    현재 지원 워크플로:
    - WF-01: 세미나 파이프라인 (/api/stream/workflow/WF-01)
    - WF-02: 인터뷰-to-Brief (/api/stream/workflow/WF-02)
    - WF-04: 인바운드 Triage (/api/stream/workflow/WF-04)
    - WF-05: KPI Digest (/api/stream/workflow/WF-05)
    """
    if workflow_id == "WF-01":
        raise HTTPException(
            status_code=400,
            detail="WF-01은 /api/stream/workflow/WF-01 엔드포인트를 사용하세요",
        )

    if workflow_id == "WF-02":
        raise HTTPException(
            status_code=400,
            detail="WF-02는 POST /api/stream/workflow/WF-02 엔드포인트를 사용하세요",
        )

    if workflow_id == "WF-04":
        raise HTTPException(
            status_code=400,
            detail="WF-04는 POST /api/stream/workflow/WF-04 엔드포인트를 사용하세요",
        )

    if workflow_id == "WF-05":
        raise HTTPException(
            status_code=400,
            detail="WF-05는 GET /api/stream/workflow/WF-05 엔드포인트를 사용하세요",
        )

    # TODO: 다른 워크플로 지원 추가
    raise HTTPException(
        status_code=501,
        detail=f"워크플로 {workflow_id}는 아직 스트리밍을 지원하지 않습니다",
    )


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str) -> dict[str, Any]:
    """세션 이벤트 히스토리 조회"""
    if session_id not in SessionEventManager._instances:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    manager = SessionEventManager._instances[session_id]
    return {
        "session_id": session_id,
        "events": manager.get_history(),
        "total_events": len(manager.history),
    }


@router.delete("/session/{session_id}")
async def close_session(session_id: str) -> dict[str, str]:
    """세션 종료 및 정리"""
    if session_id not in SessionEventManager._instances:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    SessionEventManager.remove(session_id)
    return {"status": "closed", "session_id": session_id}
