"""
Evals Router

AI 에이전트 평가(Evals) 플랫폼 REST API
- Suite 관리: 등록된 Suite 목록 조회, 상세 조회, YAML 동기화
- Run 관리: 평가 실행 생성, 목록 조회, 취소
- Trial 조회: Trial 목록/상세, 트랜스크립트, 결과 상태
- 통계 및 분석: 통계 요약, 회귀 탐지
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.deps import get_db
from backend.database.models.eval import (
    EvalOutcome,
    EvalRun,
    EvalRunStatus,
    EvalSuite,
    EvalSuitePurpose,
    EvalTask,
    EvalTranscript,
    EvalTrial,
)

router = APIRouter()
logger = structlog.get_logger()


# ============================================================
# Pydantic 스키마
# ============================================================


# === Suite 관련 스키마 ===


class SuiteResponse(BaseModel):
    """Suite 응답"""

    suite_id: str
    name: str
    description: str | None = None
    version: str
    purpose: str
    domain: str | None = None
    owner_team: str | None = None
    tags: list[str] | None = None
    task_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskSummaryResponse(BaseModel):
    """Task 요약 응답"""

    task_id: str
    type: str
    description: str
    version: str
    domain: str | None = None
    difficulty: str
    risk: str
    expected_pass_rate: float | None = None
    owner: str | None = None
    tags: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class SuiteDetailResponse(BaseModel):
    """Suite 상세 응답 (Task 목록 포함)"""

    suite_id: str
    name: str
    description: str | None = None
    version: str
    purpose: str
    domain: str | None = None
    owner_team: str | None = None
    tags: list[str] | None = None
    defaults_config: dict | None = None
    schedule_config: dict | None = None
    gates_config: dict | None = None
    notifications_config: dict | None = None
    tasks: list[TaskSummaryResponse] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SyncResult(BaseModel):
    """YAML 동기화 결과"""

    synced_suites: int = 0
    synced_tasks: int = 0
    created_suites: list[str] = []
    updated_suites: list[str] = []
    created_tasks: list[str] = []
    updated_tasks: list[str] = []
    errors: list[str] = []


# === Run 관련 스키마 ===


class CreateRunRequest(BaseModel):
    """평가 실행 생성 요청"""

    suite_id: str | None = Field(None, description="실행할 Suite ID")
    task_ids: list[str] | None = Field(None, description="실행할 Task ID 목록")
    trial_k: int = Field(5, ge=1, le=20, description="트라이얼 횟수")
    parallel: bool = Field(True, description="병렬 실행 여부")
    triggered_by: str = Field("manual", description="트리거 (ci/nightly/manual)")
    git_sha: str | None = Field(None, description="Git commit SHA")
    git_branch: str | None = Field(None, description="Git 브랜치")
    pr_number: int | None = Field(None, description="PR 번호")
    agent_version: str | None = Field(None, description="에이전트 버전")
    model_version: str | None = Field(None, description="모델 버전")


class RunResponse(BaseModel):
    """평가 실행 응답"""

    run_id: str
    suite_id: str | None = None
    status: str
    triggered_by: str
    git_sha: str | None = None
    git_branch: str | None = None
    pr_number: int | None = None
    trial_k: int
    parallel: bool
    task_ids: list[str] | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RunSummaryResponse(BaseModel):
    """Run 요약 응답"""

    run_id: str
    suite_id: str | None = None
    suite_name: str | None = None
    status: str
    triggered_by: str
    git_sha: str | None = None
    total_tasks: int = 0
    passed_tasks: int = 0
    failed_tasks: int = 0
    pass_rate: float = 0.0
    total_cost_usd: float = 0.0
    total_duration_seconds: float = 0.0
    gate_passed: bool | None = None
    gate_decision: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskResultSummary(BaseModel):
    """Task별 결과 요약"""

    task_id: str
    task_description: str | None = None
    total_trials: int = 0
    passed_trials: int = 0
    pass_rate: float = 0.0
    avg_score: float | None = None
    avg_duration_seconds: float = 0.0
    total_cost_usd: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class RunDetailResponse(BaseModel):
    """Run 상세 응답 (Task별 결과 포함)"""

    run_id: str
    suite_id: str | None = None
    suite_name: str | None = None
    status: str
    triggered_by: str
    git_sha: str | None = None
    git_branch: str | None = None
    pr_number: int | None = None
    agent_version: str | None = None
    model_version: str | None = None
    suite_version: str | None = None
    trial_k: int
    parallel: bool
    task_ids: list[str] | None = None
    total_tasks: int = 0
    passed_tasks: int = 0
    failed_tasks: int = 0
    pass_rate: float = 0.0
    total_cost_usd: float = 0.0
    total_duration_seconds: float = 0.0
    gate_passed: bool | None = None
    gate_decision: str | None = None
    gate_reason: str | None = None
    task_results: list[TaskResultSummary] = []
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CancelResponse(BaseModel):
    """취소 응답"""

    run_id: str
    status: str
    message: str
    cancelled_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === Trial 관련 스키마 ===


class TrialSummaryResponse(BaseModel):
    """Trial 요약 응답"""

    trial_id: str
    run_id: str
    task_id: str
    trial_index: int
    status: str
    passed: bool | None = None
    score: float | None = None
    duration_seconds: float = 0.0
    cost_usd: float = 0.0
    error_type: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class GraderResultResponse(BaseModel):
    """채점 결과 응답"""

    grader_id: str
    grader_type: str
    score: float
    passed: bool
    partial_scores: dict | None = None
    explanation: str | None = None
    judge_model: str | None = None
    confidence: float | None = None
    duration_seconds: float = 0.0
    graded_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TrialDetailResponse(BaseModel):
    """Trial 상세 응답"""

    trial_id: str
    run_id: str
    task_id: str
    task_description: str | None = None
    trial_index: int
    seed: int | None = None
    env_snapshot_id: str | None = None
    status: str
    passed: bool | None = None
    score: float | None = None
    duration_seconds: float = 0.0
    cost_usd: float = 0.0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    error_message: str | None = None
    error_type: str | None = None
    grader_results: list[GraderResultResponse] = []
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TranscriptResponse(BaseModel):
    """트랜스크립트 응답"""

    trial_id: str
    messages: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    intermediate_states: list[dict[str, Any]] = []
    n_turns: int = 0
    n_tool_calls: int = 0
    n_errors: int = 0
    n_retries: int = 0
    raw_transcript: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OutcomeResponse(BaseModel):
    """Outcome 응답"""

    trial_id: str
    final_state: dict[str, Any] = {}
    artifacts: list[dict[str, Any]] = []
    db_changes: list[dict[str, Any]] = []
    file_hashes: dict[str, str] = {}
    api_responses: list[dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


# === 통계 관련 스키마 ===


class DailyStats(BaseModel):
    """일별 통계"""

    date: str
    total_runs: int = 0
    total_trials: int = 0
    passed_trials: int = 0
    pass_rate: float = 0.0
    total_cost_usd: float = 0.0
    avg_duration_seconds: float = 0.0


class StatsSummaryResponse(BaseModel):
    """통계 요약 응답"""

    period_start: datetime
    period_end: datetime
    suite_id: str | None = None
    total_runs: int = 0
    total_trials: int = 0
    passed_trials: int = 0
    failed_trials: int = 0
    overall_pass_rate: float = 0.0
    total_cost_usd: float = 0.0
    avg_cost_per_run: float = 0.0
    avg_duration_per_trial: float = 0.0
    daily_stats: list[DailyStats] = []

    model_config = ConfigDict(from_attributes=True)


class RegressionItem(BaseModel):
    """회귀 항목"""

    task_id: str
    task_description: str | None = None
    previous_pass_rate: float
    current_pass_rate: float
    delta: float
    severity: str  # low, medium, high


class RegressionReport(BaseModel):
    """회귀 탐지 리포트"""

    suite_id: str
    compared_runs: int
    baseline_run_id: str | None = None
    current_run_id: str | None = None
    regressions: list[RegressionItem] = []
    improvements: list[RegressionItem] = []
    total_regressions: int = 0
    total_improvements: int = 0
    overall_delta: float = 0.0
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Suite 관리 엔드포인트
# ============================================================


@router.get("/suites", response_model=list[SuiteResponse])
async def list_suites(
    db: Annotated[AsyncSession, Depends(get_db)],
    purpose: Annotated[str | None, Query(description="목적 필터")] = None,
    domain: Annotated[str | None, Query(description="도메인 필터")] = None,
):
    """
    등록된 Suite 목록 조회

    Args:
        purpose: Suite 목적 필터 (capability/regression/benchmark/safety)
        domain: 도메인 필터

    Returns:
        Suite 목록
    """
    # 서브쿼리로 task_count 계산 (N+1 문제 해결)
    task_count_subquery = (
        select(
            EvalTask.suite_id,
            func.count(EvalTask.task_id).label("task_count"),
        )
        .group_by(EvalTask.suite_id)
        .subquery()
    )

    # Suite와 task_count를 LEFT JOIN으로 한 번에 조회
    query = select(
        EvalSuite,
        func.coalesce(task_count_subquery.c.task_count, 0).label("task_count"),
    ).outerjoin(task_count_subquery, EvalSuite.suite_id == task_count_subquery.c.suite_id)

    if purpose:
        try:
            purpose_enum = EvalSuitePurpose(purpose)
            query = query.where(EvalSuite.purpose == purpose_enum)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid purpose: {purpose}. Valid values: {[p.value for p in EvalSuitePurpose]}",
            ) from e

    if domain:
        query = query.where(EvalSuite.domain == domain)

    query = query.order_by(EvalSuite.name)
    result = await db.execute(query)
    rows = result.all()

    # 결과 변환
    responses = []
    for row in rows:
        suite = row[0]  # EvalSuite 객체
        task_count = row[1]  # task_count 값

        responses.append(
            SuiteResponse(
                suite_id=suite.suite_id,
                name=suite.name,
                description=suite.description,
                version=suite.version,
                purpose=suite.purpose.value,
                domain=suite.domain,
                owner_team=suite.owner_team,
                tags=suite.tags,
                task_count=task_count,
                created_at=suite.created_at,
                updated_at=suite.updated_at,
            )
        )

    return responses


@router.get("/suites/{suite_id}", response_model=SuiteDetailResponse)
async def get_suite(
    suite_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Suite 상세 조회 (Task 목록 포함)

    Args:
        suite_id: Suite ID

    Returns:
        Suite 상세 정보 (하위 Task 포함)
    """
    query = (
        select(EvalSuite)
        .options(selectinload(EvalSuite.tasks))
        .where(EvalSuite.suite_id == suite_id)
    )
    result = await db.execute(query)
    suite = result.scalar_one_or_none()

    if not suite:
        raise HTTPException(status_code=404, detail=f"Suite not found: {suite_id}")

    tasks = [
        TaskSummaryResponse(
            task_id=task.task_id,
            type=task.type.value,
            description=task.description,
            version=task.version,
            domain=task.domain,
            difficulty=task.difficulty,
            risk=task.risk,
            expected_pass_rate=task.expected_pass_rate,
            owner=task.owner,
            tags=task.tags,
        )
        for task in suite.tasks
    ]

    return SuiteDetailResponse(
        suite_id=suite.suite_id,
        name=suite.name,
        description=suite.description,
        version=suite.version,
        purpose=suite.purpose.value,
        domain=suite.domain,
        owner_team=suite.owner_team,
        tags=suite.tags,
        defaults_config=suite.defaults_config,
        schedule_config=suite.schedule_config,
        gates_config=suite.gates_config,
        notifications_config=suite.notifications_config,
        tasks=tasks,
        created_at=suite.created_at,
        updated_at=suite.updated_at,
    )


@router.post("/suites/sync", response_model=SyncResult)
async def sync_suites_from_yaml(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    YAML 파일에서 Suite/Task 동기화

    evals/suites 디렉토리의 YAML 파일을 파싱하여
    DB에 Suite와 Task를 생성/업데이트합니다.

    Returns:
        동기화 결과 (생성/업데이트된 Suite/Task 수)
    """
    # TODO: YAML 파일 파싱 및 동기화 구현
    # 현재는 스텁 응답 반환
    logger.info("Suite sync from YAML requested")

    return SyncResult(
        synced_suites=0,
        synced_tasks=0,
        created_suites=[],
        updated_suites=[],
        created_tasks=[],
        updated_tasks=[],
        errors=["YAML sync not yet implemented"],
    )


# ============================================================
# Run 관리 엔드포인트
# ============================================================


async def _execute_run(run_id: str, db_url: str):
    """
    백그라운드에서 평가 실행

    Args:
        run_id: 실행 ID
        db_url: 데이터베이스 URL
    """
    # TODO: 실제 평가 실행 로직 구현
    logger.info("Background run execution started", run_id=run_id)


@router.post("/runs", response_model=RunResponse)
async def create_run(
    request: CreateRunRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    평가 실행 시작

    Args:
        request: 실행 요청 (suite_id 또는 task_ids 지정)
        background_tasks: 백그라운드 태스크 핸들러

    Returns:
        생성된 Run 정보
    """
    # Validation: suite_id 또는 task_ids 중 하나는 필수
    if not request.suite_id and not request.task_ids:
        raise HTTPException(
            status_code=400,
            detail="Either suite_id or task_ids must be provided",
        )

    # Suite 존재 확인 (suite_id가 주어진 경우)
    suite_version = None
    if request.suite_id:
        suite_query = select(EvalSuite).where(EvalSuite.suite_id == request.suite_id)
        suite_result = await db.execute(suite_query)
        suite = suite_result.scalar_one_or_none()
        if not suite:
            raise HTTPException(status_code=404, detail=f"Suite not found: {request.suite_id}")
        suite_version = suite.version

    # Task 존재 확인 (task_ids가 주어진 경우)
    if request.task_ids:
        task_query = select(EvalTask).where(EvalTask.task_id.in_(request.task_ids))
        task_result = await db.execute(task_query)
        found_tasks = task_result.scalars().all()
        found_task_ids = {t.task_id for t in found_tasks}
        missing_tasks = set(request.task_ids) - found_task_ids
        if missing_tasks:
            raise HTTPException(
                status_code=404,
                detail=f"Tasks not found: {list(missing_tasks)}",
            )

    # Run ID 생성
    run_id = f"run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    # Run 생성
    run = EvalRun(
        run_id=run_id,
        suite_id=request.suite_id,
        triggered_by=request.triggered_by,
        git_sha=request.git_sha,
        git_branch=request.git_branch,
        pr_number=request.pr_number,
        agent_version=request.agent_version,
        model_version=request.model_version,
        suite_version=suite_version,
        status=EvalRunStatus.PENDING,
        trial_k=request.trial_k,
        parallel=request.parallel,
        task_ids=request.task_ids,
    )

    db.add(run)
    await db.commit()
    await db.refresh(run)

    # 백그라운드에서 실행 시작
    from backend.api.deps import get_settings

    settings = get_settings()
    background_tasks.add_task(_execute_run, run_id, settings.database_url)

    logger.info(
        "Run created",
        run_id=run_id,
        suite_id=request.suite_id,
        task_ids=request.task_ids,
        triggered_by=request.triggered_by,
    )

    return RunResponse(
        run_id=run.run_id,
        suite_id=run.suite_id,
        status=run.status.value,
        triggered_by=run.triggered_by,
        git_sha=run.git_sha,
        git_branch=run.git_branch,
        pr_number=run.pr_number,
        trial_k=run.trial_k,
        parallel=run.parallel,
        task_ids=run.task_ids,
        created_at=run.created_at,
        started_at=run.started_at,
    )


@router.get("/runs", response_model=list[RunSummaryResponse])
async def list_runs(
    db: Annotated[AsyncSession, Depends(get_db)],
    suite_id: Annotated[str | None, Query(description="Suite ID 필터")] = None,
    status: Annotated[str | None, Query(description="상태 필터")] = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    Run 목록 조회

    Args:
        suite_id: Suite ID 필터
        status: 상태 필터 (pending/running/completed/failed/cancelled)
        limit: 조회 개수
        offset: 오프셋

    Returns:
        Run 목록
    """
    query = select(EvalRun).options(selectinload(EvalRun.suite))

    if suite_id:
        query = query.where(EvalRun.suite_id == suite_id)

    if status:
        try:
            status_enum = EvalRunStatus(status)
            query = query.where(EvalRun.status == status_enum)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid values: {[s.value for s in EvalRunStatus]}",
            ) from e

    query = query.order_by(EvalRun.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    runs = result.scalars().all()

    responses = []
    for run in runs:
        pass_rate = 0.0
        if run.total_tasks > 0:
            pass_rate = run.passed_tasks / run.total_tasks

        responses.append(
            RunSummaryResponse(
                run_id=run.run_id,
                suite_id=run.suite_id,
                suite_name=run.suite.name if run.suite else None,
                status=run.status.value,
                triggered_by=run.triggered_by,
                git_sha=run.git_sha,
                total_tasks=run.total_tasks,
                passed_tasks=run.passed_tasks,
                failed_tasks=run.failed_tasks,
                pass_rate=pass_rate,
                total_cost_usd=run.total_cost_usd,
                total_duration_seconds=run.total_duration_seconds,
                gate_passed=run.gate_passed,
                gate_decision=run.gate_decision.value if run.gate_decision else None,
                created_at=run.created_at,
                started_at=run.started_at,
                completed_at=run.completed_at,
            )
        )

    return responses


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Run 상세 조회 (Task별 결과 포함)

    Args:
        run_id: Run ID

    Returns:
        Run 상세 정보
    """
    query = (
        select(EvalRun)
        .options(selectinload(EvalRun.suite), selectinload(EvalRun.trials))
        .where(EvalRun.run_id == run_id)
    )
    result = await db.execute(query)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # Trial에서 사용된 모든 task_id 추출
    task_ids_in_trials = {trial.task_id for trial in run.trials}

    # 모든 Task 정보를 한 번에 조회 (N+1 문제 해결)
    task_map: dict[str, EvalTask] = {}
    if task_ids_in_trials:
        task_query = select(EvalTask).where(EvalTask.task_id.in_(task_ids_in_trials))
        task_result = await db.execute(task_query)
        tasks = task_result.scalars().all()
        task_map = {task.task_id: task for task in tasks}

    # Task별 결과 집계
    task_results_map: dict[str, TaskResultSummary] = {}
    for trial in run.trials:
        if trial.task_id not in task_results_map:
            task = task_map.get(trial.task_id)
            task_results_map[trial.task_id] = TaskResultSummary(
                task_id=trial.task_id,
                task_description=task.description if task else None,
                total_trials=0,
                passed_trials=0,
                pass_rate=0.0,
                avg_score=None,
                avg_duration_seconds=0.0,
                total_cost_usd=0.0,
            )

        summary = task_results_map[trial.task_id]
        summary.total_trials += 1
        if trial.passed:
            summary.passed_trials += 1
        summary.total_cost_usd += trial.cost_usd
        summary.avg_duration_seconds = (
            summary.avg_duration_seconds * (summary.total_trials - 1) + trial.duration_seconds
        ) / summary.total_trials

    # Pass rate 계산
    for summary in task_results_map.values():
        if summary.total_trials > 0:
            summary.pass_rate = summary.passed_trials / summary.total_trials

    pass_rate = 0.0
    if run.total_tasks > 0:
        pass_rate = run.passed_tasks / run.total_tasks

    return RunDetailResponse(
        run_id=run.run_id,
        suite_id=run.suite_id,
        suite_name=run.suite.name if run.suite else None,
        status=run.status.value,
        triggered_by=run.triggered_by,
        git_sha=run.git_sha,
        git_branch=run.git_branch,
        pr_number=run.pr_number,
        agent_version=run.agent_version,
        model_version=run.model_version,
        suite_version=run.suite_version,
        trial_k=run.trial_k,
        parallel=run.parallel,
        task_ids=run.task_ids,
        total_tasks=run.total_tasks,
        passed_tasks=run.passed_tasks,
        failed_tasks=run.failed_tasks,
        pass_rate=pass_rate,
        total_cost_usd=run.total_cost_usd,
        total_duration_seconds=run.total_duration_seconds,
        gate_passed=run.gate_passed,
        gate_decision=run.gate_decision.value if run.gate_decision else None,
        gate_reason=run.gate_reason,
        task_results=list(task_results_map.values()),
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.delete("/runs/{run_id}", response_model=CancelResponse)
async def cancel_run(
    run_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    진행 중인 Run 취소

    Args:
        run_id: Run ID

    Returns:
        취소 결과
    """
    query = select(EvalRun).where(EvalRun.run_id == run_id)
    result = await db.execute(query)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    if run.status not in (EvalRunStatus.PENDING, EvalRunStatus.RUNNING):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel run in status: {run.status.value}. Only PENDING or RUNNING runs can be cancelled.",
        )

    # 상태 업데이트
    run.status = EvalRunStatus.CANCELLED
    run.completed_at = datetime.now(UTC)
    await db.commit()

    logger.info("Run cancelled", run_id=run_id)

    return CancelResponse(
        run_id=run_id,
        status=run.status.value,
        message="Run cancelled successfully",
        cancelled_at=run.completed_at,
    )


# ============================================================
# Trial 조회 엔드포인트
# ============================================================


@router.get("/runs/{run_id}/trials", response_model=list[TrialSummaryResponse])
async def list_trials(
    run_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    task_id: Annotated[str | None, Query(description="Task ID 필터")] = None,
    passed: Annotated[bool | None, Query(description="통과 여부 필터")] = None,
):
    """
    Run의 Trial 목록 조회

    Args:
        run_id: Run ID
        task_id: Task ID 필터
        passed: 통과 여부 필터

    Returns:
        Trial 목록
    """
    # Run 존재 확인
    run_query = select(EvalRun).where(EvalRun.run_id == run_id)
    run_result = await db.execute(run_query)
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    query = select(EvalTrial).where(EvalTrial.run_id == run_id)

    if task_id:
        query = query.where(EvalTrial.task_id == task_id)

    if passed is not None:
        query = query.where(EvalTrial.passed == passed)

    query = query.order_by(EvalTrial.task_id, EvalTrial.trial_index)
    result = await db.execute(query)
    trials = result.scalars().all()

    return [
        TrialSummaryResponse(
            trial_id=trial.trial_id,
            run_id=trial.run_id,
            task_id=trial.task_id,
            trial_index=trial.trial_index,
            status=trial.status.value,
            passed=trial.passed,
            score=trial.score,
            duration_seconds=trial.duration_seconds,
            cost_usd=trial.cost_usd,
            error_type=trial.error_type,
            created_at=trial.created_at,
            started_at=trial.started_at,
            completed_at=trial.completed_at,
        )
        for trial in trials
    ]


@router.get("/trials/{trial_id}", response_model=TrialDetailResponse)
async def get_trial(
    trial_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Trial 상세 조회 (채점 결과 포함)

    Args:
        trial_id: Trial ID

    Returns:
        Trial 상세 정보
    """
    query = (
        select(EvalTrial)
        .options(
            selectinload(EvalTrial.task),
            selectinload(EvalTrial.grader_result_details),
        )
        .where(EvalTrial.trial_id == trial_id)
    )
    result = await db.execute(query)
    trial = result.scalar_one_or_none()

    if not trial:
        raise HTTPException(status_code=404, detail=f"Trial not found: {trial_id}")

    grader_results = [
        GraderResultResponse(
            grader_id=gr.grader_id,
            grader_type=gr.grader_type,
            score=gr.score,
            passed=gr.passed,
            partial_scores=gr.partial_scores,
            explanation=gr.explanation,
            judge_model=gr.judge_model,
            confidence=gr.confidence,
            duration_seconds=gr.duration_seconds,
            graded_at=gr.graded_at,
        )
        for gr in trial.grader_result_details
    ]

    return TrialDetailResponse(
        trial_id=trial.trial_id,
        run_id=trial.run_id,
        task_id=trial.task_id,
        task_description=trial.task.description if trial.task else None,
        trial_index=trial.trial_index,
        seed=trial.seed,
        env_snapshot_id=trial.env_snapshot_id,
        status=trial.status.value,
        passed=trial.passed,
        score=trial.score,
        duration_seconds=trial.duration_seconds,
        cost_usd=trial.cost_usd,
        total_tokens=trial.total_tokens,
        input_tokens=trial.input_tokens,
        output_tokens=trial.output_tokens,
        error_message=trial.error_message,
        error_type=trial.error_type,
        grader_results=grader_results,
        created_at=trial.created_at,
        started_at=trial.started_at,
        completed_at=trial.completed_at,
    )


@router.get("/trials/{trial_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    trial_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Trial 트랜스크립트 조회

    Args:
        trial_id: Trial ID

    Returns:
        트랜스크립트 (대화 기록, 도구 호출 등)
    """
    # Trial 존재 확인
    trial_query = select(EvalTrial).where(EvalTrial.trial_id == trial_id)
    trial_result = await db.execute(trial_query)
    trial = trial_result.scalar_one_or_none()
    if not trial:
        raise HTTPException(status_code=404, detail=f"Trial not found: {trial_id}")

    # Transcript 조회
    query = select(EvalTranscript).where(EvalTranscript.trial_id == trial_id)
    result = await db.execute(query)
    transcript = result.scalar_one_or_none()

    if not transcript:
        raise HTTPException(status_code=404, detail=f"Transcript not found for trial: {trial_id}")

    return TranscriptResponse(
        trial_id=transcript.trial_id,
        messages=transcript.messages or [],
        tool_calls=transcript.tool_calls or [],
        intermediate_states=transcript.intermediate_states or [],
        n_turns=transcript.n_turns,
        n_tool_calls=transcript.n_tool_calls,
        n_errors=transcript.n_errors,
        n_retries=transcript.n_retries,
        raw_transcript=transcript.raw_transcript,
    )


@router.get("/trials/{trial_id}/outcome", response_model=OutcomeResponse)
async def get_outcome(
    trial_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Trial 최종 상태 조회

    Args:
        trial_id: Trial ID

    Returns:
        최종 상태 (파일, DB 변경, API 응답 등)
    """
    # Trial 존재 확인
    trial_query = select(EvalTrial).where(EvalTrial.trial_id == trial_id)
    trial_result = await db.execute(trial_query)
    trial = trial_result.scalar_one_or_none()
    if not trial:
        raise HTTPException(status_code=404, detail=f"Trial not found: {trial_id}")

    # Outcome 조회
    query = select(EvalOutcome).where(EvalOutcome.trial_id == trial_id)
    result = await db.execute(query)
    outcome = result.scalar_one_or_none()

    if not outcome:
        raise HTTPException(status_code=404, detail=f"Outcome not found for trial: {trial_id}")

    return OutcomeResponse(
        trial_id=outcome.trial_id,
        final_state=outcome.final_state or {},
        artifacts=outcome.artifacts or [],
        db_changes=outcome.db_changes or [],
        file_hashes=outcome.file_hashes or {},
        api_responses=outcome.api_responses or [],
    )


# ============================================================
# 통계 및 분석 엔드포인트
# ============================================================


@router.get("/stats/summary", response_model=StatsSummaryResponse)
async def get_stats_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    suite_id: Annotated[str | None, Query(description="Suite ID 필터")] = None,
    days: Annotated[int, Query(ge=1, le=90, description="조회 기간 (일)")] = 7,
):
    """
    평가 통계 요약

    Args:
        suite_id: Suite ID 필터
        days: 조회 기간 (일)

    Returns:
        통계 요약 (pass rate 추이, 비용, 시간)
    """
    period_end = datetime.now(UTC)
    period_start = period_end - timedelta(days=days)

    # Run 조회 쿼리
    run_query = select(EvalRun).where(EvalRun.created_at >= period_start)
    if suite_id:
        run_query = run_query.where(EvalRun.suite_id == suite_id)

    run_result = await db.execute(run_query)
    runs = run_result.scalars().all()

    # Trial 조회 쿼리
    run_ids = [r.run_id for r in runs]
    trials_list = []
    if run_ids:
        trial_query = select(EvalTrial).where(EvalTrial.run_id.in_(run_ids))
        trial_result = await db.execute(trial_query)
        trials_list = list(trial_result.scalars().all())
    trials = trials_list

    # 전체 통계 계산
    total_runs = len(runs)
    total_trials = len(trials)
    passed_trials = sum(1 for t in trials if t.passed is True)
    failed_trials = sum(1 for t in trials if t.passed is False)
    total_cost_usd = sum(r.total_cost_usd for r in runs)
    total_duration = sum(t.duration_seconds for t in trials)

    overall_pass_rate = passed_trials / total_trials if total_trials > 0 else 0.0
    avg_cost_per_run = total_cost_usd / total_runs if total_runs > 0 else 0.0
    avg_duration_per_trial = total_duration / total_trials if total_trials > 0 else 0.0

    # 일별 통계 계산
    daily_stats_map: dict[str, DailyStats] = {}
    for trial in trials:
        if trial.created_at:
            date_str = trial.created_at.strftime("%Y-%m-%d")
            if date_str not in daily_stats_map:
                daily_stats_map[date_str] = DailyStats(
                    date=date_str,
                    total_runs=0,
                    total_trials=0,
                    passed_trials=0,
                    pass_rate=0.0,
                    total_cost_usd=0.0,
                    avg_duration_seconds=0.0,
                )
            daily = daily_stats_map[date_str]
            daily.total_trials += 1
            if trial.passed:
                daily.passed_trials += 1
            daily.total_cost_usd += trial.cost_usd
            daily.avg_duration_seconds = (
                daily.avg_duration_seconds * (daily.total_trials - 1) + trial.duration_seconds
            ) / daily.total_trials

    # Run 수 추가 및 pass rate 계산
    for run in runs:
        if run.created_at:
            date_str = run.created_at.strftime("%Y-%m-%d")
            if date_str in daily_stats_map:
                daily_stats_map[date_str].total_runs += 1

    for daily in daily_stats_map.values():
        if daily.total_trials > 0:
            daily.pass_rate = daily.passed_trials / daily.total_trials

    daily_stats = sorted(daily_stats_map.values(), key=lambda x: x.date)

    return StatsSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        suite_id=suite_id,
        total_runs=total_runs,
        total_trials=total_trials,
        passed_trials=passed_trials,
        failed_trials=failed_trials,
        overall_pass_rate=overall_pass_rate,
        total_cost_usd=total_cost_usd,
        avg_cost_per_run=avg_cost_per_run,
        avg_duration_per_trial=avg_duration_per_trial,
        daily_stats=daily_stats,
    )


@router.get("/stats/regression", response_model=RegressionReport)
async def detect_regressions(
    suite_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    compare_runs: Annotated[int, Query(ge=2, le=20, description="비교할 Run 수")] = 5,
):
    """
    회귀 탐지 리포트

    최근 Run들을 비교하여 pass rate가 하락한 Task를 탐지합니다.

    Args:
        suite_id: Suite ID
        compare_runs: 비교할 Run 수

    Returns:
        회귀 탐지 리포트
    """
    # Suite 존재 확인
    suite_query = select(EvalSuite).where(EvalSuite.suite_id == suite_id)
    suite_result = await db.execute(suite_query)
    suite = suite_result.scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail=f"Suite not found: {suite_id}")

    # 최근 완료된 Run 조회
    run_query = (
        select(EvalRun)
        .where(EvalRun.suite_id == suite_id)
        .where(EvalRun.status == EvalRunStatus.COMPLETED)
        .order_by(EvalRun.completed_at.desc())
        .limit(compare_runs)
    )
    run_result = await db.execute(run_query)
    runs = run_result.scalars().all()

    if len(runs) < 2:
        return RegressionReport(
            suite_id=suite_id,
            compared_runs=len(runs),
            baseline_run_id=None,
            current_run_id=None,
            regressions=[],
            improvements=[],
            total_regressions=0,
            total_improvements=0,
            overall_delta=0.0,
            generated_at=datetime.now(UTC),
        )

    current_run = runs[0]
    baseline_run = runs[-1]

    # Task별 pass rate 계산
    async def get_task_pass_rates(run_id: str) -> dict[str, tuple[float, str | None]]:
        query = (
            select(EvalTrial)
            .options(selectinload(EvalTrial.task))
            .where(EvalTrial.run_id == run_id)
        )
        result = await db.execute(query)
        trials = result.scalars().all()

        task_trials: dict[str, list[bool]] = {}
        task_descriptions: dict[str, str | None] = {}
        for trial in trials:
            if trial.task_id not in task_trials:
                task_trials[trial.task_id] = []
                task_descriptions[trial.task_id] = trial.task.description if trial.task else None
            if trial.passed is not None:
                task_trials[trial.task_id].append(trial.passed)

        rates: dict[str, tuple[float, str | None]] = {}
        for task_id, passed_list in task_trials.items():
            if passed_list:
                rate = sum(passed_list) / len(passed_list)
                rates[task_id] = (rate, task_descriptions[task_id])
        return rates

    baseline_rates = await get_task_pass_rates(baseline_run.run_id)
    current_rates = await get_task_pass_rates(current_run.run_id)

    regressions: list[RegressionItem] = []
    improvements: list[RegressionItem] = []

    all_tasks = set(baseline_rates.keys()) | set(current_rates.keys())
    for task_id in all_tasks:
        baseline_rate = baseline_rates.get(task_id, (0.0, None))[0]
        current_rate = current_rates.get(task_id, (0.0, None))[0]
        task_desc = (
            current_rates.get(task_id, (0.0, None))[1]
            or baseline_rates.get(task_id, (0.0, None))[1]
        )
        delta = current_rate - baseline_rate

        if abs(delta) < 0.01:  # 1% 미만 변화는 무시
            continue

        # Severity 결정
        severity = "low"
        if abs(delta) >= 0.3:
            severity = "high"
        elif abs(delta) >= 0.15:
            severity = "medium"

        item = RegressionItem(
            task_id=task_id,
            task_description=task_desc,
            previous_pass_rate=baseline_rate,
            current_pass_rate=current_rate,
            delta=delta,
            severity=severity,
        )

        if delta < 0:
            regressions.append(item)
        else:
            improvements.append(item)

    # 전체 pass rate 변화
    baseline_overall = (
        sum(r[0] for r in baseline_rates.values()) / len(baseline_rates) if baseline_rates else 0.0
    )
    current_overall = (
        sum(r[0] for r in current_rates.values()) / len(current_rates) if current_rates else 0.0
    )
    overall_delta = current_overall - baseline_overall

    return RegressionReport(
        suite_id=suite_id,
        compared_runs=len(runs),
        baseline_run_id=baseline_run.run_id,
        current_run_id=current_run.run_id,
        regressions=sorted(regressions, key=lambda x: x.delta),
        improvements=sorted(improvements, key=lambda x: -x.delta),
        total_regressions=len(regressions),
        total_improvements=len(improvements),
        overall_delta=overall_delta,
        generated_at=datetime.now(UTC),
    )
