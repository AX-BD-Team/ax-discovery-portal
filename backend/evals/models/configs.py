"""
Evals 설정 모델

Task/Suite YAML에서 사용되는 설정 객체들
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.evals.models.enums import (
    AgentAdapter,
    Difficulty,
    Domain,
    GraderType,
    MetricType,
    NetworkAccess,
    ResetMode,
    Risk,
    SandboxType,
    ScoringMode,
    StaticAnalysisTool,
    SuitePurpose,
    TestFramework,
)

# ============================================================================
# Task 메타데이터
# ============================================================================


class TaskMetadata(BaseModel):
    """Task 메타데이터"""

    domain: Domain | None = Field(None, description="도메인 분류")
    difficulty: Difficulty = Field(Difficulty.MEDIUM, description="난이도")
    risk: Risk = Field(Risk.LOW, description="위험도")
    purpose: SuitePurpose | None = Field(None, description="평가 목적")
    expected_pass_rate: float | None = Field(None, ge=0, le=1, description="기대 통과율")
    owner: str | None = Field(None, description="담당자/팀")
    created_at: str | None = Field(None, description="생성 일자 (YYYY-MM-DD)")
    updated_at: str | None = Field(None, description="수정 일자")


# ============================================================================
# Task 입력
# ============================================================================


class FileInput(BaseModel):
    """파일 입력"""

    path: str = Field(..., description="파일 경로")
    content: str | None = Field(None, description="파일 내용 (인라인)")
    content_file: str | None = Field(None, description="내용을 읽어올 파일 경로")


class TaskInputs(BaseModel):
    """Task 입력 설정"""

    prompt: str | None = Field(None, description="에이전트에게 전달할 프롬프트")
    prompt_file: str | None = Field(None, description="프롬프트 파일 경로")
    context: dict[str, Any] = Field(default_factory=dict, description="추가 컨텍스트")
    files: list[FileInput] = Field(default_factory=list, description="초기 파일 목록")
    environment_variables: dict[str, str] = Field(default_factory=dict, description="환경 변수")


# ============================================================================
# 성공 기준
# ============================================================================


class OutcomeCheck(BaseModel):
    """결과 검증 체크"""

    type: Literal[
        "file_exists",
        "file_contains",
        "file_not_contains",
        "command_succeeds",
        "command_output_contains",
        "db_row_exists",
        "api_returns",
        "state_equals",
    ] = Field(..., description="체크 유형")
    target: str = Field(..., description="검사 대상")
    value: Any | None = Field(None, description="기대값")
    description: str | None = Field(None, description="설명")


class SuccessCriteria(BaseModel):
    """성공 기준"""

    description: str | None = Field(None, description="성공 기준 설명")
    outcome_checks: list[OutcomeCheck] = Field(
        default_factory=list, description="결과 검증 체크 목록"
    )
    negative_checks: list[OutcomeCheck] = Field(
        default_factory=list, description="일어나면 안 되는 것들"
    )


# ============================================================================
# 레퍼런스 솔루션
# ============================================================================


class ReferenceSolution(BaseModel):
    """레퍼런스 솔루션 (채점기 검증용)"""

    description: str | None = Field(None, description="솔루션 설명")
    files: list[FileInput] = Field(default_factory=list, description="정답 파일 목록")
    expected_outcome: dict[str, Any] = Field(default_factory=dict, description="기대 결과 상태")


# ============================================================================
# 트라이얼 설정
# ============================================================================


class TrialConfig(BaseModel):
    """트라이얼 설정"""

    k: int = Field(5, ge=1, le=100, description="트라이얼 횟수")
    seeds: list[int] | None = Field(None, description="고정 시드 목록")
    parallel: bool = Field(True, description="병렬 실행 여부")
    stop_on_first_pass: bool = Field(False, description="첫 성공 시 중단")


# ============================================================================
# 환경 설정
# ============================================================================


class MountConfig(BaseModel):
    """마운트 볼륨 설정"""

    source: str = Field(..., description="소스 경로")
    target: str = Field(..., description="대상 경로")
    readonly: bool = Field(True, description="읽기 전용")


class EnvironmentConfig(BaseModel):
    """실행 환경 설정"""

    sandbox: SandboxType = Field(SandboxType.CONTAINER, description="격리 수준")
    image: str | None = Field(None, description="컨테이너 이미지")
    reset: ResetMode = Field(ResetMode.CLEAN, description="환경 리셋 방식")
    network: NetworkAccess = Field(NetworkAccess.INTERNAL, description="네트워크 접근")
    working_dir: str | None = Field(None, description="작업 디렉토리")
    mounts: list[MountConfig] = Field(default_factory=list, description="마운트 볼륨")


# ============================================================================
# 에이전트 설정
# ============================================================================


class AgentConfig(BaseModel):
    """에이전트 설정"""

    adapter: AgentAdapter = Field(AgentAdapter.AX_AGENT_SDK, description="어댑터 유형")
    agent_id: str | None = Field(None, description="특정 에이전트 ID")
    model: str | None = Field(None, description="사용할 모델")
    tools_allowed: list[str] = Field(default_factory=list, description="허용 도구")
    tools_denied: list[str] = Field(default_factory=list, description="금지 도구")
    max_turns: int = Field(20, ge=1, le=100, description="최대 턴 수")
    max_tool_calls: int = Field(50, ge=1, le=500, description="최대 도구 호출 수")
    system_prompt_override: str | None = Field(None, description="시스템 프롬프트 오버라이드")


# ============================================================================
# 채점기 설정
# ============================================================================


class DeterministicTestsConfig(BaseModel):
    """테스트 실행 채점기 설정"""

    framework: TestFramework = Field(TestFramework.PYTEST, description="테스트 프레임워크")
    test_files: list[str] = Field(default_factory=list, description="테스트 파일 목록")
    test_pattern: str | None = Field(None, description="테스트 파일 glob 패턴")
    test_command: str | None = Field(None, description="커스텀 테스트 명령어")
    working_dir: str | None = Field(None, description="작업 디렉토리")
    timeout_seconds: int = Field(120, description="테스트 타임아웃")
    coverage_threshold: float | None = Field(None, ge=0, le=100, description="커버리지 임계값")
    fail_fast: bool = Field(False, description="첫 실패 시 중단")


class StaticAnalysisToolConfig(BaseModel):
    """정적 분석 도구 개별 설정"""

    name: StaticAnalysisTool = Field(..., description="분석 도구")
    command: str | None = Field(None, description="커스텀 명령어")
    config_file: str | None = Field(None, description="설정 파일 경로")
    severity_threshold: Literal["error", "warning", "info"] = Field(
        "error", description="허용 심각도"
    )


class StaticAnalysisConfig(BaseModel):
    """정적 분석 채점기 설정"""

    tools: list[StaticAnalysisToolConfig] = Field(
        default_factory=list, description="분석 도구 목록"
    )
    commands: list[str] = Field(default_factory=list, description="직접 실행할 명령어 (deprecated)")
    allow_warnings: bool = Field(False, description="경고 허용")
    max_errors: int = Field(0, description="허용 에러 개수")
    target_paths: list[str] = Field(default_factory=list, description="분석 대상 경로")


class StringCheck(BaseModel):
    """문자열 체크"""

    target: Literal["output", "file", "transcript", "tool_result"] = Field(
        "output", description="검사 대상"
    )
    path: str | None = Field(None, description="파일 경로")
    expected: str = Field(..., description="기대 문자열")
    mode: Literal["exact", "contains", "starts_with", "ends_with"] = Field(
        "contains", description="매칭 모드"
    )
    case_sensitive: bool = Field(True, description="대소문자 구분")
    negate: bool = Field(False, description="NOT 조건")


class StringMatchConfig(BaseModel):
    """문자열 매칭 채점기 설정"""

    checks: list[StringCheck] = Field(..., description="체크 목록")
    all_required: bool = Field(True, description="모든 체크 통과 필요")


class RegexPattern(BaseModel):
    """정규식 패턴"""

    pattern: str = Field(..., description="정규식 패턴")
    target: Literal["output", "file", "transcript"] = Field("output")
    path: str | None = None
    flags: str | None = Field(None, description="정규식 플래그")
    negate: bool = Field(False)
    extract_groups: bool = Field(False, description="그룹 추출 여부")


class RegexMatchConfig(BaseModel):
    """정규식 매칭 채점기 설정"""

    patterns: list[RegexPattern] = Field(..., description="패턴 목록")
    all_required: bool = Field(True)


class ToolCallRequirement(BaseModel):
    """필수 도구 호출"""

    tool: str = Field(..., description="도구 이름")
    min_count: int = Field(1, description="최소 호출 횟수")
    max_count: int | None = Field(None, description="최대 호출 횟수")
    args_match: dict[str, Any] | None = Field(None, description="인자 매칭 조건")


class ForbiddenToolCall(BaseModel):
    """금지 도구 호출"""

    tool: str = Field(..., description="도구 이름")
    reason: str | None = Field(None, description="금지 사유")


class ToolCallCheckConfig(BaseModel):
    """도구 호출 검증 채점기 설정"""

    required_calls: list[ToolCallRequirement] = Field(
        default_factory=list, description="필수 호출 도구"
    )
    forbidden_calls: list[ForbiddenToolCall] = Field(default_factory=list, description="금지 도구")
    call_order: list[str] = Field(default_factory=list, description="호출 순서")
    check_order: bool = Field(False, description="순서 검사 (false 권장)")


class StateCheckItem(BaseModel):
    """상태 체크 항목"""

    type: Literal[
        "file_exists",
        "file_not_exists",
        "file_content",
        "dir_exists",
        "db_row_exists",
        "db_row_value",
        "api_response",
        "env_var",
        "process_running",
        "port_listening",
    ] = Field(..., description="체크 유형")
    target: str = Field(..., description="대상")
    expected: Any | None = Field(None, description="기대값")
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte", "contains", "matches"] = Field(
        "eq", description="연산자"
    )
    description: str | None = None


class StateCheckConfig(BaseModel):
    """상태 검증 채점기 설정"""

    checks: list[StateCheckItem] = Field(..., description="체크 목록")


class TranscriptMetricsConfig(BaseModel):
    """트랜스크립트 메트릭 채점기 설정"""

    thresholds: dict[str, int | float] = Field(
        default_factory=dict, description="임계값 (max_turns, max_tool_calls, ...)"
    )
    efficiency_score: bool = Field(False, description="효율성 점수 계산")


class LatencyCheckConfig(BaseModel):
    """지연시간 채점기 설정"""

    thresholds: dict[str, float] = Field(
        default_factory=dict, description="임계값 (max_total_seconds, ...)"
    )
    percentile: float = Field(95, ge=0, le=100, description="백분위수 기준")


class RubricDimension(BaseModel):
    """루브릭 차원"""

    name: str = Field(..., description="차원 이름")
    description: str = Field(..., description="평가 기준 설명")
    weight: float = Field(..., ge=0, le=1, description="가중치")
    scale_min: int = Field(1, description="최소 점수")
    scale_max: int = Field(5, description="최대 점수")
    examples: list[dict[str, Any]] = Field(default_factory=list, description="점수별 예시")


class LLMRubricConfig(BaseModel):
    """LLM 루브릭 채점기 설정"""

    model: str = Field("claude-sonnet-4-20250514", description="Judge 모델")
    rubric_path: str | None = Field(None, description="루브릭 파일 경로")
    rubric_inline: str | None = Field(None, description="인라인 루브릭")
    dimensions: list[RubricDimension] = Field(default_factory=list, description="평가 차원")
    allow_unknown: bool = Field(True, description="Unknown 응답 허용")
    explanation_required: bool = Field(True, description="설명 필수")
    temperature: float = Field(0, ge=0, le=1, description="모델 temperature")


class LLMAssertion(BaseModel):
    """LLM Assertion"""

    statement: str = Field(..., description="자연어 assertion")
    weight: float = Field(1.0, ge=0)
    required: bool = Field(False)


class LLMAssertionConfig(BaseModel):
    """LLM Assertion 채점기 설정"""

    model: str = Field("claude-sonnet-4-20250514")
    assertions: list[LLMAssertion] = Field(..., description="assertion 목록")
    context_fields: list[str] = Field(
        default_factory=lambda: ["output", "transcript"],
        description="평가에 포함할 컨텍스트",
    )


class LLMPairwiseConfig(BaseModel):
    """LLM Pairwise 채점기 설정"""

    model: str = Field("claude-sonnet-4-20250514")
    baseline: dict[str, Any] = Field(..., description="비교 기준")
    criteria: list[str] = Field(default_factory=list, description="비교 기준 목록")
    tie_allowed: bool = Field(True, description="동점 허용")


class LLMReferenceConfig(BaseModel):
    """LLM Reference 채점기 설정"""

    model: str = Field("claude-sonnet-4-20250514")
    reference: dict[str, str] = Field(..., description="레퍼런스 솔루션")
    comparison_mode: Literal["semantic", "structural", "functional"] = Field(
        "semantic", description="비교 모드"
    )
    tolerance: float = Field(0.8, ge=0, le=1, description="허용 유사도")


class HumanReviewConfig(BaseModel):
    """인간 리뷰 채점기 설정"""

    reviewer_pool: list[str] = Field(default_factory=list, description="리뷰어 풀")
    min_reviewers: int = Field(1, ge=1, description="최소 리뷰어 수")
    consensus_threshold: float = Field(0.8, ge=0, le=1, description="합의 임계값")
    rubric_path: str | None = Field(None, description="리뷰 루브릭 경로")
    timeout_hours: int = Field(48, description="리뷰 타임아웃")
    escalation: dict[str, Any] | None = Field(None, description="에스컬레이션 설정")
    spot_check: dict[str, Any] | None = Field(None, description="스팟체크 설정")


class GraderConfig(BaseModel):
    """채점기 설정 (공통)"""

    type: GraderType = Field(..., description="채점기 유형")
    id: str | None = Field(None, description="채점기 고유 ID")
    weight: float = Field(1.0, ge=0, le=1, description="가중치")
    required: bool = Field(False, description="필수 통과 여부")
    enabled: bool = Field(True, description="활성화 여부")
    description: str | None = Field(None, description="설명")

    # 채점기별 설정 (type에 따라 하나만 사용)
    config: dict[str, Any] = Field(default_factory=dict, description="채점기별 설정")


# ============================================================================
# 메트릭 설정
# ============================================================================


class MetricConfig(BaseModel):
    """메트릭 추적 설정"""

    type: MetricType = Field(..., description="메트릭 유형")
    metrics: list[str] = Field(..., description="추적할 메트릭 이름")


# ============================================================================
# 채점 설정
# ============================================================================


class PartialCreditRule(BaseModel):
    """부분 점수 규칙"""

    condition: str = Field(..., description="조건")
    credit: float = Field(..., ge=0, le=1, description="점수")
    description: str | None = Field(None, description="설명")


class ScoringConfig(BaseModel):
    """채점 설정"""

    mode: ScoringMode = Field(ScoringMode.WEIGHTED, description="채점 모드")
    pass_threshold: float = Field(0.8, ge=0, le=1, description="통과 임계값")
    required_graders: list[str] = Field(default_factory=list, description="필수 통과 채점기 ID")
    partial_credit_rules: list[PartialCreditRule] = Field(
        default_factory=list, description="부분 점수 규칙"
    )


# ============================================================================
# 타임아웃 & 비용 설정
# ============================================================================


class TimeoutConfig(BaseModel):
    """타임아웃 설정"""

    total_seconds: int = Field(300, ge=1, le=3600, description="전체 타임아웃")
    per_turn_seconds: int = Field(60, ge=1, le=300, description="턴당 타임아웃")
    grading_seconds: int = Field(120, ge=1, le=600, description="채점 타임아웃")


class CostBudget(BaseModel):
    """비용 예산"""

    max_tokens: int | None = Field(None, description="최대 토큰 수")
    max_usd: float | None = Field(None, description="최대 비용 (USD)")
    warn_threshold: float = Field(0.8, ge=0, le=1, description="경고 임계값")
