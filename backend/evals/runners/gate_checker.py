"""
게이트 체커 (Gate Checker)

CI/CD 게이트 조건을 검사하고 판정 결과를 반환

주요 기능:
- pass_rate 조건 검사 (통과율)
- required_tasks 조건 검사 (필수 Task)
- min_score 조건 검사 (최소 점수)
- max_regression_count 조건 검사 (회귀 허용 개수)
- 상세 리포트 생성
"""

from dataclasses import dataclass, field
from typing import Any

import structlog

from backend.evals.models.enums import Decision
from backend.evals.models.suite import SuiteDefinition
from backend.evals.runners.results import GateResult, RunResult

logger = structlog.get_logger(__name__)


@dataclass
class GateCheckConfig:
    """게이트 체크 설정"""

    # 통과율 기준
    min_pass_rate: float = 0.8
    """최소 통과율 (0.0 ~ 1.0)"""

    # 필수 Task
    required_tasks: list[str] = field(default_factory=list)
    """반드시 통과해야 하는 Task ID 목록"""

    # 최소 점수
    min_score: float = 0.5
    """전체 평균 최소 점수 (0.0 ~ 1.0)"""

    # 회귀 허용
    max_regression_count: int = 0
    """허용 가능한 최대 회귀 개수"""

    # 블로킹 여부
    blocking: bool = True
    """실패 시 CI 차단 여부"""

    # 예외 처리
    allow_skip_with_approval: bool = False
    """승인 시 스킵 허용 여부"""

    approvers: list[str] = field(default_factory=list)
    """스킵 승인 가능 사용자 목록"""


class GateChecker:
    """
    게이트 조건 검사기

    Suite 설정과 실행 결과를 기반으로 게이트 통과 여부를 판정

    사용법:
        checker = GateChecker(suite_definition)
        result = checker.check(run_result)
        if not result.passed:
            print(f"게이트 실패: {result.reason}")
    """

    def __init__(
        self,
        suite: SuiteDefinition | None = None,
        config: GateCheckConfig | None = None,
    ):
        """
        게이트 체커 초기화

        Args:
            suite: Suite 정의 (게이트 설정 추출용)
            config: 명시적 게이트 설정 (suite보다 우선)
        """
        self.suite = suite
        self.config = config or self._extract_config_from_suite(suite)
        self.logger = logger.bind(component="gate_checker")

    def _extract_config_from_suite(
        self,
        suite: SuiteDefinition | None,
    ) -> GateCheckConfig:
        """Suite 정의에서 게이트 설정 추출"""
        if suite is None or suite.suite.gates is None:
            return GateCheckConfig()

        gates = suite.suite.gates
        pass_criteria = gates.pass_criteria
        exceptions = gates.exceptions

        return GateCheckConfig(
            min_pass_rate=pass_criteria.min_pass_rate if pass_criteria else 0.8,
            required_tasks=pass_criteria.required_tasks if pass_criteria else [],
            min_score=0.5,  # Suite 스키마에 없으므로 기본값
            max_regression_count=pass_criteria.max_regression_count if pass_criteria else 0,
            blocking=gates.blocking,
            allow_skip_with_approval=exceptions.allow_skip_with_approval if exceptions else False,
            approvers=exceptions.approvers if exceptions else [],
        )

    def check(
        self,
        run_result: RunResult,
        baseline_result: RunResult | None = None,
    ) -> GateResult:
        """
        게이트 조건 검사 실행

        Args:
            run_result: 현재 실행 결과
            baseline_result: 비교 기준 결과 (회귀 검사용)

        Returns:
            GateResult: 게이트 판정 결과
        """
        self.logger.info(
            "게이트 검사 시작",
            suite_id=run_result.run.suite_id,
            run_id=run_result.run.run_id,
        )

        gate = GateResult()
        conditions: dict[str, bool] = {}
        failed_conditions: list[str] = []

        # 1. 통과율 검사
        pass_rate_result = self._check_pass_rate(run_result)
        conditions["pass_rate"] = pass_rate_result["passed"]
        gate.required_pass_rate = self.config.min_pass_rate
        gate.actual_pass_rate = run_result.overall_pass_rate
        if not pass_rate_result["passed"]:
            failed_conditions.append(pass_rate_result["message"])

        # 2. 필수 Task 검사
        required_tasks_result = self._check_required_tasks(run_result)
        conditions["required_tasks"] = required_tasks_result["passed"]
        gate.required_tasks = self.config.required_tasks
        gate.failed_required_tasks = required_tasks_result.get("failed_tasks", [])
        if not required_tasks_result["passed"]:
            failed_conditions.append(required_tasks_result["message"])

        # 3. 최소 점수 검사
        min_score_result = self._check_min_score(run_result)
        conditions["min_score"] = min_score_result["passed"]
        if not min_score_result["passed"]:
            failed_conditions.append(min_score_result["message"])

        # 4. 회귀 검사 (baseline이 있는 경우)
        if baseline_result:
            regression_result = self._check_regression(run_result, baseline_result)
            conditions["regression"] = regression_result["passed"]
            if not regression_result["passed"]:
                failed_conditions.append(regression_result["message"])

        # 5. 최종 판정
        gate.conditions = conditions
        gate.failed_conditions = failed_conditions
        gate.passed = all(conditions.values())

        # Decision 결정
        gate.decision = self._determine_decision(gate, run_result)
        gate.reason = self._generate_reason(gate, failed_conditions)

        self.logger.info(
            "게이트 검사 완료",
            passed=gate.passed,
            decision=gate.decision.value,
            failed_count=len(failed_conditions),
        )

        return gate

    def _check_pass_rate(self, result: RunResult) -> dict[str, Any]:
        """통과율 검사"""
        actual = result.overall_pass_rate
        required = self.config.min_pass_rate
        passed = actual >= required

        return {
            "passed": passed,
            "actual": actual,
            "required": required,
            "message": f"통과율 미달: {actual:.1%} < {required:.1%}" if not passed else "",
        }

    def _check_required_tasks(self, result: RunResult) -> dict[str, Any]:
        """필수 Task 검사"""
        required = self.config.required_tasks
        if not required:
            return {"passed": True, "failed_tasks": [], "message": ""}

        failed_tasks: list[str] = []
        for task_id in required:
            task_result = result.get_task_result(task_id)
            if task_result is None:
                # Task가 실행되지 않음
                failed_tasks.append(f"{task_id} (미실행)")
            elif not task_result.passed:
                failed_tasks.append(f"{task_id} (실패)")

        passed = len(failed_tasks) == 0

        return {
            "passed": passed,
            "failed_tasks": failed_tasks,
            "message": f"필수 Task 실패: {', '.join(failed_tasks)}" if not passed else "",
        }

    def _check_min_score(self, result: RunResult) -> dict[str, Any]:
        """최소 점수 검사"""
        actual = result.overall_avg_score
        required = self.config.min_score
        passed = actual >= required

        return {
            "passed": passed,
            "actual": actual,
            "required": required,
            "message": f"최소 점수 미달: {actual:.2f} < {required:.2f}" if not passed else "",
        }

    def _check_regression(
        self,
        current: RunResult,
        baseline: RunResult,
    ) -> dict[str, Any]:
        """회귀 검사 (baseline 대비)"""
        regressions: list[str] = []

        # 이전에 통과했지만 현재 실패한 Task 찾기
        for task_result in current.task_results:
            baseline_task = baseline.get_task_result(task_result.task_id)
            if baseline_task and baseline_task.passed and not task_result.passed:
                regressions.append(task_result.task_id)

        allowed = self.config.max_regression_count
        passed = len(regressions) <= allowed

        return {
            "passed": passed,
            "regressions": regressions,
            "count": len(regressions),
            "allowed": allowed,
            "message": f"회귀 발생 ({len(regressions)}개 > {allowed}개 허용): {', '.join(regressions)}"
            if not passed
            else "",
        }

    def _determine_decision(self, gate: GateResult, result: RunResult) -> Decision:
        """최종 판정 결정"""
        if gate.passed:
            return Decision.PASS

        # 통과율이 60% 이상이면 MARGINAL
        if result.overall_pass_rate >= 0.6:
            return Decision.MARGINAL

        return Decision.FAIL

    def _generate_reason(
        self,
        gate: GateResult,
        failed_conditions: list[str],
    ) -> str:
        """판정 사유 생성"""
        if gate.passed:
            return "모든 게이트 조건 통과"

        if gate.decision == Decision.MARGINAL:
            return f"일부 조건 미달 (검토 필요): {'; '.join(failed_conditions)}"

        return f"게이트 실패: {'; '.join(failed_conditions)}"

    def format_report(self, gate: GateResult) -> str:
        """게이트 결과 리포트 생성"""
        lines = [
            "",
            "═" * 60,
            "🚦 CI 게이트 체크 결과",
            "═" * 60,
            "",
            f"결과: {'✅ 통과' if gate.passed else '❌ 실패'}",
            f"판정: {gate.decision.value}",
            f"사유: {gate.reason}",
            "",
            "─" * 60,
            "📋 조건별 검사 결과",
            "─" * 60,
        ]

        for condition, passed in gate.conditions.items():
            icon = "✅" if passed else "❌"
            condition_name = self._get_condition_display_name(condition)
            lines.append(f"  {icon} {condition_name}")

        # 통과율 상세
        lines.extend(
            [
                "",
                "─" * 60,
                "📊 상세 정보",
                "─" * 60,
                f"  요구 통과율: {gate.required_pass_rate:.1%}",
                f"  실제 통과율: {gate.actual_pass_rate:.1%}",
            ]
        )

        # 필수 Task 상세
        if gate.required_tasks:
            lines.append(f"  필수 Task: {', '.join(gate.required_tasks)}")
        if gate.failed_required_tasks:
            lines.append(f"  실패한 필수 Task: {', '.join(gate.failed_required_tasks)}")

        # 실패 조건 상세
        if gate.failed_conditions:
            lines.extend(
                [
                    "",
                    "─" * 60,
                    "⚠️ 실패 조건 상세",
                    "─" * 60,
                ]
            )
            for condition in gate.failed_conditions:
                lines.append(f"  • {condition}")

        lines.extend(
            [
                "",
                "═" * 60,
            ]
        )

        return "\n".join(lines)

    def _get_condition_display_name(self, condition: str) -> str:
        """조건 표시 이름"""
        names = {
            "pass_rate": "통과율",
            "required_tasks": "필수 Task",
            "min_score": "최소 점수",
            "regression": "회귀 검사",
        }
        return names.get(condition, condition)


def check_gate(
    run_result: RunResult,
    suite: SuiteDefinition | None = None,
    config: GateCheckConfig | None = None,
    baseline_result: RunResult | None = None,
) -> GateResult:
    """
    게이트 검사 편의 함수

    Args:
        run_result: 실행 결과
        suite: Suite 정의
        config: 게이트 설정
        baseline_result: baseline 결과 (회귀 검사용)

    Returns:
        GateResult
    """
    checker = GateChecker(suite=suite, config=config)
    return checker.check(run_result, baseline_result)


def get_exit_code(gate_result: GateResult) -> int:
    """
    게이트 결과에 따른 종료 코드 반환

    Args:
        gate_result: 게이트 판정 결과

    Returns:
        종료 코드:
        - 0: 통과
        - 1: 실패 (blocking)
        - 2: MARGINAL (경고, non-blocking 가능)
    """
    if gate_result.passed:
        return 0

    if gate_result.decision == Decision.MARGINAL:
        return 2

    return 1
