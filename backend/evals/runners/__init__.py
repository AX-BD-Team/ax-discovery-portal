"""
Evals 실행기 패키지

Trial/Task/Suite 실행 및 결과 관리
"""

from backend.evals.runners.base import (
    BaseRunner,
    CostBudgetExceededError,
    MaxFailuresExceededError,
    RunnerConfig,
    RunnerContext,
    RunnerError,
    TimeoutError,
)
from backend.evals.runners.gate_checker import (
    GateCheckConfig,
    GateChecker,
    check_gate,
    get_exit_code,
)
from backend.evals.runners.results import (
    GateResult,
    RunResult,
    TaskResult,
    TrialResult,
)
from backend.evals.runners.suite_runner import SuiteRunner, run_suite
from backend.evals.runners.task_runner import TaskRunner, run_task
from backend.evals.runners.trial_executor import (
    TrialExecutor,
    execute_trial_with_grading,
)

__all__ = [
    # 기본 클래스
    "BaseRunner",
    "RunnerConfig",
    "RunnerContext",
    # 에러
    "RunnerError",
    "TimeoutError",
    "CostBudgetExceededError",
    "MaxFailuresExceededError",
    # 결과 모델
    "TrialResult",
    "TaskResult",
    "GateResult",
    "RunResult",
    # 실행기
    "TrialExecutor",
    "TaskRunner",
    "SuiteRunner",
    # 헬퍼 함수
    "execute_trial_with_grading",
    "run_task",
    "run_suite",
    # 게이트 체커
    "GateChecker",
    "GateCheckConfig",
    "check_gate",
    "get_exit_code",
]
