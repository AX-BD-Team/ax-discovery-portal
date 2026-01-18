"""
Trial 실행기

단일 Trial 실행을 담당하는 Executor
"""

import asyncio
import builtins
import uuid
from datetime import datetime
from typing import Any

import structlog

from backend.evals.models.configs import (
    AgentConfig,
    EnvironmentConfig,
    TimeoutConfig,
)
from backend.evals.models.entities import (
    GraderResult,
    Outcome,
    Task,
    Transcript,
    Trial,
)
from backend.evals.models.enums import ResetMode, TrialStatus
from backend.evals.runners.base import (
    RunnerConfig,
    RunnerError,
    TimeoutError,
)
from backend.evals.runners.results import TrialResult

logger = structlog.get_logger()


class TrialExecutor:
    """
    단일 Trial 실행

    1. 환경 설정 (sandbox, reset)
    2. 에이전트 실행 (prompt -> response)
    3. Transcript 기록
    4. Outcome 캡처
    5. Trial 결과 반환
    """

    def __init__(
        self,
        run_id: str,
        config: RunnerConfig | None = None,
    ):
        self.run_id = run_id
        self.config = config or RunnerConfig()
        self.logger = logger.bind(component="trial_executor", run_id=run_id)

    async def execute(
        self,
        task: Task,
        trial_index: int,
        seed: int | None = None,
    ) -> TrialResult:
        """
        Trial 실행

        Args:
            task: 실행할 Task
            trial_index: Trial 인덱스 (0부터)
            seed: 랜덤 시드 (재현성)

        Returns:
            TrialResult: 실행 결과
        """
        trial_id = f"trial_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now()

        self.logger.info(
            "Trial 실행 시작",
            trial_id=trial_id,
            task_id=task.task_id,
            trial_index=trial_index,
            seed=seed,
        )

        # Trial 엔터티 생성
        trial = Trial(
            trial_id=trial_id,
            run_id=self.run_id,
            task_id=task.task_id,
            trial_index=trial_index,
            seed=seed,
            status=TrialStatus.RUNNING,
            started_at=started_at,
        )

        # Transcript 초기화
        transcript = Transcript(trial_id=trial_id)

        # Outcome 초기화
        outcome = Outcome(trial_id=trial_id)

        try:
            # 1. 환경 설정
            env_config = self._parse_environment_config(task.environment)
            await self._setup_environment(env_config, trial)

            # 2. 에이전트 설정
            agent_config = self._parse_agent_config(task.agent_config)
            timeout_config = self._get_timeout_config(task)

            # 3. 프롬프트 준비
            prompt = self._prepare_prompt(task)

            # 4. 에이전트 실행 (타임아웃 적용)
            try:
                agent_result = await asyncio.wait_for(
                    self._run_agent(prompt, agent_config, transcript),
                    timeout=timeout_config.total_seconds,
                )
            except builtins.TimeoutError as err:
                raise TimeoutError(
                    f"Trial 타임아웃: {timeout_config.total_seconds}초 초과",
                    duration_seconds=timeout_config.total_seconds,
                ) from err

            # 5. Outcome 캡처
            outcome = await self._capture_outcome(trial_id, agent_result)

            # 6. Trial 완료 처리
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            trial.status = TrialStatus.COMPLETED
            trial.completed_at = completed_at
            trial.duration_seconds = duration
            trial.cost_usd = agent_result.get("cost_usd", 0.0)
            trial.total_tokens = agent_result.get("total_tokens", 0)
            trial.input_tokens = agent_result.get("input_tokens", 0)
            trial.output_tokens = agent_result.get("output_tokens", 0)

            self.logger.info(
                "Trial 실행 완료",
                trial_id=trial_id,
                duration_seconds=duration,
                cost_usd=trial.cost_usd,
            )

            return TrialResult(
                trial=trial,
                transcript=transcript,
                outcome=outcome,
            )

        except TimeoutError as e:
            return self._handle_error(
                trial,
                transcript,
                outcome,
                started_at,
                error=str(e),
                error_type="timeout",
                status=TrialStatus.TIMEOUT,
            )

        except RunnerError as e:
            return self._handle_error(
                trial,
                transcript,
                outcome,
                started_at,
                error=str(e),
                error_type="runner_error",
                status=TrialStatus.FAILED,
            )

        except Exception as e:
            self.logger.exception("Trial 실행 중 예외 발생", trial_id=trial_id)
            return self._handle_error(
                trial,
                transcript,
                outcome,
                started_at,
                error=str(e),
                error_type=type(e).__name__,
                status=TrialStatus.FAILED,
            )

    def _handle_error(
        self,
        trial: Trial,
        transcript: Transcript,
        outcome: Outcome,
        started_at: datetime,
        error: str,
        error_type: str,
        status: TrialStatus,
    ) -> TrialResult:
        """에러 처리 및 결과 반환"""
        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        trial.status = status
        trial.completed_at = completed_at
        trial.duration_seconds = duration
        trial.error_message = error
        trial.error_type = error_type

        self.logger.error(
            "Trial 실행 실패",
            trial_id=trial.trial_id,
            error_type=error_type,
            error=error,
        )

        return TrialResult(
            trial=trial,
            transcript=transcript,
            outcome=outcome,
            error=error,
            error_type=error_type,
        )

    def _parse_environment_config(self, env_dict: dict[str, Any]) -> EnvironmentConfig:
        """환경 설정 파싱"""
        if not env_dict:
            return EnvironmentConfig()

        try:
            return EnvironmentConfig(**env_dict)
        except Exception as e:
            self.logger.warning(f"환경 설정 파싱 실패, 기본값 사용: {e}")
            return EnvironmentConfig()

    def _parse_agent_config(self, agent_dict: dict[str, Any]) -> AgentConfig:
        """에이전트 설정 파싱"""
        if not agent_dict:
            return AgentConfig()

        try:
            return AgentConfig(**agent_dict)
        except Exception as e:
            self.logger.warning(f"에이전트 설정 파싱 실패, 기본값 사용: {e}")
            return AgentConfig()

    def _get_timeout_config(self, task: Task) -> TimeoutConfig:
        """타임아웃 설정 조회"""
        trial_config = task.trial_config or {}
        timeout_dict = trial_config.get("timeout", {})

        if timeout_dict:
            try:
                return TimeoutConfig(**timeout_dict)
            except Exception:
                pass

        # 기본값 (Runner config 기반)
        return TimeoutConfig(
            total_seconds=self.config.trial_timeout,
            per_turn_seconds=60,
            grading_seconds=120,
        )

    def _prepare_prompt(self, task: Task) -> str:
        """프롬프트 준비"""
        inputs = task.inputs or {}

        # 인라인 프롬프트 우선
        prompt = inputs.get("prompt", "")

        # 프롬프트 파일에서 로드 (TODO: 파일 로드 구현)
        if not prompt and inputs.get("prompt_file"):
            prompt_file = inputs["prompt_file"]
            self.logger.debug(f"프롬프트 파일 로드: {prompt_file}")
            # TODO: 파일 로드 구현
            prompt = f"[프롬프트 파일: {prompt_file}]"

        # 컨텍스트 추가
        context = inputs.get("context", {})
        if context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            prompt = f"{prompt}\n\n컨텍스트:\n{context_str}"

        return prompt

    async def _setup_environment(
        self,
        env_config: EnvironmentConfig,
        trial: Trial,
    ) -> None:
        """
        실행 환경 설정

        TODO: 실제 샌드박스/컨테이너 설정 구현
        """
        self.logger.debug(
            "환경 설정",
            sandbox=env_config.sandbox.value,
            reset=env_config.reset.value,
            network=env_config.network.value,
        )

        # 환경 리셋
        if env_config.reset == ResetMode.CLEAN:
            # TODO: 클린 환경 생성
            pass
        elif env_config.reset == ResetMode.SNAPSHOT:
            # TODO: 스냅샷 복원
            trial.env_snapshot_id = f"snapshot_{uuid.uuid4().hex[:8]}"

        # TODO: 샌드박스 설정
        # TODO: 네트워크 설정
        # TODO: 마운트 볼륨 설정

    async def _run_agent(
        self,
        prompt: str,
        agent_config: AgentConfig,
        transcript: Transcript,
    ) -> dict[str, Any]:
        """
        에이전트 실행

        TODO: 실제 에이전트 실행 구현
        현재는 stub으로 구현

        Args:
            prompt: 에이전트에게 전달할 프롬프트
            agent_config: 에이전트 설정
            transcript: Transcript (실행 기록)

        Returns:
            에이전트 실행 결과
        """
        self.logger.debug(
            "에이전트 실행 (stub)",
            adapter=agent_config.adapter.value if hasattr(agent_config, "adapter") else "default",
            model=agent_config.model if hasattr(agent_config, "model") else None,
            prompt_length=len(prompt),
        )

        # TODO: 실제 에이전트 실행 구현
        # from backend.agent_runtime.runner import runtime
        # result = await runtime.run_workflow(...)

        # Stub 응답
        await asyncio.sleep(0.1)  # 시뮬레이션 지연

        # Transcript 기록
        transcript.messages.append(
            {
                "role": "user",
                "content": prompt,
                "timestamp": datetime.now().isoformat(),
            }
        )
        transcript.messages.append(
            {
                "role": "assistant",
                "content": "[Stub 응답] 에이전트 실행이 완료되었습니다.",
                "timestamp": datetime.now().isoformat(),
            }
        )
        transcript.n_turns = 1

        # Stub 결과
        return {
            "success": True,
            "output": "[Stub] 에이전트 실행 완료",
            "cost_usd": 0.001,  # 예상 비용
            "total_tokens": 150,
            "input_tokens": 100,
            "output_tokens": 50,
            "tool_calls": [],
        }

    async def _capture_outcome(
        self,
        trial_id: str,
        agent_result: dict[str, Any],
    ) -> Outcome:
        """
        Outcome 캡처

        에이전트 실행 후 환경 상태 캡처

        TODO: 실제 상태 캡처 구현
        """
        self.logger.debug("Outcome 캡처", trial_id=trial_id)

        outcome = Outcome(trial_id=trial_id)

        # 최종 상태
        outcome.final_state = {
            "agent_output": agent_result.get("output"),
            "success": agent_result.get("success", False),
        }

        # 도구 호출 결과
        tool_calls = agent_result.get("tool_calls", [])
        if tool_calls:
            outcome.api_responses = tool_calls

        # TODO: 파일 시스템 상태 캡처
        # TODO: DB 변경 캡처
        # TODO: 아티팩트 수집

        return outcome


async def execute_trial_with_grading(
    executor: TrialExecutor,
    task: Task,
    trial_index: int,
    graders: list[Any],  # TODO: BaseGrader 타입으로 변경
    seed: int | None = None,
) -> TrialResult:
    """
    Trial 실행 및 채점

    TrialExecutor로 실행 후 채점기로 채점

    Args:
        executor: TrialExecutor 인스턴스
        task: 실행할 Task
        trial_index: Trial 인덱스
        graders: 채점기 목록
        seed: 랜덤 시드

    Returns:
        채점 완료된 TrialResult
    """
    # Trial 실행
    result = await executor.execute(task, trial_index, seed)

    if result.error:
        # 에러 시 채점 스킵
        result.score = 0.0
        result.passed = False
        return result

    # 채점 실행
    grader_results: list[GraderResult] = []
    total_score = 0.0
    total_weight = 0.0
    all_passed = True

    for grader in graders:
        try:
            # TODO: 실제 채점기 실행
            # grader_result = await grader.grade(result.transcript, result.outcome)

            # Stub 채점 결과
            grader_result = GraderResult(
                trial_id=result.trial_id,
                grader_id=f"grader_{len(grader_results)}",
                grader_type="stub",
                score=0.8,
                passed=True,
                explanation="Stub 채점 결과",
            )

            grader_results.append(grader_result)

            # 가중치 기반 점수 계산
            weight = getattr(grader, "weight", 1.0) if grader else 1.0
            total_score += grader_result.score * weight
            total_weight += weight

            if not grader_result.passed:
                all_passed = False

        except Exception as e:
            logger.exception(f"채점기 실행 실패: {e}")
            grader_results.append(
                GraderResult(
                    trial_id=result.trial_id,
                    grader_id=f"grader_{len(grader_results)}",
                    grader_type="error",
                    score=0.0,
                    passed=False,
                    error_message=str(e),
                )
            )
            all_passed = False

    # 최종 점수 계산
    result.grader_results = grader_results
    result.score = total_score / total_weight if total_weight > 0 else 0.0
    result.passed = all_passed

    # Trial 엔터티 업데이트
    result.trial.score = result.score
    result.trial.passed = result.passed
    result.trial.grader_results = [gr.model_dump() for gr in grader_results]

    return result
