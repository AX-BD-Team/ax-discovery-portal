"""
Evals 모델 단위 테스트

backend/evals/models/ 모듈 테스트
"""

from datetime import UTC, datetime

from backend.evals.models.configs import (
    CostBudget,
    EnvironmentConfig,
    GraderConfig,
    ScoringConfig,
    TaskInputs,
    TaskMetadata,
    TimeoutConfig,
    TrialConfig,
)
from backend.evals.models.entities import (
    GraderResult,
    Outcome,
    Suite,
    Task,
    Transcript,
    Trial,
)
from backend.evals.models.enums import (
    Decision,
    Difficulty,
    Domain,
    GraderType,
    NetworkAccess,
    ResetMode,
    Risk,
    SandboxType,
    ScoringMode,
    SuitePurpose,
    TaskType,
    TrialStatus,
)

# ============================================================================
# Enum 테스트
# ============================================================================


class TestEnums:
    """열거형 테스트"""

    def test_task_type_values(self):
        """TaskType 값 검증"""
        assert TaskType.CODING.value == "coding"
        assert TaskType.WORKFLOW.value == "workflow"
        assert TaskType.CONVERSATIONAL.value == "conversational"
        assert TaskType.RESEARCH.value == "research"
        assert TaskType.COMPUTER_USE.value == "computer_use"

    def test_trial_status_values(self):
        """TrialStatus 값 검증"""
        assert TrialStatus.PENDING.value == "pending"
        assert TrialStatus.RUNNING.value == "running"
        assert TrialStatus.COMPLETED.value == "completed"
        assert TrialStatus.FAILED.value == "failed"
        assert TrialStatus.TIMEOUT.value == "timeout"
        assert TrialStatus.CANCELLED.value == "cancelled"

    def test_grader_type_values(self):
        """GraderType 값 검증"""
        assert GraderType.DETERMINISTIC_TESTS.value == "deterministic_tests"
        assert GraderType.LLM_RUBRIC.value == "llm_rubric"
        assert GraderType.STATE_CHECK.value == "state_check"
        assert GraderType.TRANSCRIPT_METRICS.value == "transcript_metrics"

    def test_scoring_mode_values(self):
        """ScoringMode 값 검증"""
        assert ScoringMode.WEIGHTED.value == "weighted"
        assert ScoringMode.BINARY.value == "binary"
        assert ScoringMode.HYBRID.value == "hybrid"
        assert ScoringMode.PARTIAL_CREDIT.value == "partial_credit"

    def test_decision_values(self):
        """Decision 값 검증"""
        assert Decision.PASS.value == "pass"
        assert Decision.FAIL.value == "fail"
        assert Decision.MARGINAL.value == "marginal"
        assert Decision.UNKNOWN.value == "unknown"


# ============================================================================
# Entity 테스트
# ============================================================================


class TestSuiteEntity:
    """Suite 엔터티 테스트"""

    def test_create_suite(self):
        """Suite 생성 테스트"""
        suite = Suite(
            suite_id="test-suite",
            name="테스트 스위트",
            purpose=SuitePurpose.REGRESSION,
        )

        assert suite.suite_id == "test-suite"
        assert suite.name == "테스트 스위트"
        assert suite.purpose == SuitePurpose.REGRESSION
        assert suite.version == "1.0.0"  # 기본값
        assert suite.tags == []

    def test_suite_with_all_fields(self):
        """Suite 전체 필드 테스트"""
        suite = Suite(
            suite_id="full-suite",
            name="전체 필드 스위트",
            description="모든 필드를 포함한 Suite",
            version="2.0.0",
            purpose=SuitePurpose.CAPABILITY,
            domain="workflow",
            owner_team="ax-bd-team",
            tags=["test", "full"],
        )

        assert suite.description == "모든 필드를 포함한 Suite"
        assert suite.version == "2.0.0"
        assert suite.domain == "workflow"
        assert suite.owner_team == "ax-bd-team"
        assert suite.tags == ["test", "full"]


class TestTaskEntity:
    """Task 엔터티 테스트"""

    def test_create_task(self):
        """Task 생성 테스트"""
        task = Task(
            task_id="test-task",
            suite_id="test-suite",
            type=TaskType.WORKFLOW,
            description="테스트용 Task",
        )

        assert task.task_id == "test-task"
        assert task.suite_id == "test-suite"
        assert task.type == TaskType.WORKFLOW
        assert task.version == "1.0.0"
        assert task.description == "테스트용 Task"

    def test_task_with_metadata(self):
        """Task 메타데이터 테스트"""
        task = Task(
            task_id="meta-task",
            suite_id="test-suite",
            type=TaskType.CODING,
            description="메타데이터 포함 Task",
            domain="functionality",
            difficulty="medium",
            risk="low",
            expected_pass_rate=0.9,
            owner="tester",
        )

        assert task.description == "메타데이터 포함 Task"
        assert task.domain == "functionality"
        assert task.difficulty == "medium"
        assert task.risk == "low"
        assert task.expected_pass_rate == 0.9


class TestTrialEntity:
    """Trial 엔터티 테스트"""

    def test_create_trial(self):
        """Trial 생성 테스트"""
        trial = Trial(
            trial_id="trial-001",
            run_id="run-001",
            task_id="task-001",
            trial_index=0,
            status=TrialStatus.PENDING,
        )

        assert trial.trial_id == "trial-001"
        assert trial.run_id == "run-001"
        assert trial.task_id == "task-001"
        assert trial.trial_index == 0
        assert trial.status == TrialStatus.PENDING
        assert trial.started_at is None
        assert trial.completed_at is None

    def test_trial_completion(self):
        """Trial 완료 상태 테스트"""
        now = datetime.now(UTC)

        trial = Trial(
            trial_id="trial-002",
            run_id="run-001",
            task_id="task-001",
            trial_index=1,
            status=TrialStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            score=0.85,
            passed=True,
        )

        assert trial.status == TrialStatus.COMPLETED
        assert trial.score == 0.85
        assert trial.passed is True


class TestTranscriptEntity:
    """Transcript 엔터티 테스트"""

    def test_create_transcript(self):
        """Transcript 생성 테스트"""
        transcript = Transcript(
            trial_id="trial-001",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            tool_calls=[
                {"name": "search", "arguments": {"query": "test"}},
            ],
        )

        assert transcript.trial_id == "trial-001"
        assert len(transcript.messages) == 2
        assert len(transcript.tool_calls) == 1
        assert transcript.messages[0]["role"] == "user"

    def test_transcript_metrics(self):
        """Transcript 메트릭 테스트"""
        transcript = Transcript(
            trial_id="trial-002",
            messages=[],
            n_turns=5,
            n_tool_calls=10,
            n_errors=0,
        )

        assert transcript.n_turns == 5
        assert transcript.n_tool_calls == 10
        assert transcript.n_errors == 0


class TestOutcomeEntity:
    """Outcome 엔터티 테스트"""

    def test_create_outcome(self):
        """Outcome 생성 테스트"""
        outcome = Outcome(
            trial_id="trial-001",
            final_state={"status": "success"},
            artifacts=[{"path": "/tmp/test.log", "type": "log"}],
        )

        assert outcome.trial_id == "trial-001"
        assert outcome.final_state["status"] == "success"
        assert len(outcome.artifacts) == 1
        assert outcome.artifacts[0]["path"] == "/tmp/test.log"


class TestGraderResultEntity:
    """GraderResult 엔터티 테스트"""

    def test_create_grader_result(self):
        """GraderResult 생성 테스트"""
        result = GraderResult(
            trial_id="trial-001",
            grader_type="deterministic_tests",
            grader_id="unit_tests",
            score=0.95,
            passed=True,
        )

        assert result.trial_id == "trial-001"
        assert result.grader_type == "deterministic_tests"
        assert result.grader_id == "unit_tests"
        assert result.score == 0.95
        assert result.passed is True

    def test_grader_result_with_details(self):
        """GraderResult 상세 정보 테스트"""
        result = GraderResult(
            trial_id="trial-002",
            grader_type="llm_rubric",
            grader_id="quality_check",
            score=0.8,
            passed=True,
            partial_scores={
                "completeness": 0.9,
                "accuracy": 0.8,
            },
            explanation="모든 기준을 만족함",
        )

        assert result.partial_scores["completeness"] == 0.9
        assert result.explanation == "모든 기준을 만족함"


# ============================================================================
# Config 테스트
# ============================================================================


class TestTaskMetadata:
    """TaskMetadata 테스트"""

    def test_create_metadata(self):
        """TaskMetadata 생성 테스트"""
        metadata = TaskMetadata(
            domain=Domain.FUNCTIONALITY,
            difficulty=Difficulty.MEDIUM,
            risk=Risk.LOW,
        )

        assert metadata.domain == Domain.FUNCTIONALITY
        assert metadata.difficulty == Difficulty.MEDIUM
        assert metadata.risk == Risk.LOW

    def test_metadata_with_optional_fields(self):
        """TaskMetadata 선택 필드 테스트"""
        metadata = TaskMetadata(
            domain=Domain.SECURITY,
            difficulty=Difficulty.HARD,
            risk=Risk.HIGH,
            purpose=SuitePurpose.CAPABILITY,
            expected_pass_rate=0.7,
            owner="security-team",
            created_at="2026-01-18",
        )

        assert metadata.purpose == SuitePurpose.CAPABILITY
        assert metadata.expected_pass_rate == 0.7
        assert metadata.owner == "security-team"


class TestTaskInputs:
    """TaskInputs 테스트"""

    def test_create_inputs_with_prompt(self):
        """프롬프트 기반 TaskInputs 테스트"""
        inputs = TaskInputs(
            prompt="테스트 프롬프트입니다.",
        )

        assert inputs.prompt == "테스트 프롬프트입니다."
        assert inputs.prompt_file is None

    def test_create_inputs_with_context(self):
        """컨텍스트 포함 TaskInputs 테스트"""
        inputs = TaskInputs(
            prompt="분석해주세요.",
            context={"workflow_id": "WF-01"},
            environment_variables={"API_KEY": "test"},
        )

        assert inputs.context["workflow_id"] == "WF-01"
        assert inputs.environment_variables["API_KEY"] == "test"


class TestGraderConfig:
    """GraderConfig 테스트"""

    def test_create_grader_config(self):
        """GraderConfig 생성 테스트"""
        config = GraderConfig(
            type=GraderType.DETERMINISTIC_TESTS,
            id="unit_tests",
            weight=0.4,
        )

        assert config.type == GraderType.DETERMINISTIC_TESTS
        assert config.id == "unit_tests"
        assert config.weight == 0.4
        assert config.required is False
        assert config.enabled is True

    def test_grader_config_with_nested_config(self):
        """중첩 설정 포함 GraderConfig 테스트"""
        config = GraderConfig(
            type=GraderType.LLM_RUBRIC,
            id="quality",
            weight=0.3,
            required=True,
            config={
                "model": "claude-sonnet-4-20250514",
                "dimensions": [
                    {"name": "accuracy", "weight": 0.5},
                ],
            },
        )

        assert config.required is True
        assert config.config["model"] == "claude-sonnet-4-20250514"
        assert len(config.config["dimensions"]) == 1


class TestScoringConfig:
    """ScoringConfig 테스트"""

    def test_default_scoring_config(self):
        """기본 ScoringConfig 테스트"""
        config = ScoringConfig()

        assert config.mode == ScoringMode.WEIGHTED
        assert config.pass_threshold == 0.8
        assert config.required_graders == []

    def test_custom_scoring_config(self):
        """사용자 정의 ScoringConfig 테스트"""
        config = ScoringConfig(
            mode=ScoringMode.HYBRID,
            pass_threshold=0.9,
            required_graders=["db_state", "unit_tests"],
        )

        assert config.mode == ScoringMode.HYBRID
        assert config.pass_threshold == 0.9
        assert "db_state" in config.required_graders


class TestTrialConfig:
    """TrialConfig 테스트"""

    def test_default_trial_config(self):
        """기본 TrialConfig 테스트"""
        config = TrialConfig()

        assert config.k == 5
        assert config.parallel is True
        assert config.stop_on_first_pass is False

    def test_custom_trial_config(self):
        """사용자 정의 TrialConfig 테스트"""
        config = TrialConfig(
            k=3,
            parallel=False,
            stop_on_first_pass=True,
        )

        assert config.k == 3
        assert config.parallel is False
        assert config.stop_on_first_pass is True


class TestEnvironmentConfig:
    """EnvironmentConfig 테스트"""

    def test_default_environment_config(self):
        """기본 EnvironmentConfig 테스트"""
        config = EnvironmentConfig()

        assert config.sandbox == SandboxType.CONTAINER
        assert config.reset == ResetMode.CLEAN
        assert config.network == NetworkAccess.INTERNAL

    def test_container_environment(self):
        """컨테이너 환경 테스트"""
        config = EnvironmentConfig(
            sandbox=SandboxType.CONTAINER,
            image="python:3.11-slim",
            network=NetworkAccess.EXTERNAL,
        )

        assert config.sandbox == SandboxType.CONTAINER
        assert config.image == "python:3.11-slim"
        assert config.network == NetworkAccess.EXTERNAL


class TestTimeoutConfig:
    """TimeoutConfig 테스트"""

    def test_default_timeout_config(self):
        """기본 TimeoutConfig 테스트"""
        config = TimeoutConfig()

        assert config.total_seconds == 300
        assert config.per_turn_seconds == 60

    def test_custom_timeout_config(self):
        """사용자 정의 TimeoutConfig 테스트"""
        config = TimeoutConfig(
            total_seconds=180,
            per_turn_seconds=30,
        )

        assert config.total_seconds == 180
        assert config.per_turn_seconds == 30


class TestCostBudget:
    """CostBudget 테스트"""

    def test_create_cost_budget(self):
        """CostBudget 생성 테스트"""
        budget = CostBudget(
            max_tokens=50000,
            max_usd=0.5,
        )

        assert budget.max_tokens == 50000
        assert budget.max_usd == 0.5

    def test_cost_budget_with_warn_threshold(self):
        """경고 임계값 포함 CostBudget 테스트"""
        budget = CostBudget(
            max_tokens=100000,
            max_usd=1.0,
            warn_threshold=0.7,
        )

        assert budget.max_tokens == 100000
        assert budget.max_usd == 1.0
        assert budget.warn_threshold == 0.7
