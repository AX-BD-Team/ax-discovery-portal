"""
Workflows Router

워크플로 실행 REST API 엔드포인트
(SSE 스트리밍이 필요없는 경우)
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent_runtime.event_manager import (
    SessionEventManager,
    WorkflowEventEmitter,
    generate_run_id,
    generate_session_id,
)
from backend.agent_runtime.workflows.wf_confluence_sync import (
    ConfluenceSyncPipeline,
    SyncAction,
    SyncInput,
    SyncTarget,
    SyncTargetType,
)
from backend.agent_runtime.workflows.wf_inbound_triage import (
    InboundInput,
    InboundTriagePipeline,
    InboundTriagePipelineWithDB,
)
from backend.agent_runtime.workflows.wf_interview_to_brief import (
    InterviewInput,
    InterviewToBriefPipeline,
    InterviewToBriefPipelineWithDB,
)
from backend.agent_runtime.workflows.wf_kpi_digest import (
    KPIDigestPipeline,
    KPIDigestPipelineWithDB,
    KPIInput,
)
from backend.agent_runtime.workflows.wf_voc_mining import (
    VoCInput,
    VoCMiningPipeline,
    VoCMiningPipelineWithDB,
)
from backend.api.deps import get_db

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
async def run_interview_to_brief(request: InterviewRequest, db: AsyncSession = Depends(get_db)):
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

        pipeline_db = InterviewToBriefPipelineWithDB(emitter, db)
        result = await pipeline_db.run(input_data)

        # DB 저장
        saved = await pipeline_db.save_to_db(result.signals, result.scorecards, result.briefs)

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
        pipeline_basic = InterviewToBriefPipeline()
        result = await pipeline_basic.run(input_data)

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
async def run_inbound_triage(request: InboundTriageRequest, db: AsyncSession = Depends(get_db)):
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

        pipeline_db = InboundTriagePipelineWithDB(emitter, db)
        result = await pipeline_db.run(input_data)

        # DB 저장 (중복이 아닐 경우)
        if not result.is_duplicate and result.signal_id:
            # Signal dict 구성
            signal_dict_to_save = {
                "signal_id": result.signal_id,
                "play_id": result.play_id,
            }
            saved = await pipeline_db.save_to_db(signal_dict_to_save, result.scorecard)
            logger.info(
                "Pipeline completed with DB save",
                signal_id=saved.get("signal_id"),
                scorecard_id=saved.get("scorecard_id"),
            )
        else:
            similar_signals = result.summary.get("similar_signals", [])
            logger.info(
                "Duplicate signal detected, skipping DB save",
                similar_count=len(similar_signals),
            )

        # 세션 정리
        SessionEventManager.remove(session_id)
    else:
        # DB 저장 없이 실행
        pipeline_basic = InboundTriagePipeline()
        result = await pipeline_basic.run(input_data)

    # InboundOutput → InboundTriageResponse 필드 매핑
    # signal dict 구성 (InboundOutput에는 signal_id만 있음)
    signal_dict = (
        {
            "signal_id": result.signal_id,
            "play_id": result.play_id,
        }
        if result.signal_id
        else None
    )

    # sla dict 구성 (InboundOutput에는 sla_deadline과 next_action이 별도로 있음)
    sla_dict = {
        "deadline": result.sla_deadline,
        "next_action": result.next_action,
    }

    # similar_signals는 summary에서 추출
    similar_signals = result.summary.get("similar_signals", [])

    return InboundTriageResponse(
        status="completed",
        signal=signal_dict,
        is_duplicate=result.is_duplicate,
        similar_signals=similar_signals,
        assigned_play_id=result.play_id,
        scorecard=result.scorecard,
        sla=sla_dict,
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
    from datetime import datetime, timedelta

    from backend.agent_runtime.workflows.wf_inbound_triage import (
        SLA_HOURS,
        Urgency,
        route_to_play,
    )

    # Play 라우팅
    play_id = route_to_play(title, description, None)

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
    period: str = "week", notify: bool = False, db: AsyncSession = Depends(get_db)
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


# ============================================================
# WF-03: VoC Mining
# ============================================================


class VoCMiningRequest(BaseModel):
    """WF-03 VoC Mining 요청"""

    source_type: str = "text"  # csv, excel, api, text
    text_content: str | None = None  # 텍스트 내용
    api_data: list[dict[str, Any]] | None = None  # API 데이터
    play_id: str = "KT_Desk_V01_VoC"
    source: str = "KT"
    channel: str = "데스크리서치"
    min_frequency: int = 5
    max_themes: int = 5
    save_to_db: bool = True


class VoCThemeSummary(BaseModel):
    """VoC 테마 요약"""

    theme_id: str
    name: str
    frequency: int
    severity: str
    keywords: list[str]


class VoCMiningResponse(BaseModel):
    """WF-03 VoC Mining 응답"""

    status: str
    themes: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    brief_candidates: list[dict[str, Any]]
    summary: dict[str, Any]


@router.post("/voc-mining", response_model=VoCMiningResponse)
async def run_voc_mining(request: VoCMiningRequest, db: AsyncSession = Depends(get_db)):
    """
    WF-03: VoC Mining 파이프라인 실행

    VoC/티켓 데이터 → 테마화 → Signal 생성 → Brief 후보

    Args:
        source_type: 데이터 소스 타입 (csv, excel, api, text)
        text_content: 텍스트 내용 (source_type=text일 때)
        api_data: API 데이터 (source_type=api일 때)
        play_id: Play ID
        source: 원천 (KT, 그룹사, 대외)
        channel: 채널
        min_frequency: 테마 최소 빈도
        max_themes: 최대 테마 개수
        save_to_db: DB 저장 여부 (기본: True)

    Returns:
        themes: 추출된 테마 목록
        signals: 생성된 Signal 목록
        brief_candidates: Brief 후보 목록
        summary: 결과 요약
    """
    logger.info(
        "Running VoC Mining pipeline",
        source_type=request.source_type,
        play_id=request.play_id,
    )

    # 입력 데이터 구성
    input_data = VoCInput(
        source_type=request.source_type,
        text_content=request.text_content,
        api_data=request.api_data,
        play_id=request.play_id,
        source=request.source,
        channel=request.channel,
        min_frequency=request.min_frequency,
        max_themes=request.max_themes,
    )

    # 파이프라인 실행
    if request.save_to_db:
        # DB 저장 포함
        session_id = generate_session_id("WF-03")
        run_id = generate_run_id()
        event_manager = SessionEventManager.get_or_create(session_id)
        emitter = WorkflowEventEmitter(event_manager, run_id)

        pipeline_db = VoCMiningPipelineWithDB(emitter, db)
        result = await pipeline_db.run(input_data)  # run() 내부에서 DB 저장 자동 수행

        # 세션 정리
        SessionEventManager.remove(session_id)

        logger.info(
            "VoC Mining completed with DB save",
            saved_signals=result.summary.get("saved_signals", 0),
            saved_scorecards=result.summary.get("saved_scorecards", 0),
        )
    else:
        # DB 저장 없이 실행
        pipeline_basic = VoCMiningPipeline()
        result = await pipeline_basic.run(input_data)

    return VoCMiningResponse(
        status="completed",
        themes=result.themes,
        signals=result.signals,
        brief_candidates=result.brief_candidates,
        summary=result.summary,
    )


@router.post("/voc-mining/preview")
async def preview_voc_mining(
    source_type: str = "text",
    text_content: str | None = None,
    min_frequency: int = 5,
    max_themes: int = 5,
):
    """
    VoC Mining 미리보기 (DB 저장 안함)

    빠른 확인용 테마 추출 및 Signal 생성
    """
    # 입력 데이터 구성
    input_data = VoCInput(
        source_type=source_type,
        text_content=text_content,
        min_frequency=min_frequency,
        max_themes=max_themes,
    )

    # 기본 파이프라인 실행
    pipeline = VoCMiningPipeline()
    result = await pipeline.run(input_data)

    return {
        "status": "preview",
        "themes_count": len(result.themes),
        "themes": [
            {
                "theme_id": t.get("theme_id"),
                "name": t.get("name"),
                "frequency": t.get("frequency"),
                "severity": t.get("severity"),
            }
            for t in result.themes
        ],
        "signals_count": len(result.signals),
        "brief_candidates_count": len(result.brief_candidates),
        "message": "실제 실행은 POST /api/workflows/voc-mining를 사용하세요",
    }


# ============================================================
# WF-06: Confluence Sync
# ============================================================


class ConfluenceSyncRequest(BaseModel):
    """WF-06 Confluence Sync 요청"""

    targets: list[dict[str, Any]] = []
    sync_type: str = "realtime"
    play_id: str | None = None
    dry_run: bool = False


class ConfluenceSyncResponse(BaseModel):
    """WF-06 Confluence Sync 응답"""

    status: str
    results: list[dict[str, Any]]
    summary: dict[str, int]


@router.post("/confluence-sync", response_model=ConfluenceSyncResponse)
async def run_confluence_sync(request: ConfluenceSyncRequest):
    """
    WF-06: Confluence Sync 파이프라인 실행

    Signal/Scorecard/Brief/Play → Confluence 페이지 동기화

    Args:
        targets: 동기화 대상 목록
        sync_type: 동기화 타입 (realtime, batch)
        play_id: Play ID (선택)
        dry_run: 테스트 모드 (실제 동기화 안함)

    Returns:
        results: 각 대상별 동기화 결과
        summary: 성공/실패/스킵 요약
    """
    logger.info(
        "Running Confluence Sync pipeline",
        targets_count=len(request.targets),
        sync_type=request.sync_type,
        dry_run=request.dry_run,
    )

    sync_targets = []
    for t in request.targets:
        sync_targets.append(
            SyncTarget(
                target_type=SyncTargetType(t.get("target_type", "signal")),
                target_id=t.get("target_id", ""),
                data=t.get("data", {}),
                action=SyncAction(t.get("action", "create_page")),
                play_id=t.get("play_id"),
                page_id=t.get("page_id"),
            )
        )

    input_data = SyncInput(
        targets=sync_targets,
        sync_type=request.sync_type,
        play_id=request.play_id,
        dry_run=request.dry_run,
    )

    pipeline = ConfluenceSyncPipeline()
    result = await pipeline.run(input_data)

    return ConfluenceSyncResponse(
        status="completed",
        results=[
            {
                "target_type": r.target_type.value,
                "target_id": r.target_id,
                "action": r.action.value,
                "status": r.status,
                "page_id": r.page_id,
                "page_url": r.page_url,
                "error": r.error,
            }
            for r in result.results
        ],
        summary=result.summary,
    )


@router.post("/confluence-sync/signal")
async def sync_signal_to_confluence(
    signal_id: str,
    signal_data: dict[str, Any],
    action: str = "create_page",
):
    """Signal을 Confluence에 동기화"""
    pipeline = ConfluenceSyncPipeline()

    try:
        result = await pipeline.sync_signal(signal_data, SyncAction(action))
        return {
            "status": result.status,
            "page_id": result.page_id,
            "page_url": result.page_url,
            "error": result.error,
        }
    except ValueError as e:
        return {"status": "error", "error": str(e)}


@router.post("/confluence-sync/brief")
async def sync_brief_to_confluence(
    brief_id: str,
    brief_data: dict[str, Any],
    action: str = "create_page",
):
    """Brief를 Confluence에 동기화"""
    pipeline = ConfluenceSyncPipeline()

    try:
        result = await pipeline.sync_brief(brief_data, SyncAction(action))
        return {
            "status": result.status,
            "page_id": result.page_id,
            "page_url": result.page_url,
            "error": result.error,
        }
    except ValueError as e:
        return {"status": "error", "error": str(e)}


@router.post("/confluence-sync/activity-log")
async def log_activity_to_confluence(activity_data: dict[str, Any]):
    """Activity 로그를 Confluence Live Doc에 추가"""
    pipeline = ConfluenceSyncPipeline()
    result = await pipeline.log_activity(activity_data)

    return {
        "status": result.status,
        "page_id": result.page_id,
        "page_url": result.page_url,
        "error": result.error,
    }


@router.post("/confluence-sync/preview")
async def preview_confluence_sync(
    target_type: str,
    target_id: str,
    data: dict[str, Any],
):
    """Confluence 동기화 미리보기"""
    from backend.agent_runtime.workflows.wf_confluence_sync import (
        format_brief_page,
        format_scorecard_page,
        format_signal_page,
    )

    content = ""
    if target_type == "signal":
        content = format_signal_page(data)
    elif target_type == "scorecard":
        content = format_scorecard_page(data)
    elif target_type == "brief":
        content = format_brief_page(data)
    else:
        content = f"지원되지 않는 타입: {target_type}"

    return {
        "status": "preview",
        "target_type": target_type,
        "target_id": target_id,
        "content_preview": content[:500] + "..." if len(content) > 500 else content,
        "content_length": len(content),
        "message": "실제 동기화는 POST /api/workflows/confluence-sync를 사용하세요",
    }


# ============================================================
# WF-06: Confluence Sync (양방향)
# ============================================================


class ConfluenceImportRequest(BaseModel):
    """Confluence Import 요청"""

    target_type: str = "signal"  # signal, scorecard, brief, all
    page_ids: list[str] | None = None  # 특정 페이지 ID 목록
    label: str | None = None  # 검색할 라벨


class ConfluenceImportResponse(BaseModel):
    """Confluence Import 응답"""

    status: str
    total: int
    imported: int
    updated: int
    skipped: int
    failed: int
    details: list[dict[str, Any]]


class BidirectionalSyncResponse(BaseModel):
    """양방향 동기화 응답"""

    status: str
    import_results: dict[str, Any]
    export_results: dict[str, Any]


@router.post("/confluence-sync/import", response_model=ConfluenceImportResponse)
async def import_from_confluence(
    request: ConfluenceImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    WF-06: Confluence → DB Import

    Confluence 페이지를 파싱하여 DB에 저장

    Args:
        target_type: 가져올 대상 타입 (signal, scorecard, brief, all)
        page_ids: 가져올 페이지 ID 목록 (없으면 라벨로 검색)
        label: 검색할 라벨 (page_ids가 없을 때)

    Returns:
        total: 처리한 페이지 수
        imported: 새로 생성된 항목 수
        updated: 업데이트된 항목 수
        skipped: 스킵된 항목 수
        failed: 실패한 항목 수
        details: 각 페이지별 상세 결과
    """
    from backend.agent_runtime.workflows.wf_confluence_sync import (
        ConfluenceSyncPipelineWithDB,
    )

    logger.info(
        "Running Confluence Import",
        target_type=request.target_type,
        page_ids=request.page_ids,
        label=request.label,
    )

    # 이벤트 세션 설정
    session_id = generate_session_id("WF-06-import")
    run_id = generate_run_id()
    event_manager = SessionEventManager.get_or_create(session_id)
    emitter = WorkflowEventEmitter(event_manager, run_id)

    # 파이프라인 실행
    pipeline = ConfluenceSyncPipelineWithDB(emitter, db)
    result = await pipeline.import_from_confluence(
        target_type=SyncTargetType(request.target_type),
        page_ids=request.page_ids,
        label=request.label,
    )

    # 세션 정리
    SessionEventManager.remove(session_id)

    return ConfluenceImportResponse(
        status="completed",
        total=result["total"],
        imported=result["imported"],
        updated=result["updated"],
        skipped=result["skipped"],
        failed=result["failed"],
        details=result["details"],
    )


@router.post("/confluence-sync/from-db")
async def sync_from_db_to_confluence(
    target_type: str = "all",
    target_ids: list[str] | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    WF-06: DB → Confluence 배치 동기화

    DB 데이터를 Confluence 페이지로 동기화

    Args:
        target_type: 동기화 대상 타입 (signal, scorecard, brief, all)
        target_ids: 동기화할 ID 목록 (없으면 최근 100개)

    Returns:
        동기화 결과 summary
    """
    from backend.agent_runtime.workflows.wf_confluence_sync import (
        ConfluenceSyncPipelineWithDB,
    )

    logger.info(
        "Running DB → Confluence sync",
        target_type=target_type,
        target_ids=target_ids,
    )

    # 이벤트 세션 설정
    session_id = generate_session_id("WF-06-export")
    run_id = generate_run_id()
    event_manager = SessionEventManager.get_or_create(session_id)
    emitter = WorkflowEventEmitter(event_manager, run_id)

    # 파이프라인 실행
    pipeline = ConfluenceSyncPipelineWithDB(emitter, db)
    result = await pipeline.sync_from_db(
        target_type=SyncTargetType(target_type),
        target_ids=target_ids,
    )

    # 세션 정리
    SessionEventManager.remove(session_id)

    return {
        "status": "completed",
        "results_count": len(result.results),
        "summary": result.summary,
    }


@router.post("/confluence-sync/bidirectional", response_model=BidirectionalSyncResponse)
async def run_bidirectional_sync(
    target_type: str = "all",
    db: AsyncSession = Depends(get_db),
):
    """
    WF-06: 양방향 동기화

    1. Confluence → DB: 새로운/변경된 페이지 import
    2. DB → Confluence: 새로운/변경된 데이터 export

    Args:
        target_type: 동기화 대상 타입 (signal, scorecard, brief, all)

    Returns:
        import_results: Confluence → DB 결과
        export_results: DB → Confluence 결과
    """
    from backend.agent_runtime.workflows.wf_confluence_sync import (
        ConfluenceSyncPipelineWithDB,
    )

    logger.info(
        "Running bidirectional sync",
        target_type=target_type,
    )

    # 이벤트 세션 설정
    session_id = generate_session_id("WF-06-bidirectional")
    run_id = generate_run_id()
    event_manager = SessionEventManager.get_or_create(session_id)
    emitter = WorkflowEventEmitter(event_manager, run_id)

    # 파이프라인 실행
    pipeline = ConfluenceSyncPipelineWithDB(emitter, db)
    result = await pipeline.bidirectional_sync(
        target_type=SyncTargetType(target_type),
    )

    # 세션 정리
    SessionEventManager.remove(session_id)

    return BidirectionalSyncResponse(
        status="completed",
        import_results=result["import_results"],
        export_results=result["export_results"],
    )


@router.post("/confluence-sync/parse-preview")
async def preview_confluence_page_parsing(
    content: str,
    page_type: str | None = None,
):
    """
    Confluence 페이지 파싱 미리보기

    Markdown 내용을 파싱하여 추출 결과 확인

    Args:
        content: Markdown 형식의 페이지 내용
        page_type: 페이지 타입 (signal, scorecard, brief / 없으면 자동 감지)

    Returns:
        detected_type: 감지된 페이지 타입
        parsed_data: 파싱된 데이터
    """
    from backend.agent_runtime.workflows.wf_confluence_sync import (
        detect_page_type,
        parse_brief_page,
        parse_scorecard_page,
        parse_signal_page,
    )

    # 페이지 타입 감지
    detected = SyncTargetType(page_type) if page_type else detect_page_type(content)

    if not detected:
        return {
            "status": "error",
            "error": "페이지 타입을 감지할 수 없습니다",
            "hint": "page_type 파라미터를 명시하거나, Signal/Scorecard/Brief 형식의 Markdown을 입력하세요",
        }

    # 타입별 파싱
    if detected == SyncTargetType.SIGNAL:
        parsed = parse_signal_page(content)
    elif detected == SyncTargetType.SCORECARD:
        parsed = parse_scorecard_page(content)
    elif detected == SyncTargetType.BRIEF:
        parsed = parse_brief_page(content)
    else:
        return {
            "status": "error",
            "error": f"지원되지 않는 타입: {detected}",
        }

    return {
        "status": "preview",
        "detected_type": detected.value,
        "parsed_data": parsed,
        "message": "실제 import는 POST /api/workflows/confluence-sync/import를 사용하세요",
    }


# ============================================================
# WF-07: External Scout (외부 세미나 수집)
# ============================================================


class ExternalScoutRequest(BaseModel):
    """WF-07 외부 스카우트 요청"""

    sources: list[str] = ["rss", "festa", "eventbrite"]  # 수집 소스
    keywords: list[str] | None = None  # 필터 키워드
    categories: list[str] | None = None  # 필터 카테고리
    rss_feed_urls: list[str] | None = None  # RSS 피드 URL 목록
    festa_categories: list[str] | None = None  # Festa 카테고리
    eventbrite_location: str | None = None  # Eventbrite 지역
    limit_per_source: int = 50  # 소스당 최대 수집 개수
    play_id: str = "EXT_Desk_D01_Seminar"  # Play ID
    save_to_db: bool = True  # DB 저장 여부
    sync_confluence: bool = True  # Confluence 동기화 여부


class ExternalScoutResponse(BaseModel):
    """WF-07 외부 스카우트 응답"""

    status: str
    total_collected: int
    total_saved: int
    duplicates_skipped: int
    by_source: dict[str, Any]
    activities_count: int
    confluence_updated: bool
    confluence_url: str | None
    duration_seconds: float
    errors: list[dict[str, Any]]


@router.post("/external-scout", response_model=ExternalScoutResponse)
async def run_external_scout(
    request: ExternalScoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    WF-07: External Scout 파이프라인 실행

    외부 세미나/이벤트 정보를 자동으로 수집하여 Activity로 등록

    지원 소스:
    - RSS: 기술 블로그, 이벤트 사이트 피드
    - Festa: festa.io IT/스타트업 이벤트
    - Eventbrite: 글로벌 이벤트 플랫폼

    Args:
        sources: 수집 소스 목록 (기본: rss, festa, eventbrite)
        keywords: 필터링할 키워드 (제목/설명에 포함)
        categories: 필터링할 카테고리
        rss_feed_urls: 추가 RSS 피드 URL
        festa_categories: Festa 카테고리 (tech, ai, startup 등)
        eventbrite_location: Eventbrite 지역 (예: Korea, Seoul)
        limit_per_source: 소스당 최대 수집 개수
        play_id: 저장할 Play ID
        save_to_db: DB 저장 여부 (기본: True)
        sync_confluence: Confluence 동기화 여부 (기본: True)

    Returns:
        total_collected: 총 수집된 세미나 수
        total_saved: DB에 저장된 Activity 수
        duplicates_skipped: 중복으로 스킵된 수
        by_source: 소스별 통계
        confluence_updated: Confluence 동기화 성공 여부
        duration_seconds: 실행 시간 (초)
        errors: 에러 목록
    """
    from backend.agent_runtime.workflows.wf_external_scout import (
        ExternalScoutInput,
        ExternalScoutPipeline,
        ExternalScoutPipelineWithDB,
    )

    logger.info(
        "Running external scout pipeline",
        sources=request.sources,
        keywords=request.keywords,
        save_to_db=request.save_to_db,
    )

    # 입력 데이터 구성
    # ⚠️ festa_categories 제거 (Festa 2025.01.31 서비스 종료)
    input_data = ExternalScoutInput(
        sources=request.sources,
        keywords=request.keywords,
        categories=request.categories,
        rss_feed_urls=request.rss_feed_urls,
        eventbrite_location=request.eventbrite_location,
        limit_per_source=request.limit_per_source,
        play_id=request.play_id,
        save_to_db=request.save_to_db,
        sync_confluence=request.sync_confluence,
    )

    # 파이프라인 실행
    pipeline = ExternalScoutPipelineWithDB(db) if request.save_to_db else ExternalScoutPipeline()
    result = await pipeline.run(input_data)

    logger.info(
        "External scout completed",
        total_collected=result.total_collected,
        total_saved=result.total_saved,
        duplicates_skipped=result.duplicates_skipped,
    )

    return ExternalScoutResponse(
        status="completed",
        total_collected=result.total_collected,
        total_saved=result.total_saved,
        duplicates_skipped=result.duplicates_skipped,
        by_source=result.by_source,
        activities_count=len(result.activities),
        confluence_updated=result.confluence_updated,
        confluence_url=result.confluence_url,
        duration_seconds=result.duration_seconds,
        errors=result.errors,
    )


@router.post("/external-scout/preview")
async def preview_external_scout(
    sources: list[str] | None = None,
    keywords: list[str] | None = None,
    limit_per_source: int = 10,
):
    """
    외부 스카우트 미리보기 (DB 저장 안함)

    소스별 수집 가능한 세미나 목록 확인

    Args:
        sources: 수집 소스 (기본: rss, festa, eventbrite)
        keywords: 필터 키워드
        limit_per_source: 소스당 최대 개수 (기본: 10)

    Returns:
        각 소스별 수집된 세미나 목록 미리보기
    """
    from backend.agent_runtime.workflows.wf_external_scout import (
        ExternalScoutInput,
        ExternalScoutPipeline,
    )

    input_data = ExternalScoutInput(
        sources=sources or ["rss", "festa", "eventbrite"],
        keywords=keywords,
        limit_per_source=limit_per_source,
        save_to_db=False,
        sync_confluence=False,
    )

    pipeline = ExternalScoutPipeline()
    result = await pipeline.run(input_data)

    return {
        "status": "preview",
        "total_collected": result.total_collected,
        "by_source": result.by_source,
        "activities": [
            {
                "title": act.get("title", "")[:50],
                "url": act.get("url"),
                "date": act.get("date"),
                "source_type": act.get("source_type"),
            }
            for act in result.activities[:20]  # 최대 20개만 표시
        ],
        "message": "실제 실행은 POST /api/workflows/external-scout를 사용하세요",
    }
