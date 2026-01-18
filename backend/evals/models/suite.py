"""
Suite 정의 모델

YAML 파일에서 로드되는 Suite 전체 구조
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from backend.evals.models.enums import NotificationChannel, SuitePurpose

if TYPE_CHECKING:
    from backend.evals.models.entities import Suite


# ============================================================================
# Suite 기본 설정
# ============================================================================


class SuiteDefaults(BaseModel):
    """Suite 레벨 기본값 (Task에서 오버라이드 가능)"""

    trials: dict[str, int | bool] | None = Field(None, description="트라이얼 설정")
    environment: dict[str, str] | None = Field(None, description="환경 설정")
    agent: dict[str, str | int] | None = Field(None, description="에이전트 설정")
    timeout: dict[str, int] | None = Field(None, description="타임아웃 설정")
    cost_budget: dict[str, int | float] | None = Field(None, description="비용 예산")


# ============================================================================
# 스케줄 설정
# ============================================================================


class ScheduleConfig(BaseModel):
    """실행 스케줄 설정"""

    enabled: bool = Field(True, description="스케줄 활성화")
    cron: str | None = Field(None, description="Cron 표현식")
    on_commit: bool = Field(False, description="커밋마다 실행")
    on_pr: bool = Field(True, description="PR마다 실행")
    branches: list[str] = Field(
        default_factory=lambda: ["main", "develop"],
        description="대상 브랜치",
    )


# ============================================================================
# 게이트 설정
# ============================================================================


class PassCriteria(BaseModel):
    """통과 기준"""

    min_pass_rate: float = Field(0.95, ge=0, le=1, description="최소 통과율")
    required_tasks: list[str] = Field(default_factory=list, description="필수 통과 Task ID")
    max_regression_count: int = Field(0, ge=0, description="허용 회귀 개수")


class GateExceptions(BaseModel):
    """게이트 예외 설정"""

    allow_skip_with_approval: bool = Field(False, description="승인 시 스킵 허용")
    approvers: list[str] = Field(default_factory=list, description="승인자 목록")


class GateConfig(BaseModel):
    """배포 게이트 설정"""

    enabled: bool = Field(True, description="게이트 활성화")
    blocking: bool = Field(True, description="실패 시 배포 차단")
    pass_criteria: PassCriteria = Field(
        default_factory=PassCriteria,
        description="통과 기준",  # type: ignore[arg-type]
    )
    exceptions: GateExceptions = Field(
        default_factory=GateExceptions,
        description="예외 설정",  # type: ignore[arg-type]
    )


# ============================================================================
# 알림 설정
# ============================================================================


class NotificationTarget(BaseModel):
    """알림 대상"""

    type: NotificationChannel = Field(..., description="채널 유형")
    target: str = Field(..., description="대상 (채널명, 이메일 등)")


class NotificationEvent(BaseModel):
    """알림 이벤트 설정"""

    enabled: bool = Field(True, description="활성화")
    channels: list[NotificationTarget] = Field(default_factory=list, description="알림 채널")


class SaturationNotification(BaseModel):
    """포화 알림 설정"""

    enabled: bool = Field(True, description="활성화")
    threshold: float = Field(0.98, ge=0, le=1, description="포화 임계값")
    channels: list[NotificationTarget] = Field(default_factory=list)


class DailyDigestNotification(BaseModel):
    """일일 다이제스트 설정"""

    enabled: bool = Field(False, description="활성화")
    time: str = Field("09:00", description="발송 시간 (HH:MM)")
    timezone: str = Field("Asia/Seoul", description="시간대")
    channels: list[NotificationTarget] = Field(default_factory=list)


class NotificationConfig(BaseModel):
    """알림 설정"""

    on_failure: NotificationEvent = Field(
        default_factory=NotificationEvent,
        description="실패 시 알림",  # type: ignore[arg-type]
    )
    on_regression: NotificationEvent = Field(
        default_factory=NotificationEvent,
        description="회귀 시 알림",  # type: ignore[arg-type]
    )
    on_saturation: SaturationNotification = Field(
        default_factory=SaturationNotification,
        description="포화 시 알림",  # type: ignore[arg-type]
    )
    daily_digest: DailyDigestNotification = Field(
        default_factory=DailyDigestNotification,
        description="일일 다이제스트",  # type: ignore[arg-type]
    )


# ============================================================================
# Task 참조
# ============================================================================


class TaskReference(BaseModel):
    """Task 참조 (경로 기반)"""

    path: str = Field(..., description="Task YAML 파일 경로")
    enabled: bool = Field(True, description="활성화 여부")
    override: dict | None = Field(None, description="Task 설정 오버라이드")


# ============================================================================
# Suite 정의
# ============================================================================


class SuiteDefinitionInner(BaseModel):
    """
    Suite 정의 내부 구조

    YAML의 `suite:` 아래 내용
    """

    # 필수 필드
    id: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-z0-9_-]+$",
        description="Suite 고유 ID",
    )
    name: str = Field(..., max_length=100, description="Suite 이름")
    purpose: SuitePurpose = Field(..., description="목적")
    tasks: list[str | TaskReference] = Field(..., min_length=1, description="Task 목록")

    # 선택 필드
    description: str | None = Field(None, max_length=500, description="설명")
    version: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$", description="버전")
    domain: str | None = Field(None, description="도메인 분류")
    owner_team: str | None = Field(None, description="담당 팀")

    # 설정
    defaults: SuiteDefaults | None = Field(None, description="기본 설정")
    schedule: ScheduleConfig | None = Field(None, description="스케줄 설정")
    gates: GateConfig | None = Field(None, description="게이트 설정")
    notifications: NotificationConfig | None = Field(None, description="알림 설정")

    # 태그
    tags: list[str] = Field(default_factory=list, description="분류 태그")

    def get_task_paths(self) -> list[str]:
        """Task 경로 목록 반환"""
        paths = []
        for task in self.tasks:
            if isinstance(task, str):
                # Task ID만 있는 경우 - 경로 추론 필요
                paths.append(task)
            else:
                paths.append(task.path)
        return paths

    def get_enabled_task_paths(self) -> list[str]:
        """활성화된 Task 경로 목록 반환"""
        paths = []
        for task in self.tasks:
            if isinstance(task, str):
                paths.append(task)
            elif task.enabled:
                paths.append(task.path)
        return paths


class SuiteDefinition(BaseModel):
    """
    Suite 정의 (YAML 루트)

    YAML 파일 전체 구조
    """

    suite: SuiteDefinitionInner = Field(..., description="Suite 정의")

    def get_suite_id(self) -> str:
        """Suite ID 반환"""
        return self.suite.id

    def get_task_count(self) -> int:
        """Task 수 반환"""
        return len(self.suite.tasks)

    def is_regression(self) -> bool:
        """회귀 테스트 Suite인지 확인"""
        return self.suite.purpose == SuitePurpose.REGRESSION

    def is_gate_enabled(self) -> bool:
        """게이트가 활성화되었는지 확인"""
        return self.suite.gates.enabled if self.suite.gates else False

    def get_min_pass_rate(self) -> float:
        """최소 통과율 반환"""
        if self.suite.gates and self.suite.gates.pass_criteria:
            return self.suite.gates.pass_criteria.min_pass_rate
        return 0.95

    def to_suite_entity(self) -> Suite:
        """DB 저장용 Suite 엔터티로 변환"""
        from backend.evals.models.entities import Suite

        s = self.suite
        return Suite(
            suite_id=s.id,
            name=s.name,
            description=s.description,
            version=s.version,
            purpose=s.purpose,
            domain=s.domain,
            owner_team=s.owner_team,
            tags=s.tags,
        )
