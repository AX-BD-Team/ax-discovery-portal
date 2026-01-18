"""
Evals Runner 기본 클래스

모든 Runner의 공통 인터페이스 정의
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from backend.evals.runners.results import RunResult

logger = structlog.get_logger()


@dataclass
class RunnerContext:
    """Runner 실행 컨텍스트"""

    run_id: str
    started_at: datetime = field(default_factory=datetime.now)
    git_sha: str | None = None
    git_branch: str | None = None
    triggered_by: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunnerConfig:
    """Runner 설정"""

    # 병렬 실행
    parallel: bool = True
    max_workers: int = 4

    # 타임아웃 (초)
    total_timeout: int = 3600  # 전체 실행 타임아웃 (1시간)
    task_timeout: int = 600  # Task당 타임아웃 (10분)
    trial_timeout: int = 300  # Trial당 타임아웃 (5분)

    # 비용 제한
    max_cost_usd: float | None = None  # 최대 비용 (USD)
    cost_warning_threshold: float = 0.8  # 비용 경고 임계값

    # 중단 조건
    stop_on_failure: bool = False  # 첫 실패 시 중단
    max_failures: int | None = None  # 최대 실패 허용 수

    # 디버깅
    verbose: bool = False
    save_transcripts: bool = True


class RunnerError(Exception):
    """Runner 실행 중 발생하는 에러의 기본 클래스"""

    pass


class TimeoutError(RunnerError):
    """타임아웃 에러"""

    def __init__(self, message: str, duration_seconds: float):
        super().__init__(message)
        self.duration_seconds = duration_seconds


class CostBudgetExceededError(RunnerError):
    """비용 예산 초과 에러"""

    def __init__(self, message: str, current_cost: float, budget: float):
        super().__init__(message)
        self.current_cost = current_cost
        self.budget = budget


class MaxFailuresExceededError(RunnerError):
    """최대 실패 수 초과 에러"""

    def __init__(self, message: str, failure_count: int, max_failures: int):
        super().__init__(message)
        self.failure_count = failure_count
        self.max_failures = max_failures


class BaseRunner(ABC):
    """
    Runner 기본 클래스

    모든 Runner (TrialExecutor, TaskRunner, SuiteRunner)의 공통 인터페이스
    """

    def __init__(
        self,
        config: RunnerConfig | None = None,
        context: RunnerContext | None = None,
    ):
        self.config = config or RunnerConfig()
        self.context = context
        self.logger = logger.bind(runner=self.__class__.__name__)

        # 상태 추적
        self._started_at: datetime | None = None
        self._completed_at: datetime | None = None
        self._current_cost: float = 0.0
        self._failure_count: int = 0

    @abstractmethod
    async def run(self) -> "RunResult":
        """
        Runner 실행

        Returns:
            RunResult: 실행 결과
        """
        ...

    def _check_timeout(self, timeout_seconds: int, started_at: datetime) -> None:
        """타임아웃 체크"""
        elapsed = (datetime.now() - started_at).total_seconds()
        if elapsed > timeout_seconds:
            raise TimeoutError(
                f"실행 시간 초과: {elapsed:.1f}초 > {timeout_seconds}초",
                duration_seconds=elapsed,
            )

    def _check_cost_budget(self, additional_cost: float = 0.0) -> None:
        """비용 예산 체크"""
        if self.config.max_cost_usd is None:
            return

        projected_cost = self._current_cost + additional_cost

        # 경고 임계값 체크
        warning_threshold = self.config.max_cost_usd * self.config.cost_warning_threshold
        if projected_cost >= warning_threshold:
            self.logger.warning(
                "비용 경고: 예산 임계값 도달",
                current_cost=self._current_cost,
                projected_cost=projected_cost,
                budget=self.config.max_cost_usd,
                threshold=warning_threshold,
            )

        # 예산 초과 체크
        if projected_cost > self.config.max_cost_usd:
            raise CostBudgetExceededError(
                f"비용 예산 초과: ${projected_cost:.4f} > ${self.config.max_cost_usd:.4f}",
                current_cost=projected_cost,
                budget=self.config.max_cost_usd,
            )

    def _check_max_failures(self) -> None:
        """최대 실패 수 체크"""
        if self.config.max_failures is None:
            return

        if self._failure_count >= self.config.max_failures:
            raise MaxFailuresExceededError(
                f"최대 실패 수 초과: {self._failure_count} >= {self.config.max_failures}",
                failure_count=self._failure_count,
                max_failures=self.config.max_failures,
            )

    def _record_cost(self, cost: float) -> None:
        """비용 기록"""
        self._current_cost += cost

    def _record_failure(self) -> None:
        """실패 기록"""
        self._failure_count += 1

        if self.config.stop_on_failure:
            raise RunnerError("실행 중 실패 발생 - stop_on_failure 설정으로 중단")

        self._check_max_failures()
