"""
Event Manager 단위 테스트

backend/agent_runtime/event_manager.py 테스트
"""

import asyncio

import pytest

from backend.agent_runtime.event_manager import (
    SessionEventManager,
    WorkflowEventEmitter,
    generate_run_id,
    generate_session_id,
)
from backend.agent_runtime.event_types import (
    RunStartedEvent,
    TextMessageContentEvent,
)


class TestSessionEventManager:
    """SessionEventManager 테스트"""

    def setup_method(self):
        """각 테스트 전에 _instances 초기화"""
        SessionEventManager._instances.clear()

    @pytest.mark.asyncio
    async def test_get_or_create_singleton(self):
        """세션별 싱글톤 검증 테스트"""
        # 첫 번째 호출: 새 인스턴스 생성
        manager1 = SessionEventManager.get_or_create("session-1")
        assert manager1 is not None
        assert manager1.session_id == "session-1"

        # 두 번째 호출: 같은 인스턴스 반환
        manager2 = SessionEventManager.get_or_create("session-1")
        assert manager1 is manager2

        # 다른 세션: 다른 인스턴스
        manager3 = SessionEventManager.get_or_create("session-2")
        assert manager1 is not manager3
        assert manager3.session_id == "session-2"

    @pytest.mark.asyncio
    async def test_publish_event(self):
        """이벤트 발행 및 히스토리 저장 테스트"""
        manager = SessionEventManager.get_or_create("session-test")

        # 이벤트 생성
        event = RunStartedEvent(
            run_id="run-001",
            session_id="session-test",
            workflow_id="WF-01",
            input_data={"test": "data"},
            total_steps=3,
            steps=[
                {"id": "step-1", "label": "Step 1"},
                {"id": "step-2", "label": "Step 2"},
                {"id": "step-3", "label": "Step 3"},
            ],
        )

        # 이벤트 발행
        await manager.publish(event)

        # 히스토리 확인 (to_dict()가 camelCase로 변환)
        history = manager.get_history()
        assert len(history) == 1
        assert history[0]["type"] == "RUN_STARTED"
        assert history[0]["runId"] == "run-001"
        assert history[0]["workflowId"] == "WF-01"

    @pytest.mark.asyncio
    async def test_subscribe_and_stream(self):
        """구독 및 큐 수신 테스트"""
        manager = SessionEventManager.get_or_create("session-sub-test")

        # 구독
        queue = manager.subscribe()
        assert queue is not None
        assert len(manager.subscribers) == 1

        # 이벤트 발행
        event = TextMessageContentEvent(
            run_id="run-001",
            session_id="session-sub-test",
            message_id="msg-001",
            content="Test message",
            is_complete=True,
        )
        await manager.publish(event)

        # 큐에서 이벤트 수신
        received_event = await queue.get()
        assert received_event["type"] == "TEXT_MESSAGE_CONTENT"
        assert received_event["content"] == "Test message"

        # 구독 해제
        manager.unsubscribe(queue)
        assert len(manager.subscribers) == 0

    @pytest.mark.asyncio
    async def test_stream_generator_with_close(self):
        """종료 신호 처리 테스트"""
        manager = SessionEventManager.get_or_create("session-stream-test")
        queue = manager.subscribe()

        # 이벤트 스트림 시작
        stream_task = asyncio.create_task(self._collect_stream_events(manager, queue))

        # 이벤트 발행
        await manager.publish(
            TextMessageContentEvent(
                run_id="run-001",
                session_id="session-stream-test",
                message_id="msg-001",
                content="First message",
                is_complete=True,
            )
        )

        # 이벤트가 스트림에서 처리될 시간 확보
        await asyncio.sleep(0.05)

        # 종료 신호 발행
        manager.close()

        # 스트림 종료 대기
        events = await stream_task

        # 검증: 종료 신호 전 이벤트만 수신
        assert len(events) >= 1
        assert events[0]["type"] == "TEXT_MESSAGE_CONTENT"

    async def _collect_stream_events(self, manager, queue):
        """스트림 이벤트 수집 헬퍼"""
        events = []
        async for event in manager.stream(queue):
            if event.get("type") == "__CLOSE__":
                break
            events.append(event)
        return events

    @pytest.mark.asyncio
    async def test_remove_manager(self):
        """매니저 제거 테스트"""
        session_id = "session-remove-test"
        manager = SessionEventManager.get_or_create(session_id)

        assert session_id in SessionEventManager._instances

        # 매니저 제거
        SessionEventManager.remove(session_id)

        # 검증
        assert session_id not in SessionEventManager._instances
        assert manager._closed is True


class TestWorkflowEventEmitter:
    """WorkflowEventEmitter 테스트"""

    def setup_method(self):
        """각 테스트 전에 _instances 초기화"""
        SessionEventManager._instances.clear()

    @pytest.mark.asyncio
    async def test_emit_run_started(self):
        """실행 시작 이벤트 발행 테스트"""
        manager = SessionEventManager.get_or_create("session-emitter-test")
        emitter = WorkflowEventEmitter(manager, "run-001")

        # 실행 시작 이벤트 발행
        await emitter.emit_run_started(
            workflow_id="WF-01",
            input_data={"test": "data"},
            steps=[
                {"id": "step-1", "label": "Extract metadata"},
                {"id": "step-2", "label": "Create activity"},
            ],
        )

        # 히스토리 확인 (to_dict()가 camelCase로 변환)
        history = manager.get_history()
        assert len(history) == 1
        assert history[0]["type"] == "RUN_STARTED"
        assert history[0]["runId"] == "run-001"
        assert history[0]["workflowId"] == "WF-01"
        assert history[0]["totalSteps"] == 2

    @pytest.mark.asyncio
    async def test_emit_step_with_duration(self):
        """단계 duration 측정 테스트"""
        manager = SessionEventManager.get_or_create("session-step-test")
        emitter = WorkflowEventEmitter(manager, "run-002")

        # 단계 시작
        await emitter.emit_step_started(
            step_id="step-1",
            step_index=0,
            step_label="Extract metadata",
            message="Fetching HTML...",
        )

        # 약간의 대기 (duration 측정용)
        await asyncio.sleep(0.01)

        # 단계 완료
        await emitter.emit_step_finished(
            step_id="step-1", step_index=0, result={"status": "success"}
        )

        # 히스토리 확인
        history = manager.get_history()
        assert len(history) == 2

        # 시작 이벤트 (to_dict()가 camelCase로 변환)
        start_event = history[0]
        assert start_event["type"] == "STEP_STARTED"
        assert start_event["stepId"] == "step-1"
        assert start_event["stepLabel"] == "Extract metadata"

        # 완료 이벤트
        finish_event = history[1]
        assert finish_event["type"] == "STEP_FINISHED"
        assert finish_event["stepId"] == "step-1"
        assert finish_event["durationMs"] >= 10  # 최소 10ms

    @pytest.mark.asyncio
    async def test_emit_run_finished_with_duration(self):
        """실행 duration 측정 테스트"""
        manager = SessionEventManager.get_or_create("session-run-duration-test")
        emitter = WorkflowEventEmitter(manager, "run-003")

        # 실행 시작
        await emitter.emit_run_started(workflow_id="WF-01", input_data={}, steps=[])

        # 약간의 대기
        await asyncio.sleep(0.01)

        # 실행 완료
        await emitter.emit_run_finished(result={"status": "success"})

        # 히스토리 확인 (to_dict()가 camelCase로 변환)
        history = manager.get_history()
        finish_event = history[-1]
        assert finish_event["type"] == "RUN_FINISHED"
        assert finish_event["durationMs"] >= 10

    @pytest.mark.asyncio
    async def test_emit_text_message(self):
        """텍스트 메시지 이벤트 발행 테스트"""
        manager = SessionEventManager.get_or_create("session-message-test")
        emitter = WorkflowEventEmitter(manager, "run-004")

        # 텍스트 메시지 발행
        await emitter.emit_text_message(
            message_id="msg-001",
            content="Processing seminar data...",
            is_complete=True,
        )

        # 히스토리 확인 (to_dict()가 camelCase로 변환)
        history = manager.get_history()
        assert len(history) == 1
        message_event = history[0]
        assert message_event["type"] == "TEXT_MESSAGE_CONTENT"
        assert message_event["messageId"] == "msg-001"
        assert message_event["content"] == "Processing seminar data..."
        assert message_event["isComplete"] is True


class TestHelperFunctions:
    """ID 생성 헬퍼 함수 테스트"""

    def test_generate_run_id_format(self):
        """run_id 형식 검증 테스트"""
        run_id = generate_run_id()

        # 형식 검증: run-YYYYMMDDHHMMSSffffff
        assert run_id.startswith("run-")
        assert len(run_id) == len("run-20260114123456789012")

        # 두 번 호출 시 다른 ID 생성
        run_id2 = generate_run_id()
        assert run_id != run_id2

    def test_generate_session_id_format(self):
        """session_id 형식 검증 테스트"""
        session_id = generate_session_id("WF-01")

        # 형식 검증: sess-{workflow_id}-YYYYMMDDHHMMSSffffff
        assert session_id.startswith("sess-WF-01-")
        assert len(session_id) >= len("sess-WF-01-20260114123456789012")

        # 두 번 호출 시 다른 ID 생성
        session_id2 = generate_session_id("WF-01")
        assert session_id != session_id2

    def test_generate_session_id_with_different_workflows(self):
        """다른 워크플로 ID로 세션 ID 생성 테스트"""
        session_id_wf01 = generate_session_id("WF-01")
        session_id_wf02 = generate_session_id("WF-02")

        assert "WF-01" in session_id_wf01
        assert "WF-02" in session_id_wf02
        assert session_id_wf01 != session_id_wf02
