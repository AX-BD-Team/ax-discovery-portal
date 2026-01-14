"""
Workflows Router

워크플로 실행 REST API 엔드포인트
(SSE 스트리밍이 필요없는 경우)
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.api.deps import get_db
from backend.agent_runtime.workflows.wf_interview_to_brief import (
    InterviewInput,
    InterviewToBriefPipeline,
    InterviewToBriefPipelineWithDB,
)
from backend.agent_runtime.workflows.wf_inbound_triage import (
    InboundInput,
    InboundTriagePipeline,
    InboundTriagePipelineWithDB,
)
from backend.agent_runtime.workflows.wf_kpi_digest import (
    KPIInput,
    KPIDigestPipeline,
    KPIDigestPipelineWithDB,
)
from backend.agent_runtime.event_manager import (
    SessionEventManager,
    WorkflowEventEmitter,
    generate_run_id,
    generate_session_id,
)


logger = structlog.get_logger()

router = APIRouter()


# ============================================================
# Request/Response Models
# ============================================================

class InterviewRequest(BaseModel):
    """WF-02 인터뷰 파이프라인 요청"""
    content: str  # 인터뷰 노트 내용 (필수)
    play_id: str | None = None
    customer: str | None = None
    source: str = "KT"
    channel: str = "영업PM"
    interviewee: str | None = None
    interview_date: str | None = None
    save_to_db: bool = True  # DB 저장 여부


class SignalSummary(BaseModel):
    """Signal 요약"""
    signal_id: str
    title: str
    pain: str
    confidence: float


class ScorecardSummary(BaseModel):
    """Scorecard 요약"""
    scorecard_id: str
    signal_id: str
    total_score: int
    decision: str
    next_step: str


class BriefSummary(BaseModel):
    """Brief 요약"""
    brief_id: str
    signal_id: str
    title: str
    status: str


class InterviewResponse(BaseModel):
    """WF-02 인터뷰 파이프라인 응답"""
    status: str
    signals: list[dict[str, Any]]
    scorecards: list[dict[str, Any]]
    briefs: list[dict[str, Any]]
    pending_approvals: list[str]
    summary: dict[str, Any]


class InboundTriageRequest(BaseModel):
    """WF-04 인바운드 Triage 요청"""
    title: str  # 제목 (필수)
    description: str  # 설명 (필수)
    customer_segment: str | None = None
    pain: str | None = None
    submitter: str | None = None
    urgency: str = "NORMAL"  # URGENT, NORMAL, LOW
    source: str = "KT"  # KT, 그룹사, 대외
    save_to_db: bool = True  # DB 저장 여부


class InboundTriageResponse(BaseModel):
    """WF-04 인바운드 Triage 응답"""
    status: str
    signal: dict[str, Any] | None
    is_duplicate: bool
    similar_signals: list[dict[str, Any]]
    assigned_play_id: str | None
    scorecard: dict[str, Any] | None
    sla: dict[str, Any]
    summary: dict[str, Any]


# ============================================================
# WF-02: Interview-to-Brief
# ============================================================

@router.post("/interview-to-brief", response_model=InterviewResponse)
async def run_interview_to_brief(
    request: InterviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    WF-02: Interview-to-Brief 파이프라인 실행

    인터뷰 노트 → Signal 추출 → Scorecard 평가 → Brief 생성

    Args:
        content: 인터뷰 노트 텍스트
        play_id: Play ID (예: KT_Sales_S01_Interview)
        customer: 고객/세그먼트
        source: 원천 (KT, 그룹사, 대외)
        channel: 채널 (영업PM, 데스크리서치 등)
        interviewee: 인터뷰 대상자
        save_to_db: DB 저장 여부 (기본: True)

    Returns:
        signals: 추출된 Signal 목록
        scorecards: Scorecard 평가 결과
        briefs: 생성된 Brief 초안 (승인 대기)
        pending_approvals: 승인 대기 Brief ID 목록
        summary: 결과 요약
    """
    logger.info(
        "Running interview-to-brief pipeline",
        play_id=request.play_id,
        customer=request.customer,
        content_length=len(request.content),
    )

    # 입력 데이터 구성
    input_data = InterviewInput(
        content=request.content,
        play_id=request.play_id,
        customer=request.customer,
        source=request.source,
        channel=request.channel,
        interviewee=request.interviewee,
        interview_date=request.interview_date,
    )

    # 파이프라인 실행
    if request.save_to_db:
        # DB 저장 포함
        session_id = generate_session_id("WF-02")
        run_id = generate_run_id()
        event_manager = SessionEventManager.get_or_create(session_id)
        emitter = WorkflowEventEmitter(event_manager, run_id)

        pipeline = InterviewToBriefPipelineWithDB(emitter, db)
        result = await pipeline.run(input_data)

        # DB 저장
        saved = await pipeline.save_to_db(
            result.signals,
            result.scorecards,
            result.briefs
        )

        # 세션 정리
        SessionEventManager.remove(session_id)

        logger.info(
            "Pipeline completed with DB save",
            saved_signals=len(saved["signals"]),
            saved_scorecards=len(saved["scorecards"]),
            saved_briefs=len(saved["briefs"]),
        )
    else:
        # DB 저장 없이 실행
        pipeline = InterviewToBriefPipeline()
        result = await pipeline.run(input_data)

    return InterviewResponse(
        status="completed",
        signals=result.signals,
        scorecards=result.scorecards,
        briefs=result.briefs,
        pending_approvals=result.pending_approvals,
        summary=result.summary,
    )


@router.post("/interview-to-brief/preview")
async def preview_interview_signals(
    content: str,
    play_id: str | None = None,
    customer: str | None = None,
):
    """
    인터뷰 노트에서 Signal 추출 미리보기 (DB 저장 안함)

    Scorecard/Brief 생성 없이 Signal만 추출하여 확인
    """
    from backend.agent_runtime.workflows.wf_interview_to_brief import (
        extract_signals_from_interview,
    )

    signals = extract_signals_from_interview(content, play_id, customer)

    return {
        "status": "preview",
        "signals_count": len(signals),
        "signals": [
            {
                "title": s.title,
                "pain": s.pain,
                "confidence": s.confidence,
            }
            for s in signals
        ],
        "message": "실제 실행은 POST /api/workflows/interview-to-brief를 사용하세요",
    }


# ============================================================
# WF-04: Inbound Triage
# ============================================================

@router.post("/inbound-triage", response_model=InboundTriageResponse)
async def run_inbound_triage(
    request: InboundTriageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    WF-04: Inbound Triage 파이프라인 실행

    Intake Form → Signal 생성 → 중복 체크 → Play 라우팅 → Scorecard 초안 → SLA 설정

    Args:
        title: 제목 (필수)
        description: 설명 (필수)
        customer_segment: 고객/세그먼트
        pain: Pain Point
        submitter: 제출자
        urgency: 긴급도 (URGENT: 24h, NORMAL: 48h, LOW: 72h)
        source: 원천 (KT, 그룹사, 대외)
        save_to_db: DB 저장 여부 (기본: True)

    Returns:
        signal: 생성된 Signal (중복이면 None)
        is_duplicate: 중복 여부
        similar_signals: 유사 Signal 목록
        assigned_play_id: 배정된 Play ID
        scorecard: Scorecard 초안
        sla: SLA 정보 (deadline, hours_remaining)
        summary: 결과 요약
    """
    logger.info(
        "Running inbound triage pipeline",
        title=request.title,
        urgency=request.urgency,
        source=request.source,
    )

    # 입력 데이터 구성
    input_data = InboundInput(
        title=request.title,
        description=request.description,
        customer_segment=request.customer_segment,
        pain=request.pain,
        submitter=request.submitter,
        urgency=request.urgency,
        source=request.source,
    )

    # 파이프라인 실행
    if request.save_to_db:
        # DB 저장 포함
        session_id = generate_session_id("WF-04")
        run_id = generate_run_id()
        event_manager = SessionEventManager.get_or_create(session_id)
        emitter = WorkflowEventEmitter(event_manager, run_id)

        pipeline = InboundTriagePipelineWithDB(emitter, db)
        result = await pipeline.run(input_data)

        # DB 저장 (중복이 아닐 경우)
        if not result.is_duplicate and result.signal:
            saved = await pipeline.save_to_db(
                result.signal,
                result.scorecard
            )
            logger.info(
                "Pipeline completed with DB save",
                signal_id=saved.get("signal_id"),
                scorecard_id=saved.get("scorecard_id"),
            )
        else:
            logger.info(
                "Duplicate signal detected, skipping DB save",
                similar_count=len(result.similar_signals),
            )

        # 세션 정리
        SessionEventManager.remove(session_id)
    else:
        # DB 저장 없이 실행
        pipeline = InboundTriagePipeline()
        result = await pipeline.run(input_data)

    return InboundTriageResponse(
        status="completed",
        signal=result.signal,
        is_duplicate=result.is_duplicate,
        similar_signals=result.similar_signals,
        assigned_play_id=result.assigned_play_id,
        scorecard=result.scorecard,
        sla=result.sla,
        summary=result.summary,
    )


@router.post("/inbound-triage/preview")
async def preview_inbound_triage(
    title: str,
    description: str,
    urgency: str = "NORMAL",
):
    """
    인바운드 Triage 미리보기 (DB 저장 안함)

    중복 체크 및 Play 라우팅 결과만 확인
    """
    from backend.agent_runtime.workflows.wf_inbound_triage import (
        route_to_play,
        Urgency,
        SLA_HOURS,
    )
    from datetime import datetime, timedelta

    # Play 라우팅
    play_id = route_to_play(title, description)

    # SLA 계산
    try:
        urgency_enum = Urgency(urgency)
    except ValueError:
        urgency_enum = Urgency.NORMAL

    sla_hours = SLA_HOURS[urgency_enum]
    deadline = datetime.now() + timedelta(hours=sla_hours)

    return {
        "status": "preview",
        "assigned_play_id": play_id,
        "urgency": urgency,
        "sla": {
            "hours": sla_hours,
            "deadline": deadline.isoformat(),
        },
        "message": "실제 실행은 POST /api/workflows/inbound-triage를 사용하세요",
    }


# ============================================================
# WF-05: KPI Digest
# ============================================================

class KPIDigestRequest(BaseModel):
    """WF-05 KPI Digest 요청"""
    period: str = "week"  # week, month
    play_ids: list[str] | None = None  # None이면 전체
    notify: bool = False  # Teams/Slack 알림 여부
    include_recommendations: bool = True


class KPIDigestResponse(BaseModel):
    """WF-05 KPI Digest 응답"""
    period: str
    period_start: str
    period_end: str
    metrics: dict[str, Any]
    lead_times: dict[str, Any]
    alerts: list[dict[str, Any]]
    top_plays: list[dict[str, Any]]
    recommendations: list[str]
    status_summary: dict[str, int]
    confluence_url: str | None
    generated_at: str


@router.get("/kpi-digest", response_model=KPIDigestResponse)
async def get_kpi_digest(
    period: str = "week",
    notify: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    WF-05: KPI Digest 리포트 생성

    주간/월간 KPI 리포트 + 지연 Play/Action 경고

    Args:
        period: 기간 (week, month)
        notify: 알림 발송 여부

    Returns:
        metrics: Activity/Signal/Brief/S2 달성 현황
        lead_times: Signal→Brief, Brief→S2 리드타임
        alerts: 목표 미달/지연 경고
        top_plays: 성과 우수 Play 순위
        recommendations: 개선 권고사항
        status_summary: G/Y/R Play 분포
    """
    logger.info(
        "Running KPI Digest",
        period=period,
        notify=notify,
    )

    # 입력 데이터 구성
    input_data = KPIInput(
        period=period,
        notify=notify,
        include_recommendations=True,
    )

    # DB 연동 파이프라인 실행
    session_id = generate_session_id("WF-05")
    run_id = generate_run_id()
    event_manager = SessionEventManager.get_or_create(session_id)
    emitter = WorkflowEventEmitter(event_manager, run_id)

    pipeline = KPIDigestPipelineWithDB(emitter, db)
    result = await pipeline.run(input_data)

    # 세션 정리
    SessionEventManager.remove(session_id)

    return KPIDigestResponse(
        period=result.period,
        period_start=result.period_start,
        period_end=result.period_end,
        metrics=result.metrics,
        lead_times=result.lead_times,
        alerts=result.alerts,
        top_plays=result.top_plays,
        recommendations=result.recommendations,
        status_summary=result.status_summary,
        confluence_url=result.confluence_url,
        generated_at=result.generated_at,
    )


@router.get("/kpi-digest/summary")
async def get_kpi_summary(
    period: str = "week",
):
    """
    KPI 요약 미리보기 (DB 연결 없이)

    빠른 확인용 간략 리포트
    """
    from backend.agent_runtime.workflows.wf_kpi_digest import (
        calculate_period_range,
    )

    period_start, period_end = calculate_period_range(period)

    # 기본 파이프라인으로 실행 (Mock 데이터)
    pipeline = KPIDigestPipeline()
    input_data = KPIInput(
        period=period,
        notify=False,
        include_recommendations=True,
    )

    result = await pipeline.run(input_data)

    return {
        "status": "preview",
        "period": period,
        "period_range": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "metrics_summary": {
            "activity": result.metrics["activity"]["achievement"],
            "signal": result.metrics["signal"]["achievement"],
            "brief": result.metrics["brief"]["achievement"],
            "s2": result.metrics["s2"]["achievement"],
        },
        "alerts_count": len(result.alerts),
        "message": "실제 데이터는 GET /api/workflows/kpi-digest를 사용하세요",
    }
