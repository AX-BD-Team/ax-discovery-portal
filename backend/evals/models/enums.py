"""
Evals Enum 정의

평가 플랫폼에서 사용하는 열거형 타입
"""

from enum import Enum


class TaskType(str, Enum):
    """Task 유형"""

    CODING = "coding"
    WORKFLOW = "workflow"
    CONVERSATIONAL = "conversational"
    RESEARCH = "research"
    COMPUTER_USE = "computer_use"


class TrialStatus(str, Enum):
    """Trial 실행 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class RunStatus(str, Enum):
    """Run(평가 세션) 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SuitePurpose(str, Enum):
    """Suite 목적"""

    CAPABILITY = "capability"  # 역량 측정 (새 기능, 품질 향상)
    REGRESSION = "regression"  # 회귀 방지 (기존 기능 유지)
    BENCHMARK = "benchmark"  # 벤치마크 (모델/에이전트 비교)
    SAFETY = "safety"  # 안전성 테스트


class GraderType(str, Enum):
    """채점기 유형"""

    # Deterministic (결정적)
    DETERMINISTIC_TESTS = "deterministic_tests"
    STATIC_ANALYSIS = "static_analysis"
    STRING_MATCH = "string_match"
    REGEX_MATCH = "regex_match"
    TOOL_CALL_CHECK = "tool_call_check"
    STATE_CHECK = "state_check"
    TRANSCRIPT_METRICS = "transcript_metrics"
    LATENCY_CHECK = "latency_check"

    # LLM-as-Judge
    LLM_RUBRIC = "llm_rubric"
    LLM_ASSERTION = "llm_assertion"
    LLM_PAIRWISE = "llm_pairwise"
    LLM_REFERENCE = "llm_reference"

    # Human
    HUMAN_REVIEW = "human_review"


class ScoringMode(str, Enum):
    """채점 모드"""

    WEIGHTED = "weighted"  # 가중치 기반 합산
    BINARY = "binary"  # 모든 채점기 통과 필요
    HYBRID = "hybrid"  # 필수 + 가중치 조합
    PARTIAL_CREDIT = "partial_credit"  # 부분 점수


class SandboxType(str, Enum):
    """샌드박스/격리 유형"""

    NONE = "none"  # 격리 없음 (위험)
    PROCESS = "process"  # 프로세스 격리
    CONTAINER = "container"  # 컨테이너 격리 (권장)
    VM = "vm"  # VM 격리


class ResetMode(str, Enum):
    """환경 리셋 모드"""

    CLEAN = "clean"  # 매 Trial마다 깨끗한 환경
    SNAPSHOT = "snapshot"  # 스냅샷 기반 복원
    PERSIST = "persist"  # 상태 유지 (주의 필요)


class NetworkAccess(str, Enum):
    """네트워크 접근 수준"""

    NONE = "none"  # 네트워크 차단
    INTERNAL = "internal"  # 내부 네트워크만
    EXTERNAL = "external"  # 외부 네트워크 허용


class AgentAdapter(str, Enum):
    """에이전트 어댑터 유형"""

    AX_AGENT_SDK = "ax_agent_sdk"
    CLAUDE_CODE = "claude_code"
    LANGCHAIN = "langchain"
    CUSTOM = "custom"


class MetricType(str, Enum):
    """메트릭 유형"""

    TRANSCRIPT = "transcript"
    LATENCY = "latency"
    COST = "cost"
    CUSTOM = "custom"


class Domain(str, Enum):
    """도메인 분류"""

    SECURITY = "security"
    PERFORMANCE = "performance"
    FUNCTIONALITY = "functionality"
    UX = "ux"
    INTEGRATION = "integration"
    DATA_QUALITY = "data_quality"


class Difficulty(str, Enum):
    """난이도"""

    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class Risk(str, Enum):
    """위험도 (실패 시 영향)"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Decision(str, Enum):
    """평가 판정"""

    PASS = "pass"
    FAIL = "fail"
    MARGINAL = "marginal"
    UNKNOWN = "unknown"


class TestFramework(str, Enum):
    """테스트 프레임워크"""

    PYTEST = "pytest"
    JEST = "jest"
    MOCHA = "mocha"
    GO_TEST = "go_test"
    CARGO_TEST = "cargo_test"
    JUNIT = "junit"


class StaticAnalysisTool(str, Enum):
    """정적 분석 도구"""

    RUFF = "ruff"
    MYPY = "mypy"
    ESLINT = "eslint"
    PYLINT = "pylint"
    BANDIT = "bandit"
    SEMGREP = "semgrep"
    CLIPPY = "clippy"


class NotificationChannel(str, Enum):
    """알림 채널"""

    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
