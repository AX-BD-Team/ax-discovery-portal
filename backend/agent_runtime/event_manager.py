"""
Session Event Manager

세션별 이벤트 발행/구독 관리
AG-UI 프로토콜 기반 실시간 이벤트 스트리밍 지원
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import structlog

from .event_types import (
    AgentEvent,
    ApprovalRequestedEvent,
    BaseAgentEvent,
    ImpactLevel,
    RenderSurfaceEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StepErrorEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageContentEvent,
)

logger = structlog.get_logger()


class SessionEventManager:
    """세션별 이벤트 관리자"""

    _instances: dict[str, "SessionEventManager"] = {}

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self.history: list[dict[str, Any]] = []
        self.logger = logger.bind(session_id=session_id)
        self._closed = False

    @classmethod
    def get_or_create(cls, session_id: str) -> "SessionEventManager":
        """세션 이벤트 매니저 가져오기 또는 생성"""
        if session_id not in cls._instances:
            cls._instances[session_id] = cls(session_id)
        return cls._instances[session_id]

    @classmethod
    def remove(cls, session_id: str) -> None:
        """세션 이벤트 매니저 제거"""
        if session_id in cls._instances:
            instance = cls._instances[session_id]
            instance.close()
            del cls._instances[session_id]

    def close(self) -> None:
        """이벤트 매니저 종료"""
        self._closed = True
        # 모든 구독자에게 종료 신호 전송
        for queue in self.subscribers:
            try:
                queue.put_nowait({"type": "__CLOSE__"})
            except asyncio.QueueFull:
                pass

    async def publish(self, event: AgentEvent | BaseAgentEvent | dict[str, Any]) -> None:
        """이벤트 발행

        Args:
            event: 이벤트 객체 또는 dict
                - BaseAgentEvent/AgentEvent: to_dict() 호출하여 변환
                - dict: 그대로 사용 (테스트 또는 레거시 호환용)
        """
        if self._closed:
            return

        # dict인 경우 그대로 사용, 아니면 to_dict() 호출
        event_dict = event if isinstance(event, dict) else event.to_dict()

        self.history.append(event_dict)
        self.logger.debug("Event published", event_type=event_dict.get("type"))

        # 모든 구독자에게 이벤트 전달
        for queue in self.subscribers:
            try:
                await queue.put(event_dict)
            except asyncio.QueueFull:
                self.logger.warning("Queue full, dropping event")

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """이벤트 구독"""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self.subscribers.append(queue)
        self.logger.info("New subscriber added", total_subscribers=len(self.subscribers))
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """구독 해제"""
        if queue in self.subscribers:
            self.subscribers.remove(queue)
            self.logger.info("Subscriber removed", total_subscribers=len(self.subscribers))

    async def stream(
        self, queue: asyncio.Queue[dict[str, Any]]
    ) -> AsyncGenerator[dict[str, Any], None]:
        """이벤트 스트림 생성기"""
        try:
            while not self._closed:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # 종료 신호 확인
                    if event.get("type") == "__CLOSE__":
                        break

                    yield event

                    # 실행 완료/오류 시 스트림 종료
                    if event.get("type") in ("RUN_FINISHED", "RUN_ERROR"):
                        break

                except TimeoutError:
                    # 주기적으로 keep-alive 이벤트 발송 (SSE 연결 유지)
                    yield {"type": "KEEP_ALIVE", "timestamp": datetime.now(UTC).isoformat() + "Z"}

        finally:
            self.unsubscribe(queue)

    def get_history(self) -> list[dict[str, Any]]:
        """이벤트 히스토리 조회"""
        return self.history.copy()


class WorkflowEventEmitter:
    """워크플로 이벤트 발행기

    워크플로 실행 중 이벤트 발행을 쉽게 하기 위한 헬퍼 클래스
    """

    def __init__(self, event_manager: SessionEventManager, run_id: str):
        self.event_manager = event_manager
        self.run_id = run_id
        self.session_id = event_manager.session_id
        self._step_start_times: dict[str, datetime] = {}
        self._run_start_time: datetime | None = None

    async def emit_run_started(
        self,
        workflow_id: str,
        input_data: dict[str, Any],
        steps: list[dict[str, str]],
    ) -> None:
        """실행 시작 이벤트 발행"""
        self._run_start_time = datetime.now(UTC)
        event = RunStartedEvent(
            run_id=self.run_id,
            session_id=self.session_id,
            workflow_id=workflow_id,
            input_data=input_data,
            total_steps=len(steps),
            steps=steps,
        )
        await self.event_manager.publish(event)

    async def emit_run_finished(self, result: dict[str, Any]) -> None:
        """실행 완료 이벤트 발행"""
        duration_ms = 0
        if self._run_start_time:
            duration_ms = int((datetime.now(UTC) - self._run_start_time).total_seconds() * 1000)

        event = RunFinishedEvent(
            run_id=self.run_id,
            session_id=self.session_id,
            result=result,
            duration_ms=duration_ms,
        )
        await self.event_manager.publish(event)

    async def emit_run_error(
        self, error: str, error_code: str | None = None, recoverable: bool = False
    ) -> None:
        """실행 오류 이벤트 발행"""
        event = RunErrorEvent(
            run_id=self.run_id,
            session_id=self.session_id,
            error=error,
            error_code=error_code,
            recoverable=recoverable,
        )
        await self.event_manager.publish(event)

    async def emit_step_started(
        self,
        step_id: str,
        step_index: int,
        step_label: str,
        message: str | None = None,
    ) -> None:
        """단계 시작 이벤트 발행"""
        self._step_start_times[step_id] = datetime.now(UTC)
        event = StepStartedEvent(
            run_id=self.run_id,
            session_id=self.session_id,
            step_id=step_id,
            step_index=step_index,
            step_label=step_label,
            message=message,
        )
        await self.event_manager.publish(event)

    async def emit_step_finished(
        self, step_id: str, step_index: int, result: dict[str, Any] | None = None
    ) -> None:
        """단계 완료 이벤트 발행"""
        duration_ms = 0
        if step_id in self._step_start_times:
            duration_ms = int(
                (datetime.now(UTC) - self._step_start_times[step_id]).total_seconds() * 1000
            )

        event = StepFinishedEvent(
            run_id=self.run_id,
            session_id=self.session_id,
            step_id=step_id,
            step_index=step_index,
            duration_ms=duration_ms,
            result=result,
        )
        await self.event_manager.publish(event)

    async def emit_step_error(
        self, step_id: str, step_index: int, error: str, recoverable: bool = False
    ) -> None:
        """단계 오류 이벤트 발행"""
        event = StepErrorEvent(
            run_id=self.run_id,
            session_id=self.session_id,
            step_id=step_id,
            step_index=step_index,
            error=error,
            recoverable=recoverable,
        )
        await self.event_manager.publish(event)

    async def emit_text_message(
        self, message_id: str, content: str, is_complete: bool = True
    ) -> None:
        """텍스트 메시지 이벤트 발행"""
        event = TextMessageContentEvent(
            run_id=self.run_id,
            session_id=self.session_id,
            message_id=message_id,
            content=content,
            is_complete=is_complete,
        )
        await self.event_manager.publish(event)

    async def emit_surface(self, surface_id: str, surface: dict[str, Any]) -> None:
        """Surface 렌더링 이벤트 발행"""
        event = RenderSurfaceEvent(
            run_id=self.run_id,
            session_id=self.session_id,
            surface_id=surface_id,
            surface=surface,
        )
        await self.event_manager.publish(event)

    async def emit_approval_request(
        self,
        approval_id: str,
        title: str,
        description: str,
        impact: ImpactLevel = ImpactLevel.LOW,
        changes: list[dict[str, Any]] | None = None,
        timeout: int | None = None,
    ) -> None:
        """승인 요청 이벤트 발행"""
        event = ApprovalRequestedEvent(
            run_id=self.run_id,
            session_id=self.session_id,
            approval_id=approval_id,
            title=title,
            description=description,
            impact=impact,
            changes=changes or [],
            timeout=timeout,
        )
        await self.event_manager.publish(event)


def generate_run_id() -> str:
    """실행 ID 생성"""
    return f"run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"


def generate_session_id(workflow_id: str) -> str:
    """세션 ID 생성"""
    return f"sess-{workflow_id}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
