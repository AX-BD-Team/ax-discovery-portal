"""
Suite 실행기

전체 Suite (다중 Task) 실행
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import structlog

from backend.evals.models.entities import Run, Suite, Task
from backend.evals.models.enums import Decision, RunStatus
from backend.evals.runners.base import (
    BaseRunner,
    RunnerConfig,
    RunnerContext,
    RunnerError,
)
from backend.evals.runners.results import GateResult, RunResult, TaskResult
from backend.evals.runners.task_runner import TaskRunner

logger = structlog.get_logger()


class SuiteRunner(BaseRunner):
    """
    전체 Suite 실행

    1. Suite의 모든 Task 로드
    2. 각 Task에 대해 TaskRunner 실행
    3. 게이트 조건 검사 (pass_rate, required_tasks)
    4. Run 결과 저장 및 반환
    """

    def __init__(
        self,
        suite: Suite,
        tasks: list[Task],
        graders_map: dict[str, list[Any]] | None = None,  # task_id -> graders
        config: RunnerConfig | None = None,
        context: RunnerContext | None = None,
    ):
        super().__init__(config, context)
        self.suite = suite
        self.tasks = tasks
        self.graders_map = graders_map or {}
        self.logger = logger.bind(
            component="suite_runner",
            suite_id=suite.suite_id,
        )

        # Run 엔터티 생성
        self.run_entity = self._create_run()

    def _create_run(self) -> Run:
        """Run 엔터티 생성"""
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        return Run(
            run_id=run_id,
            suite_id=self.suite.suite_id,
            task_ids=[t.task_id for t in self.tasks],
            suite_version=self.suite.version,
            triggered_by=self.context.triggered_by if self.context else "manual",
            git_sha=self.context.git_sha if self.context else None,
            git_branch=self.context.git_branch if self.context else None,
            status=RunStatus.PENDING,
        )

    async def run(
        self,
        task_filter: list[str] | None = None,
        k: int = 5,
        parallel: bool = True,
    ) -> RunResult:
        """
        Suite 실행

        Args:
            task_filter: 실행할 Task ID 목록 (None이면 전체)
            k: Trial 횟수
            parallel: Task 병렬 실행 여부

        Returns:
            RunResult
        """
        self._started_at = datetime.now()
        self.run_entity.status = RunStatus.RUNNING
        self.run_entity.started_at = self._started_at

        self.logger.info(
            "Suite 실행 시작",
            task_count=len(self.tasks),
            task_filter=task_filter,
            k=k,
            parallel=parallel,
        )

        # Task 필터링
        tasks_to_run = self._filter_tasks(task_filter)

        if not tasks_to_run:
            self.logger.warning("실행할 Task가 없습니다")
            return self._create_empty_result()

        try:
            # Task 실행
            if parallel:
                task_results = await self._run_tasks_parallel(tasks_to_run, k)
            else:
                task_results = await self._run_tasks_sequential(tasks_to_run, k)

            # RunResult 생성
            run_result = RunResult(
                run=self.run_entity,
                task_results=task_results,
                started_at=self._started_at,
            )
            run_result.compute_statistics()

            # 게이트 판정
            run_result.gate_result = self._evaluate_gate(run_result)

            # Run 상태 업데이트
            self._completed_at = datetime.now()
            self.run_entity.status = RunStatus.COMPLETED
            self.run_entity.completed_at = self._completed_at

            self.logger.info(
                "Suite 실행 완료",
                total_tasks=run_result.total_tasks,
                passed_tasks=run_result.passed_tasks,
                gate_passed=run_result.gate_passed,
                decision=run_result.decision.value,
                duration_seconds=run_result.total_duration_seconds,
            )

            run_result.completed_at = self._completed_at
            return run_result

        except RunnerError as e:
            self.logger.error("Suite 실행 중 에러", error=str(e))
            self.run_entity.status = RunStatus.FAILED
            self._completed_at = datetime.now()
            self.run_entity.completed_at = self._completed_at
            raise

    def _filter_tasks(self, task_filter: list[str] | None) -> list[Task]:
        """Task 필터링"""
        if task_filter is None:
            return self.tasks

        filtered = [t for t in self.tasks if t.task_id in task_filter]

        if len(filtered) < len(task_filter):
            missing = set(task_filter) - {t.task_id for t in filtered}
            self.logger.warning(f"존재하지 않는 Task ID: {missing}")

        return filtered

    async def _run_tasks_parallel(
        self,
        tasks: list[Task],
        k: int,
    ) -> list[TaskResult]:
        """
        Task 병렬 실행

        Args:
            tasks: 실행할 Task 목록
            k: Trial 횟수

        Returns:
            TaskResult 목록
        """
        self.logger.debug(f"병렬 실행: {len(tasks)}개 Task")

        # 동시 실행 수 제한
        max_workers = min(len(tasks), self.config.max_workers)
        semaphore = asyncio.Semaphore(max_workers)

        async def run_with_semaphore(task: Task) -> TaskResult:
            async with semaphore:
                return await self._run_single_task(task, k)

        # 병렬 실행
        coros = [run_with_semaphore(task) for task in tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)

        # 예외 처리
        task_results: list[TaskResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Task {tasks[i].task_id} 예외 발생",
                    error=str(result),
                )
                task_results.append(self._create_error_task_result(tasks[i], result))
                self._record_failure()
            else:
                # result는 TaskResult 타입 (Exception이 아닌 경우)
                assert isinstance(result, TaskResult)
                task_results.append(result)
                if not result.passed:
                    self._record_failure()
                self._record_cost(result.total_cost)

        return task_results

    async def _run_tasks_sequential(
        self,
        tasks: list[Task],
        k: int,
    ) -> list[TaskResult]:
        """
        Task 순차 실행

        Args:
            tasks: 실행할 Task 목록
            k: Trial 횟수

        Returns:
            TaskResult 목록
        """
        self.logger.debug(f"순차 실행: {len(tasks)}개 Task")

        task_results: list[TaskResult] = []

        for task in tasks:
            try:
                # 비용/타임아웃 체크
                self._check_cost_budget()
                if self._started_at:
                    self._check_timeout(self.config.total_timeout, self._started_at)

                result = await self._run_single_task(task, k)
                task_results.append(result)

                self._record_cost(result.total_cost)
                if not result.passed:
                    self._record_failure()

            except RunnerError:
                raise
            except Exception as e:
                self.logger.error(f"Task {task.task_id} 예외 발생", error=str(e))
                task_results.append(self._create_error_task_result(task, e))
                self._record_failure()

        return task_results

    async def _run_single_task(self, task: Task, k: int) -> TaskResult:
        """
        단일 Task 실행

        Args:
            task: 실행할 Task
            k: Trial 횟수

        Returns:
            TaskResult
        """
        self.logger.debug(f"Task 실행: {task.task_id}")

        # Task별 채점기 조회
        graders = self.graders_map.get(task.task_id, [])

        # Task 설정에서 k 오버라이드
        trial_config = task.trial_config or {}
        task_k = trial_config.get("k", k)
        task_parallel = trial_config.get("parallel", True)

        # TaskRunner 생성 및 실행
        runner = TaskRunner(
            task=task,
            graders=graders,
            run_id=self.run_entity.run_id,
            config=self.config,
            context=self.context,
        )

        return await runner.run_task(k=task_k, parallel=task_parallel)

    def _create_error_task_result(
        self,
        task: Task,
        error: Exception,
    ) -> TaskResult:
        """에러 TaskResult 생성"""
        return TaskResult(
            task_id=task.task_id,
            trials=[],
            errors=[str(error)],
        )

    def _create_empty_result(self) -> RunResult:
        """빈 결과 생성"""
        self._completed_at = datetime.now()
        self.run_entity.status = RunStatus.COMPLETED
        self.run_entity.completed_at = self._completed_at

        return RunResult(
            run=self.run_entity,
            task_results=[],
            started_at=self._started_at,
            completed_at=self._completed_at,
            gate_result=GateResult(
                passed=True,
                decision=Decision.PASS,
                reason="실행할 Task 없음",
            ),
        )

    def _evaluate_gate(self, run_result: RunResult) -> GateResult:
        """
        게이트 조건 평가

        Args:
            run_result: 실행 결과

        Returns:
            GateResult
        """
        gate = GateResult()
        conditions: dict[str, bool] = {}
        failed_conditions: list[str] = []

        # 1. 통과율 검사
        required_pass_rate = 0.8  # TODO: Suite 설정에서 로드
        gate.required_pass_rate = required_pass_rate
        gate.actual_pass_rate = run_result.overall_pass_rate

        pass_rate_ok = run_result.overall_pass_rate >= required_pass_rate
        conditions["pass_rate"] = pass_rate_ok
        if not pass_rate_ok:
            failed_conditions.append(
                f"통과율 미달: {run_result.overall_pass_rate:.1%} < {required_pass_rate:.1%}"
            )

        # 2. 필수 Task 검사
        # TODO: Suite 설정에서 required_tasks 로드
        required_tasks: list[str] = []
        gate.required_tasks = required_tasks

        failed_required: list[str] = []
        for task_id in required_tasks:
            task_result = run_result.get_task_result(task_id)
            if task_result is None or not task_result.passed:
                failed_required.append(task_id)

        required_tasks_ok = len(failed_required) == 0
        conditions["required_tasks"] = required_tasks_ok
        gate.failed_required_tasks = failed_required
        if not required_tasks_ok:
            failed_conditions.append(f"필수 Task 실패: {failed_required}")

        # 3. 최소 점수 검사
        min_score_threshold = 0.5  # TODO: Suite 설정에서 로드
        min_score_ok = run_result.overall_avg_score >= min_score_threshold
        conditions["min_score"] = min_score_ok
        if not min_score_ok:
            failed_conditions.append(
                f"최소 점수 미달: {run_result.overall_avg_score:.2f} < {min_score_threshold}"
            )

        # 4. 최종 판정
        gate.conditions = conditions
        gate.failed_conditions = failed_conditions
        gate.passed = all(conditions.values())

        # Decision 결정
        if gate.passed:
            gate.decision = Decision.PASS
            gate.reason = "모든 게이트 조건 통과"
        elif run_result.overall_pass_rate >= 0.6:
            gate.decision = Decision.MARGINAL
            gate.reason = f"일부 조건 미달: {', '.join(failed_conditions)}"
        else:
            gate.decision = Decision.FAIL
            gate.reason = f"게이트 실패: {', '.join(failed_conditions)}"

        self.logger.info(
            "게이트 평가 완료",
            passed=gate.passed,
            decision=gate.decision.value,
            conditions=conditions,
        )

        return gate


async def run_suite(
    suite: Suite,
    tasks: list[Task],
    graders_map: dict[str, list[Any]] | None = None,
    task_filter: list[str] | None = None,
    k: int = 5,
    parallel: bool = True,
    config: RunnerConfig | None = None,
    context: RunnerContext | None = None,
) -> RunResult:
    """
    Suite 실행 헬퍼 함수

    Args:
        suite: 실행할 Suite
        tasks: Task 목록
        graders_map: Task ID별 채점기 맵
        task_filter: 실행할 Task ID 필터
        k: Trial 횟수
        parallel: 병렬 실행 여부
        config: Runner 설정
        context: 실행 컨텍스트

    Returns:
        RunResult
    """
    runner = SuiteRunner(
        suite=suite,
        tasks=tasks,
        graders_map=graders_map,
        config=config,
        context=context,
    )

    return await runner.run(task_filter=task_filter, k=k, parallel=parallel)
