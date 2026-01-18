"""
Task 실행기

단일 Task에 대해 k번의 Trial을 실행
"""

import asyncio
from datetime import datetime
from typing import Any

import structlog

from backend.evals.models.entities import Task
from backend.evals.runners.base import (
    BaseRunner,
    RunnerConfig,
    RunnerContext,
    RunnerError,
)
from backend.evals.runners.results import RunResult, TaskResult, TrialResult
from backend.evals.runners.trial_executor import TrialExecutor, execute_trial_with_grading

logger = structlog.get_logger()


class TaskRunner(BaseRunner):
    """
    단일 Task에 대해 k번 Trial 실행

    1. k번 Trial 실행 (parallel or sequential)
    2. 각 Trial에 대해 채점기 실행
    3. 점수 집계 (pass@k, pass^k 계산)
    4. TaskResult 반환
    """

    def __init__(
        self,
        task: Task,
        graders: list[Any],  # TODO: list[BaseGrader]로 변경
        run_id: str,
        config: RunnerConfig | None = None,
        context: RunnerContext | None = None,
    ):
        super().__init__(config, context)
        self.task = task
        self.graders = graders
        self.run_id = run_id
        self.executor = TrialExecutor(run_id=run_id, config=config)
        self.logger = logger.bind(
            component="task_runner",
            task_id=task.task_id,
            run_id=run_id,
        )

    async def run(self, k: int = 5, parallel: bool = True) -> "RunResult":
        """
        Task 실행

        Args:
            k: Trial 실행 횟수
            parallel: 병렬 실행 여부

        Returns:
            RunResult (단일 Task만 포함)
        """
        # TaskResult로 반환하는 것이 더 적절
        task_result = await self.run_task(k=k, parallel=parallel)

        # RunResult로 래핑 (인터페이스 일관성)
        from backend.evals.models.entities import Run
        from backend.evals.models.enums import RunStatus

        run = Run(
            run_id=self.run_id,
            task_ids=[self.task.task_id],
            status=RunStatus.COMPLETED,
        )

        run_result = RunResult(
            run=run,
            task_results=[task_result],
        )
        run_result.compute_statistics()

        return run_result

    async def run_task(self, k: int = 5, parallel: bool = True) -> TaskResult:
        """
        Task 실행 (TaskResult 반환)

        Args:
            k: Trial 실행 횟수
            parallel: 병렬 실행 여부

        Returns:
            TaskResult
        """
        self._started_at = datetime.now()

        self.logger.info(
            "Task 실행 시작",
            k=k,
            parallel=parallel,
            task_type=self.task.type.value if self.task.type else "unknown",
        )

        # Trial 설정
        trial_config = self.task.trial_config or {}
        seeds = trial_config.get("seeds")
        stop_on_first_pass = trial_config.get("stop_on_first_pass", False)

        # Trial 실행
        trial_results: list[TrialResult] = []

        if parallel and not stop_on_first_pass:
            # 병렬 실행
            trial_results = await self._run_trials_parallel(k, seeds)
        else:
            # 순차 실행
            trial_results = await self._run_trials_sequential(k, seeds, stop_on_first_pass)

        # TaskResult 생성
        task_result = TaskResult(
            task_id=self.task.task_id,
            trials=trial_results,
        )
        task_result.compute_statistics()

        self._completed_at = datetime.now()
        duration = (self._completed_at - self._started_at).total_seconds()

        self.logger.info(
            "Task 실행 완료",
            trial_count=len(trial_results),
            passed=task_result.passed,
            pass_rate=task_result.pass_rate,
            avg_score=task_result.avg_score,
            duration_seconds=duration,
        )

        return task_result

    async def _run_trials_parallel(
        self,
        k: int,
        seeds: list[int] | None = None,
    ) -> list[TrialResult]:
        """
        Trial 병렬 실행

        Args:
            k: 실행 횟수
            seeds: 시드 목록

        Returns:
            Trial 결과 목록
        """
        self.logger.debug(f"병렬 실행: {k}개 Trial")

        # 동시 실행 수 제한
        max_workers = min(k, self.config.max_workers)
        semaphore = asyncio.Semaphore(max_workers)

        async def run_with_semaphore(trial_index: int, seed: int | None) -> TrialResult:
            async with semaphore:
                return await self._execute_single_trial(trial_index, seed)

        # 시드 준비
        trial_seeds: list[int | None] = list(seeds[:k]) if seeds else [None] * k
        if seeds and len(seeds) < k:
            # 시드가 부족하면 None으로 채움
            trial_seeds.extend([None] * (k - len(seeds)))

        # 병렬 실행
        tasks = [run_with_semaphore(i, trial_seeds[i]) for i in range(k)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외 처리
        trial_results: list[TrialResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Trial {i} 예외 발생", error=str(result))
                # 실패한 Trial도 결과에 포함
                trial_results.append(self._create_error_trial_result(i, result))
                self._record_failure()
            else:
                # result는 TrialResult 타입 (Exception이 아닌 경우)
                assert isinstance(result, TrialResult)
                trial_results.append(result)
                if not result.passed:
                    self._record_failure()
                self._record_cost(result.cost_usd)

        return trial_results

    async def _run_trials_sequential(
        self,
        k: int,
        seeds: list[int] | None = None,
        stop_on_first_pass: bool = False,
    ) -> list[TrialResult]:
        """
        Trial 순차 실행

        Args:
            k: 실행 횟수
            seeds: 시드 목록
            stop_on_first_pass: 첫 성공 시 중단

        Returns:
            Trial 결과 목록
        """
        self.logger.debug(f"순차 실행: {k}개 Trial (stop_on_first_pass={stop_on_first_pass})")

        trial_results: list[TrialResult] = []

        for i in range(k):
            seed = seeds[i] if seeds and i < len(seeds) else None

            try:
                result = await self._execute_single_trial(i, seed)
                trial_results.append(result)

                self._record_cost(result.cost_usd)
                if not result.passed:
                    self._record_failure()

                # 첫 성공 시 중단
                if stop_on_first_pass and result.passed:
                    self.logger.info(f"첫 성공으로 중단 (Trial {i})")
                    break

            except RunnerError:
                # 비용/실패 제한 초과 시 중단
                raise
            except Exception as e:
                self.logger.error(f"Trial {i} 예외 발생", error=str(e))
                trial_results.append(self._create_error_trial_result(i, e))
                self._record_failure()

        return trial_results

    async def _execute_single_trial(
        self,
        trial_index: int,
        seed: int | None,
    ) -> TrialResult:
        """
        단일 Trial 실행 (채점 포함)

        Args:
            trial_index: Trial 인덱스
            seed: 랜덤 시드

        Returns:
            TrialResult
        """
        # 비용 예산 체크
        self._check_cost_budget()

        # 타임아웃 체크
        if self._started_at:
            self._check_timeout(self.config.task_timeout, self._started_at)

        # Trial 실행 + 채점
        result = await execute_trial_with_grading(
            executor=self.executor,
            task=self.task,
            trial_index=trial_index,
            graders=self.graders,
            seed=seed,
        )

        return result

    def _create_error_trial_result(
        self,
        trial_index: int,
        error: Exception,
    ) -> TrialResult:
        """에러 Trial 결과 생성"""
        import uuid

        from backend.evals.models.entities import Outcome, Transcript, Trial
        from backend.evals.models.enums import TrialStatus

        trial_id = f"trial_{uuid.uuid4().hex[:12]}"

        trial = Trial(
            trial_id=trial_id,
            run_id=self.run_id,
            task_id=self.task.task_id,
            trial_index=trial_index,
            status=TrialStatus.FAILED,
            error_message=str(error),
            error_type=type(error).__name__,
        )

        return TrialResult(
            trial=trial,
            transcript=Transcript(trial_id=trial_id),
            outcome=Outcome(trial_id=trial_id),
            error=str(error),
            error_type=type(error).__name__,
        )


async def run_task(
    task: Task,
    graders: list[Any],
    run_id: str,
    k: int = 5,
    parallel: bool = True,
    config: RunnerConfig | None = None,
) -> TaskResult:
    """
    Task 실행 헬퍼 함수

    Args:
        task: 실행할 Task
        graders: 채점기 목록
        run_id: Run ID
        k: Trial 횟수
        parallel: 병렬 실행 여부
        config: Runner 설정

    Returns:
        TaskResult
    """
    runner = TaskRunner(
        task=task,
        graders=graders,
        run_id=run_id,
        config=config,
    )

    return await runner.run_task(k=k, parallel=parallel)
