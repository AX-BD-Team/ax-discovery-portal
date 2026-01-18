"""
Evals 핵심 엔터티 모델

평가 플랫폼의 1급 객체들 (DB 저장 대상)
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.evals.models.enums import (
    Decision,
    RunStatus,
    SuitePurpose,
    TaskType,
    TrialStatus,
)


class Suite(BaseModel):
    """
    평가 스위트 (Eval Suite)

    특정 역량/행동을 측정하는 Task 묶음
    """

    suite_id: str = Field(..., description="Suite 고유 ID")
    name: str = Field(..., description="Suite 이름")
    description: str | None = Field(None, description="Suite 설명")
    version: str = Field("1.0.0", description="Suite 버전")
    purpose: SuitePurpose = Field(..., description="목적 (capability/regression)")
    domain: str | None = Field(None, description="도메인 분류")
    owner_team: str | None = Field(None, description="담당 팀")
    tags: list[str] = Field(default_factory=list, description="분류 태그")

    # 메타데이터
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class Task(BaseModel):
    """
    평가 과제 (Eval Task)

    입력 + 성공 기준이 정의된 단일 테스트 케이스
    """

    task_id: str = Field(..., description="Task 고유 ID")
    suite_id: str = Field(..., description="소속 Suite ID")
    type: TaskType = Field(..., description="Task 유형")
    description: str = Field(..., description="Task 설명")
    version: str = Field("1.0.0", description="Task 버전")

    # 메타데이터
    domain: str | None = Field(None, description="도메인")
    difficulty: str = Field("medium", description="난이도")
    risk: str = Field("low", description="위험도")
    purpose: str | None = Field(None, description="평가 목적")
    expected_pass_rate: float | None = Field(None, ge=0, le=1, description="기대 통과율")
    owner: str | None = Field(None, description="담당자")
    tags: list[str] = Field(default_factory=list, description="태그")

    # 설정 (YAML에서 로드)
    inputs: dict[str, Any] = Field(default_factory=dict, description="입력 설정")
    success_criteria: dict[str, Any] = Field(default_factory=dict, description="성공 기준")
    trial_config: dict[str, Any] = Field(default_factory=dict, description="트라이얼 설정")
    environment: dict[str, Any] = Field(default_factory=dict, description="환경 설정")
    agent_config: dict[str, Any] = Field(default_factory=dict, description="에이전트 설정")
    graders: list[dict[str, Any]] = Field(default_factory=list, description="채점기 목록")
    scoring: dict[str, Any] = Field(default_factory=dict, description="채점 설정")

    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class Run(BaseModel):
    """
    평가 실행 (Eval Run)

    하나의 평가 세션 (Suite 또는 개별 Task 실행)
    """

    run_id: str = Field(..., description="Run 고유 ID")
    suite_id: str | None = Field(None, description="실행한 Suite ID")
    task_ids: list[str] = Field(default_factory=list, description="실행한 Task ID 목록")

    # 트리거 정보
    triggered_by: str = Field("manual", description="트리거 (ci/nightly/manual)")
    git_sha: str | None = Field(None, description="Git commit SHA")
    git_branch: str | None = Field(None, description="Git 브랜치")
    pr_number: int | None = Field(None, description="PR 번호")

    # 버전 정보
    agent_version: str | None = Field(None, description="에이전트 버전")
    model_version: str | None = Field(None, description="모델 버전")
    suite_version: str | None = Field(None, description="Suite 버전")

    # 상태
    status: RunStatus = Field(RunStatus.PENDING, description="실행 상태")
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # 실행 설정
    trial_k: int = Field(5, ge=1, description="트라이얼 횟수")
    parallel: bool = Field(True, description="병렬 실행 여부")

    # 결과 요약
    total_tasks: int = Field(0, ge=0)
    passed_tasks: int = Field(0, ge=0)
    failed_tasks: int = Field(0, ge=0)
    total_cost_usd: float = Field(0.0, ge=0)
    total_duration_seconds: float = Field(0.0, ge=0)

    model_config = ConfigDict(from_attributes=True)


class Trial(BaseModel):
    """
    트라이얼 (Trial)

    한 Task에 대한 1회 실행 시도
    비결정성 때문에 복수 트라이얼 수행 가능
    """

    trial_id: str = Field(..., description="Trial 고유 ID")
    run_id: str = Field(..., description="소속 Run ID")
    task_id: str = Field(..., description="실행한 Task ID")
    trial_index: int = Field(..., ge=0, description="트라이얼 인덱스 (0부터)")

    # 실행 정보
    seed: int | None = Field(None, description="랜덤 시드 (재현성)")
    env_snapshot_id: str | None = Field(None, description="환경 스냅샷 ID")

    # 상태
    status: TrialStatus = Field(TrialStatus.PENDING, description="실행 상태")
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # 메트릭
    duration_seconds: float = Field(0.0, ge=0, description="실행 시간 (초)")
    cost_usd: float = Field(0.0, ge=0, description="비용 (USD)")
    total_tokens: int = Field(0, ge=0, description="총 토큰 수")
    input_tokens: int = Field(0, ge=0, description="입력 토큰 수")
    output_tokens: int = Field(0, ge=0, description="출력 토큰 수")

    # 채점 결과
    passed: bool | None = Field(None, description="통과 여부")
    score: float | None = Field(None, ge=0, le=1, description="점수 (0-1)")
    grader_results: list[dict[str, Any]] = Field(default_factory=list, description="채점기별 결과")

    # 에러 정보
    error_message: str | None = Field(None, description="에러 메시지")
    error_type: str | None = Field(None, description="에러 유형")

    model_config = ConfigDict(from_attributes=True)


class Transcript(BaseModel):
    """
    트랜스크립트 (Transcript)

    한 Trial의 전체 실행 기록
    """

    trial_id: str = Field(..., description="소속 Trial ID")

    # 메시지 기록
    messages: list[dict[str, Any]] = Field(default_factory=list, description="대화 메시지 목록")

    # 도구 호출 기록
    tool_calls: list[dict[str, Any]] = Field(default_factory=list, description="도구 호출 목록")

    # 중간 상태
    intermediate_states: list[dict[str, Any]] = Field(
        default_factory=list, description="중간 상태 스냅샷"
    )

    # 트랜스크립트 메트릭
    n_turns: int = Field(0, ge=0, description="대화 턴 수")
    n_tool_calls: int = Field(0, ge=0, description="도구 호출 수")
    n_errors: int = Field(0, ge=0, description="에러 수")
    n_retries: int = Field(0, ge=0, description="재시도 수")

    # 원본 저장
    raw_transcript: str | None = Field(None, description="원본 트랜스크립트 (JSON)")

    model_config = ConfigDict(from_attributes=True)


class Outcome(BaseModel):
    """
    결과 상태 (Outcome)

    Trial 종료 시 환경의 최종 상태
    "말"이 아니라 "상태"로 검증
    """

    trial_id: str = Field(..., description="소속 Trial ID")

    # 최종 상태
    final_state: dict[str, Any] = Field(default_factory=dict, description="최종 환경 상태")

    # 생성된 아티팩트
    artifacts: list[dict[str, Any]] = Field(
        default_factory=list, description="생성된 파일/데이터 목록"
    )

    # DB 변경
    db_changes: list[dict[str, Any]] = Field(default_factory=list, description="DB 변경 내역")

    # 파일 해시 (무결성 검증용)
    file_hashes: dict[str, str] = Field(default_factory=dict, description="파일 경로 → SHA256 해시")

    # API 응답
    api_responses: list[dict[str, Any]] = Field(default_factory=list, description="API 호출 결과")

    model_config = ConfigDict(from_attributes=True)


class GraderResult(BaseModel):
    """
    채점 결과 (Grader Result)

    개별 채점기의 평가 결과
    """

    trial_id: str = Field(..., description="소속 Trial ID")
    grader_id: str = Field(..., description="채점기 ID")
    grader_type: str = Field(..., description="채점기 유형")

    # 점수
    score: float = Field(..., ge=0, le=1, description="점수 (0-1)")
    passed: bool = Field(..., description="통과 여부")

    # 부분 점수 (partial credit)
    partial_scores: dict[str, float] = Field(default_factory=dict, description="항목별 부분 점수")

    # 설명
    explanation: str | None = Field(None, description="채점 설명/근거")

    # LLM Judge 메타데이터
    judge_model: str | None = Field(None, description="Judge 모델 (LLM 채점 시)")
    judge_prompt: str | None = Field(None, description="Judge 프롬프트")
    judge_response: str | None = Field(None, description="Judge 원본 응답")
    confidence: float | None = Field(None, ge=0, le=1, description="신뢰도")

    # 실행 정보
    duration_seconds: float = Field(0.0, ge=0, description="채점 소요 시간")
    error_message: str | None = Field(None, description="에러 메시지")

    # 타임스탬프
    graded_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)


class AggregatedMetrics(BaseModel):
    """
    집계 메트릭 (Aggregated Metrics)

    Run 레벨 집계 통계
    """

    run_id: str = Field(..., description="소속 Run ID")

    # 전체 통계
    total_tasks: int = Field(0, ge=0)
    total_trials: int = Field(0, ge=0)
    passed_tasks: int = Field(0, ge=0)
    failed_tasks: int = Field(0, ge=0)

    # 통과율
    task_pass_rate: float = Field(0.0, ge=0, le=1, description="Task 통과율")
    trial_pass_rate: float = Field(0.0, ge=0, le=1, description="Trial 통과율")

    # pass@k / pass^k
    pass_at_1: float = Field(0.0, ge=0, le=1, description="pass@1")
    pass_at_k: float = Field(0.0, ge=0, le=1, description="pass@k")
    pass_pow_k: float = Field(0.0, ge=0, le=1, description="pass^k (모든 트라이얼 성공)")

    # 점수 통계
    avg_score: float = Field(0.0, ge=0, le=1, description="평균 점수")
    min_score: float = Field(0.0, ge=0, le=1, description="최소 점수")
    max_score: float = Field(0.0, ge=0, le=1, description="최대 점수")
    std_score: float = Field(0.0, ge=0, description="점수 표준편차")

    # 비용/지연 통계
    total_cost_usd: float = Field(0.0, ge=0, description="총 비용")
    avg_cost_per_task: float = Field(0.0, ge=0, description="Task당 평균 비용")
    total_duration_seconds: float = Field(0.0, ge=0, description="총 실행 시간")
    avg_duration_per_trial: float = Field(0.0, ge=0, description="Trial당 평균 시간")

    # 토큰 통계
    total_tokens: int = Field(0, ge=0)
    avg_tokens_per_trial: float = Field(0.0, ge=0)

    # 포화도 지표 (saturation)
    saturation_indicator: float | None = Field(
        None, ge=0, le=1, description="포화도 (1에 가까우면 개선 신호 약함)"
    )
    regression_count: int = Field(0, ge=0, description="회귀 개수")

    # Task별 상세
    task_results: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Task ID → 결과 상세"
    )

    # 타임스탬프
    aggregated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)


class EvalSummary(BaseModel):
    """
    평가 요약 (간략 리포트용)
    """

    run_id: str
    suite_id: str | None
    status: RunStatus
    decision: Decision = Field(Decision.UNKNOWN, description="최종 판정")

    # 핵심 지표
    pass_rate: float = Field(0.0, ge=0, le=1)
    pass_at_k: float = Field(0.0, ge=0, le=1)
    avg_score: float = Field(0.0, ge=0, le=1)
    total_cost_usd: float = Field(0.0, ge=0)

    # 실패 정보
    failed_tasks: list[str] = Field(default_factory=list)
    regressions: list[str] = Field(default_factory=list)

    # 게이트 판정
    gate_passed: bool | None = Field(None, description="CI 게이트 통과 여부")
    gate_reason: str | None = Field(None, description="게이트 판정 사유")

    # 타임스탬프
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
