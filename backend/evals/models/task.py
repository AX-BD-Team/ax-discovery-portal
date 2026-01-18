"""
Task 정의 모델

YAML 파일에서 로드되는 Task 전체 구조
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from backend.evals.models.entities import Task

from backend.evals.models.configs import (
    AgentConfig,
    CostBudget,
    EnvironmentConfig,
    GraderConfig,
    MetricConfig,
    ReferenceSolution,
    ScoringConfig,
    SuccessCriteria,
    TaskInputs,
    TaskMetadata,
    TimeoutConfig,
    TrialConfig,
)
from backend.evals.models.enums import TaskType


class TaskDefinitionInner(BaseModel):
    """
    Task 정의 내부 구조

    YAML의 `task:` 아래 내용
    """

    # 필수 필드
    id: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9_-]+$",
        description="Task 고유 ID",
    )
    type: TaskType = Field(..., description="Task 유형")
    desc: str = Field(..., max_length=500, description="Task 설명")
    suite: str = Field(..., description="소속 Suite ID")

    # 선택 필드
    version: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$", description="버전")

    # 메타데이터
    metadata: TaskMetadata | None = Field(None, description="메타데이터")

    # 입력/기준
    inputs: TaskInputs | None = Field(None, description="입력 설정")
    success_criteria: SuccessCriteria | None = Field(None, description="성공 기준")
    reference_solution: ReferenceSolution | None = Field(None, description="레퍼런스 솔루션")

    # 실행 설정
    trials: TrialConfig | None = Field(None, description="트라이얼 설정")
    environment: EnvironmentConfig | None = Field(None, description="환경 설정")
    agent: AgentConfig | None = Field(None, description="에이전트 설정")

    # 채점
    graders: list[GraderConfig] = Field(..., min_length=1, description="채점기 목록")
    tracked_metrics: list[MetricConfig] = Field(default_factory=list, description="추적 메트릭")
    scoring: ScoringConfig = Field(..., description="채점 설정")

    # 제한
    timeout: TimeoutConfig | None = Field(None, description="타임아웃 설정")
    cost_budget: CostBudget | None = Field(None, description="비용 예산")

    # 태그
    tags: list[str] = Field(default_factory=list, description="분류 태그")

    @model_validator(mode="after")
    def validate_inputs(self) -> TaskDefinitionInner:
        """입력 검증"""
        if self.inputs:
            # prompt와 prompt_file 중 하나만 있어야 함
            if self.inputs.prompt and self.inputs.prompt_file:
                raise ValueError("prompt와 prompt_file은 동시에 지정할 수 없습니다")
            if not self.inputs.prompt and not self.inputs.prompt_file:
                # 컨텍스트만 있어도 허용
                pass
        return self

    @model_validator(mode="after")
    def validate_graders(self) -> TaskDefinitionInner:
        """채점기 검증"""
        grader_ids = [g.id for g in self.graders if g.id]
        if len(grader_ids) != len(set(grader_ids)):
            raise ValueError("채점기 ID가 중복됩니다")

        # 가중치 합 검증 (weighted 모드)
        if self.scoring.mode.value == "weighted":
            total_weight = sum(g.weight for g in self.graders if g.enabled)
            if abs(total_weight - 1.0) > 0.01:
                # 경고만 하고 자동 정규화
                pass

        # 필수 채점기 검증
        if self.scoring.required_graders:
            for required_id in self.scoring.required_graders:
                if required_id not in grader_ids:
                    raise ValueError(f"필수 채점기 '{required_id}'가 정의되지 않았습니다")

        return self


class TaskDefinition(BaseModel):
    """
    Task 정의 (YAML 루트)

    YAML 파일 전체 구조
    """

    task: TaskDefinitionInner = Field(..., description="Task 정의")

    def get_task_id(self) -> str:
        """Task ID 반환"""
        return self.task.id

    def get_suite_id(self) -> str:
        """Suite ID 반환"""
        return self.task.suite

    def get_grader_ids(self) -> list[str]:
        """채점기 ID 목록 반환"""
        return [g.id or f"grader_{i}" for i, g in enumerate(self.task.graders)]

    def get_trial_count(self) -> int:
        """트라이얼 횟수 반환"""
        return self.task.trials.k if self.task.trials else 5

    def get_timeout_seconds(self) -> int:
        """타임아웃(초) 반환"""
        return self.task.timeout.total_seconds if self.task.timeout else 300

    def get_cost_budget_usd(self) -> float | None:
        """비용 예산(USD) 반환"""
        return self.task.cost_budget.max_usd if self.task.cost_budget else None

    def to_task_entity(self) -> Task:
        """DB 저장용 Task 엔터티로 변환"""
        from backend.evals.models.entities import Task

        t = self.task
        return Task(
            task_id=t.id,
            suite_id=t.suite,
            type=t.type,
            description=t.desc,
            version=t.version,
            domain=t.metadata.domain.value if t.metadata and t.metadata.domain else None,
            difficulty=t.metadata.difficulty.value if t.metadata else "medium",
            risk=t.metadata.risk.value if t.metadata else "low",
            purpose=t.metadata.purpose.value if t.metadata and t.metadata.purpose else None,
            expected_pass_rate=t.metadata.expected_pass_rate if t.metadata else None,
            owner=t.metadata.owner if t.metadata else None,
            tags=t.tags,
            inputs=t.inputs.model_dump() if t.inputs else {},
            success_criteria=t.success_criteria.model_dump() if t.success_criteria else {},
            trial_config=t.trials.model_dump() if t.trials else {},
            environment=t.environment.model_dump() if t.environment else {},
            agent_config=t.agent.model_dump() if t.agent else {},
            graders=[g.model_dump() for g in t.graders],
            scoring=t.scoring.model_dump(),
        )
