"""
Evals 결과 모델

Runner 실행 결과를 담는 데이터 클래스들
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.evals.models.entities import (
    GraderResult,
    Outcome,
    Run,
    Transcript,
    Trial,
)
from backend.evals.models.enums import Decision, RunStatus


@dataclass
class TrialResult:
    """
    단일 Trial 실행 결과

    Trial 실행 후 채점까지 완료된 결과
    """

    # 기본 Trial 정보
    trial: Trial
    transcript: Transcript
    outcome: Outcome

    # 채점 결과
    grader_results: list[GraderResult] = field(default_factory=list)
    score: float = 0.0
    passed: bool = False

    # 에러 정보
    error: str | None = None
    error_type: str | None = None

    @property
    def trial_id(self) -> str:
        """Trial ID"""
        return self.trial.trial_id

    @property
    def task_id(self) -> str:
        """Task ID"""
        return self.trial.task_id

    @property
    def duration_seconds(self) -> float:
        """실행 시간 (초)"""
        return self.trial.duration_seconds

    @property
    def cost_usd(self) -> float:
        """비용 (USD)"""
        return self.trial.cost_usd

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "trial_id": self.trial_id,
            "task_id": self.task_id,
            "trial_index": self.trial.trial_index,
            "score": self.score,
            "passed": self.passed,
            "duration_seconds": self.duration_seconds,
            "cost_usd": self.cost_usd,
            "grader_count": len(self.grader_results),
            "error": self.error,
        }


@dataclass
class TaskResult:
    """
    단일 Task 실행 결과

    k번의 Trial 실행 결과를 집계
    """

    task_id: str
    trials: list[TrialResult] = field(default_factory=list)

    # 집계 통계
    pass_rate: float = 0.0  # 통과한 Trial 비율
    pass_at_k: float = 0.0  # pass@k (k번 중 1번 이상 성공 확률)
    pass_pow_k: float = 0.0  # pass^k (모든 Trial 성공 확률)
    avg_score: float = 0.0  # 평균 점수
    min_score: float = 0.0  # 최소 점수
    max_score: float = 0.0  # 최대 점수

    # 비용/시간
    total_cost: float = 0.0
    total_duration: float = 0.0

    # 에러 정보
    errors: list[str] = field(default_factory=list)

    def compute_statistics(self) -> None:
        """Trial 결과로부터 통계 계산"""
        if not self.trials:
            return

        k = len(self.trials)
        passed_count = sum(1 for t in self.trials if t.passed)
        scores = [t.score for t in self.trials]

        # 통과율
        self.pass_rate = passed_count / k

        # pass@k 계산
        # pass@k = 1 - (1 - p)^k, 여기서 p는 개별 trial 성공 확률
        # 단순화: k번 중 최소 1번 성공 확률 (이미 결과가 있으므로)
        self.pass_at_k = 1.0 if passed_count > 0 else 0.0

        # pass^k 계산 (모든 trial 성공)
        self.pass_pow_k = 1.0 if passed_count == k else 0.0

        # 점수 통계
        self.avg_score = sum(scores) / k if scores else 0.0
        self.min_score = min(scores) if scores else 0.0
        self.max_score = max(scores) if scores else 0.0

        # 비용/시간 합계
        self.total_cost = sum(t.cost_usd for t in self.trials)
        self.total_duration = sum(t.duration_seconds for t in self.trials)

        # 에러 수집
        self.errors = [t.error for t in self.trials if t.error]

    @property
    def passed(self) -> bool:
        """Task 통과 여부 (pass@k 기준)"""
        return self.pass_at_k > 0

    @property
    def trial_count(self) -> int:
        """실행된 Trial 수"""
        return len(self.trials)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "task_id": self.task_id,
            "trial_count": self.trial_count,
            "passed": self.passed,
            "pass_rate": self.pass_rate,
            "pass_at_k": self.pass_at_k,
            "pass_pow_k": self.pass_pow_k,
            "avg_score": self.avg_score,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "total_cost": self.total_cost,
            "total_duration": self.total_duration,
            "error_count": len(self.errors),
        }


@dataclass
class GateResult:
    """
    게이트 판정 결과

    CI/CD 게이트 조건 검사 결과
    """

    passed: bool = False
    decision: Decision = Decision.UNKNOWN
    reason: str = ""

    # 세부 조건
    conditions: dict[str, bool] = field(default_factory=dict)
    failed_conditions: list[str] = field(default_factory=list)

    # 임계값
    required_pass_rate: float = 0.8
    actual_pass_rate: float = 0.0
    required_tasks: list[str] = field(default_factory=list)
    failed_required_tasks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "passed": self.passed,
            "decision": self.decision.value,
            "reason": self.reason,
            "conditions": self.conditions,
            "failed_conditions": self.failed_conditions,
            "required_pass_rate": self.required_pass_rate,
            "actual_pass_rate": self.actual_pass_rate,
            "failed_required_tasks": self.failed_required_tasks,
        }


@dataclass
class RunResult:
    """
    전체 Run 실행 결과

    Suite 또는 개별 Task들의 실행 결과를 집계
    """

    # Run 정보
    run: Run
    task_results: list[TaskResult] = field(default_factory=list)

    # 게이트 판정
    gate_result: GateResult = field(default_factory=GateResult)

    # 집계 통계
    total_tasks: int = 0
    passed_tasks: int = 0
    failed_tasks: int = 0
    total_trials: int = 0
    passed_trials: int = 0

    # 메트릭
    overall_pass_rate: float = 0.0
    overall_avg_score: float = 0.0
    total_cost_usd: float = 0.0
    total_duration_seconds: float = 0.0

    # 타임스탬프
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def compute_statistics(self) -> None:
        """Task 결과로부터 전체 통계 계산"""
        if not self.task_results:
            return

        # Task별 통계 먼저 계산
        for task_result in self.task_results:
            task_result.compute_statistics()

        # 전체 통계
        self.total_tasks = len(self.task_results)
        self.passed_tasks = sum(1 for t in self.task_results if t.passed)
        self.failed_tasks = self.total_tasks - self.passed_tasks

        # Trial 통계
        self.total_trials = sum(t.trial_count for t in self.task_results)
        self.passed_trials = sum(
            sum(1 for trial in t.trials if trial.passed) for t in self.task_results
        )

        # 비율 계산
        if self.total_tasks > 0:
            self.overall_pass_rate = self.passed_tasks / self.total_tasks

        # 평균 점수
        all_scores = [
            trial.score for task_result in self.task_results for trial in task_result.trials
        ]
        if all_scores:
            self.overall_avg_score = sum(all_scores) / len(all_scores)

        # 비용/시간 합계
        self.total_cost_usd = sum(t.total_cost for t in self.task_results)
        self.total_duration_seconds = sum(t.total_duration for t in self.task_results)

        # Run 모델 업데이트
        self.run.total_tasks = self.total_tasks
        self.run.passed_tasks = self.passed_tasks
        self.run.failed_tasks = self.failed_tasks
        self.run.total_cost_usd = self.total_cost_usd
        self.run.total_duration_seconds = self.total_duration_seconds

    @property
    def gate_passed(self) -> bool:
        """게이트 통과 여부"""
        return self.gate_result.passed

    @property
    def decision(self) -> Decision:
        """최종 판정"""
        return self.gate_result.decision

    @property
    def status(self) -> RunStatus:
        """실행 상태"""
        return self.run.status

    def get_failed_tasks(self) -> list[str]:
        """실패한 Task ID 목록"""
        return [t.task_id for t in self.task_results if not t.passed]

    def get_task_result(self, task_id: str) -> TaskResult | None:
        """특정 Task 결과 조회"""
        for task_result in self.task_results:
            if task_result.task_id == task_id:
                return task_result
        return None

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "run_id": self.run.run_id,
            "suite_id": self.run.suite_id,
            "status": self.run.status.value,
            "total_tasks": self.total_tasks,
            "passed_tasks": self.passed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_trials": self.total_trials,
            "passed_trials": self.passed_trials,
            "overall_pass_rate": self.overall_pass_rate,
            "overall_avg_score": self.overall_avg_score,
            "total_cost_usd": self.total_cost_usd,
            "total_duration_seconds": self.total_duration_seconds,
            "gate_passed": self.gate_passed,
            "decision": self.decision.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "task_results": [t.to_dict() for t in self.task_results],
        }

    def to_summary(self) -> dict[str, Any]:
        """요약 정보 반환"""
        return {
            "run_id": self.run.run_id,
            "status": self.run.status.value,
            "passed": self.gate_passed,
            "decision": self.decision.value,
            "pass_rate": f"{self.overall_pass_rate:.1%}",
            "avg_score": f"{self.overall_avg_score:.2f}",
            "tasks": f"{self.passed_tasks}/{self.total_tasks}",
            "cost": f"${self.total_cost_usd:.4f}",
            "duration": f"{self.total_duration_seconds:.1f}s",
        }
