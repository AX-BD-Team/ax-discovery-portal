"""
AG-UI (Agent-User Interaction) Event Types

AG-UI 프로토콜 기반 이벤트 타입 정의 (Python)
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AgentEventType(str, Enum):
    """이벤트 타입 열거형"""

    # 실행 제어
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"
    # 단계 진행
    STEP_STARTED = "STEP_STARTED"
    STEP_FINISHED = "STEP_FINISHED"
    STEP_ERROR = "STEP_ERROR"
    # 메시지 스트리밍
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"
    # 도구 호출
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"
    # 상태 동기화
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    STATE_DELTA = "STATE_DELTA"
    # 사용자 개입
    ACTION_REQUIRED = "ACTION_REQUIRED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    # A2UI Surface
    RENDER_SURFACE = "RENDER_SURFACE"


class RunStatus(str, Enum):
    """실행 상태"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    PAUSED = "paused"


class StepStatus(str, Enum):
    """단계 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"


class ImpactLevel(str, Enum):
    """위험도 수준"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SeminarPipelineStep(str, Enum):
    """WF-01 세미나 파이프라인 단계"""

    METADATA_EXTRACTION = "METADATA_EXTRACTION"
    ACTIVITY_CREATION = "ACTIVITY_CREATION"
    AAR_TEMPLATE_GENERATION = "AAR_TEMPLATE_GENERATION"
    CONFLUENCE_UPDATE = "CONFLUENCE_UPDATE"
    SIGNAL_INITIALIZATION = "SIGNAL_INITIALIZATION"


@dataclass
class StepInfo:
    """단계 정보"""

    id: str
    label: str
    status: StepStatus = StepStatus.PENDING
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    error: str | None = None


@dataclass
class BaseAgentEvent:
    """기본 이벤트"""

    type: AgentEventType = field(default=AgentEventType.RUN_STARTED)
    run_id: str = ""
    session_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리 변환"""
        result: dict[str, Any] = {
            "type": self.type.value,
            "runId": self.run_id,
            "sessionId": self.session_id,
            "timestamp": self.timestamp,
        }
        # 하위 클래스 필드 추가
        for key, value in self.__dict__.items():
            if key not in ("type", "run_id", "session_id", "timestamp"):
                # snake_case -> camelCase 변환
                camel_key = "".join(
                    word.capitalize() if i > 0 else word for i, word in enumerate(key.split("_"))
                )
                if isinstance(value, Enum):
                    result[camel_key] = value.value
                elif hasattr(value, "to_dict"):
                    result[camel_key] = value.to_dict()
                elif isinstance(value, list):
                    result[camel_key] = [
                        item.to_dict() if hasattr(item, "to_dict") else item for item in value
                    ]
                else:
                    result[camel_key] = value
        return result


@dataclass
class RunStartedEvent(BaseAgentEvent):
    """실행 시작 이벤트"""

    type: AgentEventType = field(default=AgentEventType.RUN_STARTED)
    workflow_id: str = ""
    input_data: dict[str, Any] = field(default_factory=dict)
    total_steps: int = 0
    steps: list[dict[str, str]] = field(default_factory=list)


@dataclass
class RunFinishedEvent(BaseAgentEvent):
    """실행 완료 이벤트"""

    type: AgentEventType = field(default=AgentEventType.RUN_FINISHED)
    result: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0


@dataclass
class RunErrorEvent(BaseAgentEvent):
    """실행 오류 이벤트"""

    type: AgentEventType = field(default=AgentEventType.RUN_ERROR)
    error: str = ""
    error_code: str | None = None
    recoverable: bool = False


@dataclass
class StepStartedEvent(BaseAgentEvent):
    """단계 시작 이벤트"""

    type: AgentEventType = field(default=AgentEventType.STEP_STARTED)
    step_id: str = ""
    step_index: int = 0
    step_label: str = ""
    message: str | None = None


@dataclass
class StepFinishedEvent(BaseAgentEvent):
    """단계 완료 이벤트"""

    type: AgentEventType = field(default=AgentEventType.STEP_FINISHED)
    step_id: str = ""
    step_index: int = 0
    duration_ms: int = 0
    result: dict[str, Any] | None = None


@dataclass
class StepErrorEvent(BaseAgentEvent):
    """단계 오류 이벤트"""

    type: AgentEventType = field(default=AgentEventType.STEP_ERROR)
    step_id: str = ""
    step_index: int = 0
    error: str = ""
    recoverable: bool = False


@dataclass
class TextMessageContentEvent(BaseAgentEvent):
    """텍스트 메시지 내용 이벤트"""

    type: AgentEventType = field(default=AgentEventType.TEXT_MESSAGE_CONTENT)
    message_id: str = ""
    content: str = ""
    is_complete: bool = False


@dataclass
class RenderSurfaceEvent(BaseAgentEvent):
    """Surface 렌더링 이벤트"""

    type: AgentEventType = field(default=AgentEventType.RENDER_SURFACE)
    surface_id: str = ""
    surface: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalRequestedEvent(BaseAgentEvent):
    """승인 요청 이벤트"""

    type: AgentEventType = field(default=AgentEventType.APPROVAL_REQUESTED)
    approval_id: str = ""
    title: str = ""
    description: str = ""
    impact: ImpactLevel = ImpactLevel.LOW
    changes: list[dict[str, Any]] = field(default_factory=list)
    timeout: int | None = None


# 이벤트 유니온 타입 (타입 힌트용)
AgentEvent = (
    RunStartedEvent
    | RunFinishedEvent
    | RunErrorEvent
    | StepStartedEvent
    | StepFinishedEvent
    | StepErrorEvent
    | TextMessageContentEvent
    | RenderSurfaceEvent
    | ApprovalRequestedEvent
)
