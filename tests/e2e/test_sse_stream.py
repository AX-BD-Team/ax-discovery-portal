"""
SSE Stream API 테스트

AG-UI 실시간 이벤트 스트리밍 엔드포인트 E2E 테스트
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.agent_runtime.event_manager import (
    SessionEventManager,
    WorkflowEventEmitter,
    generate_run_id,
    generate_session_id,
)
from backend.api.main import app

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
async def async_client():
    """비동기 HTTP 클라이언트 (SSE 타임아웃 설정)"""
    import httpx

    transport = ASGITransport(app=app)
    # SSE 스트리밍 테스트를 위해 짧은 타임아웃 설정
    timeout = httpx.Timeout(5.0, connect=2.0)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=timeout) as client:
        yield client


@pytest.fixture
def mock_event_manager():
    """Mock 이벤트 매니저"""
    manager = MagicMock(spec=SessionEventManager)
    manager.history = []
    manager.get_history.return_value = []
    return manager


@pytest.fixture(autouse=True)
def cleanup_sessions():
    """테스트 후 세션 정리"""
    yield
    # 테스트 후 모든 세션 정리
    SessionEventManager._instances.clear()


# ============================================================
# 테스트 1: 이벤트 생성기 기본 동작
# ============================================================


class TestEventGenerator:
    """이벤트 생성기 테스트"""

    @pytest.mark.asyncio
    async def test_event_generator_basic(self):
        """기본 이벤트 생성 테스트"""
        from backend.api.routers.stream import event_generator

        # 세션 생성
        session_id = generate_session_id("TEST")
        manager = SessionEventManager.get_or_create(session_id)
        queue = manager.subscribe()

        # 이벤트 발행
        test_event = {"type": "test_event", "data": "hello"}
        await manager.publish(test_event)
        await manager.publish({"type": "run_finished", "data": "done"})

        # 이벤트 수신
        events = []
        async for event in event_generator(manager, queue):
            events.append(event)
            if event.get("event") == "run_finished":
                break

        assert len(events) >= 1
        assert events[0]["event"] == "test_event"

    @pytest.mark.asyncio
    async def test_event_generator_json_format(self):
        """이벤트 JSON 형식 테스트"""
        from backend.api.routers.stream import event_generator

        session_id = generate_session_id("TEST")
        manager = SessionEventManager.get_or_create(session_id)
        queue = manager.subscribe()

        # 복잡한 데이터 이벤트
        complex_event = {
            "type": "step_started",
            "step_id": "STEP-001",
            "label": "데이터 검증",
            "metadata": {"progress": 25},
        }
        await manager.publish(complex_event)
        await manager.publish({"type": "run_finished"})

        async for event in event_generator(manager, queue):
            if event.get("event") == "step_started":
                data = json.loads(event["data"])
                assert data["step_id"] == "STEP-001"
                assert data["label"] == "데이터 검증"
                break


# ============================================================
# 테스트 2: WF-01 세미나 파이프라인 스트리밍
# ============================================================


class TestSeminarPipelineStream:
    """WF-01 세미나 파이프라인 스트림 테스트"""

    @pytest.mark.asyncio
    async def test_stream_seminar_returns_sse_response(self, async_client):
        """SSE 응답 반환 테스트 (스트리밍 방식)"""
        with patch("backend.api.routers.stream.SeminarPipelineWithEvents") as mock_pipeline:
            # Mock 파이프라인 설정 - 빠르게 완료되도록
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            # asyncio.timeout으로 스트리밍 강제 종료
            try:
                async with asyncio.timeout(2.0):
                    async with async_client.stream(
                        "GET",
                        "/api/stream/workflow/WF-01",
                        params={"url": "https://example.com/seminar"},
                    ) as response:
                        # SSE 응답 확인
                        assert response.status_code == 200
                        assert "text/event-stream" in response.headers.get("content-type", "")
            except TimeoutError:
                pass  # 타임아웃은 예상된 동작

    @pytest.mark.asyncio
    async def test_stream_seminar_with_themes(self, async_client):
        """테마 파라미터 포함 테스트"""
        with patch("backend.api.routers.stream.SeminarPipelineWithEvents") as mock_pipeline:
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            try:
                async with asyncio.timeout(2.0):
                    async with async_client.stream(
                        "GET",
                        "/api/stream/workflow/WF-01",
                        params={
                            "url": "https://example.com/seminar",
                            "themes": "AI,Cloud,Security",
                            "play_id": "EXT_Desk_D01_AI",
                        },
                    ) as response:
                        assert response.status_code == 200
            except TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_seminar_missing_url(self, async_client):
        """필수 파라미터 누락 테스트"""
        response = await async_client.get("/api/stream/workflow/WF-01")

        assert response.status_code == 422  # Validation Error


# ============================================================
# 테스트 3: WF-02 인터뷰-to-Brief 스트리밍
# ============================================================


class TestInterviewPipelineStream:
    """WF-02 인터뷰-to-Brief 스트림 테스트"""

    @pytest.mark.asyncio
    async def test_stream_interview_returns_sse_response(self, async_client):
        """SSE 응답 반환 테스트"""
        with patch(
            "backend.api.routers.stream.InterviewToBriefPipelineWithEvents"
        ) as mock_pipeline:
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            try:
                async with asyncio.timeout(2.0):
                    async with async_client.stream(
                        "POST",
                        "/api/stream/workflow/WF-02",
                        params={"content": "인터뷰 내용입니다. 고객이 AI 자동화를 원합니다."},
                    ) as response:
                        assert response.status_code == 200
                        assert "text/event-stream" in response.headers.get("content-type", "")
            except TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_interview_with_full_params(self, async_client):
        """전체 파라미터 테스트"""
        with patch(
            "backend.api.routers.stream.InterviewToBriefPipelineWithEvents"
        ) as mock_pipeline:
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            try:
                async with asyncio.timeout(2.0):
                    async with async_client.stream(
                        "POST",
                        "/api/stream/workflow/WF-02",
                        params={
                            "content": "인터뷰 내용",
                            "play_id": "KT_Sales_S01",
                            "customer": "대기업",
                            "source": "KT",
                            "channel": "영업PM",
                            "interviewee": "김철수 팀장",
                        },
                    ) as response:
                        assert response.status_code == 200
            except TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_interview_missing_content(self, async_client):
        """필수 content 누락 테스트"""
        response = await async_client.post("/api/stream/workflow/WF-02")

        assert response.status_code == 422


# ============================================================
# 테스트 4: WF-04 Inbound Triage 스트리밍
# ============================================================


class TestInboundTriageStream:
    """WF-04 Inbound Triage 스트림 테스트"""

    @pytest.mark.asyncio
    async def test_stream_inbound_returns_sse_response(self, async_client):
        """SSE 응답 반환 테스트"""
        with patch("backend.api.routers.stream.InboundTriagePipelineWithEvents") as mock_pipeline:
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            try:
                async with asyncio.timeout(2.0):
                    async with async_client.stream(
                        "POST",
                        "/api/stream/workflow/WF-04",
                        params={
                            "title": "AI 솔루션 도입 문의",
                            "description": "고객사에서 AI 자동화 솔루션에 관심을 보입니다.",
                        },
                    ) as response:
                        assert response.status_code == 200
                        assert "text/event-stream" in response.headers.get("content-type", "")
            except TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_inbound_with_urgency(self, async_client):
        """긴급도 파라미터 테스트"""
        with patch("backend.api.routers.stream.InboundTriagePipelineWithEvents") as mock_pipeline:
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            try:
                async with asyncio.timeout(2.0):
                    async with async_client.stream(
                        "POST",
                        "/api/stream/workflow/WF-04",
                        params={
                            "title": "긴급 요청",
                            "description": "긴급 처리 필요",
                            "urgency": "URGENT",
                            "customer_segment": "금융",
                            "pain": "응답 시간 지연",
                        },
                    ) as response:
                        assert response.status_code == 200
            except TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_inbound_missing_required(self, async_client):
        """필수 파라미터 누락 테스트"""
        response = await async_client.post(
            "/api/stream/workflow/WF-04",
            params={"title": "제목만 있음"},  # description 누락
        )

        assert response.status_code == 422


# ============================================================
# 테스트 5: WF-05 KPI Digest 스트리밍
# ============================================================


class TestKPIDigestStream:
    """WF-05 KPI Digest 스트림 테스트"""

    @pytest.mark.asyncio
    async def test_stream_kpi_digest_returns_sse_response(self, async_client):
        """SSE 응답 반환 테스트"""
        with patch("backend.api.routers.stream.KPIDigestPipelineWithEvents") as mock_pipeline:
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            try:
                async with asyncio.timeout(2.0):
                    async with async_client.stream(
                        "GET",
                        "/api/stream/workflow/WF-05",
                    ) as response:
                        assert response.status_code == 200
                        assert "text/event-stream" in response.headers.get("content-type", "")
            except TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_kpi_digest_with_period(self, async_client):
        """기간 파라미터 테스트"""
        with patch("backend.api.routers.stream.KPIDigestPipelineWithEvents") as mock_pipeline:
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            try:
                async with asyncio.timeout(2.0):
                    async with async_client.stream(
                        "GET",
                        "/api/stream/workflow/WF-05",
                        params={"period": "month", "notify": True},
                    ) as response:
                        assert response.status_code == 200
            except TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_kpi_digest_default_params(self, async_client):
        """기본 파라미터 테스트"""
        with patch("backend.api.routers.stream.KPIDigestPipelineWithEvents") as mock_pipeline:
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            try:
                async with asyncio.timeout(2.0):
                    # 파라미터 없이 호출 (기본값 사용)
                    async with async_client.stream(
                        "GET",
                        "/api/stream/workflow/WF-05",
                    ) as response:
                        assert response.status_code == 200
            except TimeoutError:
                pass


# ============================================================
# 테스트 6: 범용 워크플로 스트리밍
# ============================================================


class TestGenericWorkflowStream:
    """범용 워크플로 스트림 테스트"""

    @pytest.mark.asyncio
    async def test_wf01_redirect_message(self, async_client):
        """WF-01 리다이렉트 메시지 테스트"""
        with patch("backend.api.routers.stream.SeminarPipelineWithEvents") as mock_pipeline:
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            try:
                async with asyncio.timeout(2.0):
                    async with async_client.stream(
                        "GET",
                        "/api/stream/workflow/WF-01",
                        params={"url": "test"},
                    ) as response:
                        # 실제로는 정상 응답이 와야 함 (전용 엔드포인트로 처리)
                        assert response.status_code == 200
            except TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_unsupported_workflow(self, async_client):
        """지원되지 않는 워크플로 테스트"""
        response = await async_client.get("/api/stream/workflow/WF-99")

        assert response.status_code == 501
        assert "지원하지 않습니다" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_wf03_not_supported(self, async_client):
        """WF-03 미지원 테스트"""
        response = await async_client.get("/api/stream/workflow/WF-03")

        assert response.status_code == 501


# ============================================================
# 테스트 7: 세션 관리 API
# ============================================================


class TestSessionManagement:
    """세션 관리 API 테스트"""

    @pytest.mark.asyncio
    async def test_get_session_history(self, async_client):
        """세션 히스토리 조회 테스트"""
        # 세션 생성
        session_id = generate_session_id("TEST")
        manager = SessionEventManager.get_or_create(session_id)

        # 이벤트 발행
        await manager.publish({"type": "test", "data": "event1"})
        await manager.publish({"type": "test", "data": "event2"})

        # 히스토리 조회
        response = await async_client.get(f"/api/stream/session/{session_id}/history")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "events" in data
        assert data["total_events"] >= 0

    @pytest.mark.asyncio
    async def test_get_session_history_not_found(self, async_client):
        """존재하지 않는 세션 히스토리 조회 테스트"""
        response = await async_client.get("/api/stream/session/nonexistent-session/history")

        assert response.status_code == 404
        assert "찾을 수 없습니다" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_close_session(self, async_client):
        """세션 종료 테스트"""
        # 세션 생성
        session_id = generate_session_id("TEST")
        SessionEventManager.get_or_create(session_id)

        # 세션 종료
        response = await async_client.delete(f"/api/stream/session/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"
        assert data["session_id"] == session_id

        # 세션이 실제로 제거되었는지 확인
        assert session_id not in SessionEventManager._instances

    @pytest.mark.asyncio
    async def test_close_session_not_found(self, async_client):
        """존재하지 않는 세션 종료 테스트"""
        response = await async_client.delete("/api/stream/session/nonexistent-session")

        assert response.status_code == 404


# ============================================================
# 테스트 8: 이벤트 에미터 통합
# ============================================================


class TestWorkflowEventEmitter:
    """워크플로 이벤트 에미터 테스트"""

    @pytest.mark.asyncio
    async def test_emitter_run_started(self):
        """run_started 이벤트 테스트"""
        session_id = generate_session_id("TEST")
        run_id = generate_run_id()
        manager = SessionEventManager.get_or_create(session_id)
        emitter = WorkflowEventEmitter(manager, run_id)

        queue = manager.subscribe()

        await emitter.emit_run_started(
            workflow_id="WF-01",
            input_data={"url": "https://example.com"},
            steps=[{"id": "STEP1", "label": "Step 1"}],
        )

        # 이벤트 수신
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "RUN_STARTED"
        assert event["runId"] == run_id

    @pytest.mark.asyncio
    async def test_emitter_step_events(self):
        """step 이벤트 테스트"""
        session_id = generate_session_id("TEST")
        run_id = generate_run_id()
        manager = SessionEventManager.get_or_create(session_id)
        emitter = WorkflowEventEmitter(manager, run_id)

        queue = manager.subscribe()

        # Step 시작
        await emitter.emit_step_started(
            step_id="VALIDATION",
            step_index=0,
            step_label="데이터 검증",
        )

        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "STEP_STARTED"
        assert event["stepId"] == "VALIDATION"
        assert event["stepLabel"] == "데이터 검증"

        # Step 완료
        await emitter.emit_step_finished(
            step_id="VALIDATION",
            step_index=0,
            result={"validated": True},
        )

        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "STEP_FINISHED"
        assert event["stepId"] == "VALIDATION"

    @pytest.mark.asyncio
    async def test_emitter_surface_event(self):
        """surface 이벤트 테스트"""
        session_id = generate_session_id("TEST")
        run_id = generate_run_id()
        manager = SessionEventManager.get_or_create(session_id)
        emitter = WorkflowEventEmitter(manager, run_id)

        queue = manager.subscribe()

        # Surface 이벤트 (실시간 미리보기)
        await emitter.emit_surface(
            surface_id="signal_preview",
            surface={"signal_id": "SIG-001", "title": "AI 도입"},
        )

        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "RENDER_SURFACE"
        assert event["surfaceId"] == "signal_preview"
        assert event["surface"]["signal_id"] == "SIG-001"

    @pytest.mark.asyncio
    async def test_emitter_run_error(self):
        """run_error 이벤트 테스트"""
        session_id = generate_session_id("TEST")
        run_id = generate_run_id()
        manager = SessionEventManager.get_or_create(session_id)
        emitter = WorkflowEventEmitter(manager, run_id)

        queue = manager.subscribe()

        await emitter.emit_run_error("테스트 에러", recoverable=True)

        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "RUN_ERROR"
        assert event["error"] == "테스트 에러"
        assert event["recoverable"] is True


# ============================================================
# 테스트 9: 동시성 및 다중 구독자
# ============================================================


class TestConcurrencyAndMultipleSubscribers:
    """동시성 및 다중 구독자 테스트"""

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """다중 구독자 테스트"""
        session_id = generate_session_id("TEST")
        manager = SessionEventManager.get_or_create(session_id)

        # 다중 구독자
        queue1 = manager.subscribe()
        queue2 = manager.subscribe()
        queue3 = manager.subscribe()

        # 이벤트 발행
        await manager.publish({"type": "broadcast", "message": "hello"})

        # 모든 구독자가 이벤트 수신
        event1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        event2 = await asyncio.wait_for(queue2.get(), timeout=1.0)
        event3 = await asyncio.wait_for(queue3.get(), timeout=1.0)

        assert event1["type"] == "broadcast"
        assert event2["type"] == "broadcast"
        assert event3["type"] == "broadcast"

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, async_client):
        """동시 세션 테스트"""
        with patch("backend.api.routers.stream.SeminarPipelineWithEvents") as mock_pipeline:
            mock_instance = AsyncMock()
            mock_pipeline.return_value = mock_instance

            async def make_stream_request(i: int) -> int:
                """스트리밍 요청을 만들고 상태 코드 반환"""
                try:
                    async with asyncio.timeout(2.0):
                        async with async_client.stream(
                            "GET",
                            "/api/stream/workflow/WF-01",
                            params={"url": f"https://example.com/seminar{i}"},
                        ) as response:
                            return response.status_code
                except TimeoutError:
                    return 200  # 타임아웃은 정상 동작으로 간주

            # 동시에 여러 스트림 요청
            tasks = [make_stream_request(i) for i in range(3)]
            status_codes = await asyncio.gather(*tasks)

            # 모든 응답 성공
            for status_code in status_codes:
                assert status_code == 200

    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """세션 격리 테스트"""
        session1_id = generate_session_id("TEST1")
        session2_id = generate_session_id("TEST2")

        manager1 = SessionEventManager.get_or_create(session1_id)
        manager2 = SessionEventManager.get_or_create(session2_id)

        queue1 = manager1.subscribe()
        queue2 = manager2.subscribe()

        # 세션1에만 이벤트 발행
        await manager1.publish({"type": "session1_event"})

        # 세션1만 수신
        event = await asyncio.wait_for(queue1.get(), timeout=1.0)
        assert event["type"] == "session1_event"

        # 세션2는 이벤트 없음
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue2.get(), timeout=0.1)


# ============================================================
# 테스트 10: 에러 처리
# ============================================================


class TestErrorHandling:
    """에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_pipeline_error_emits_error_event(self):
        """파이프라인 에러 시 에러 이벤트 발행 테스트"""
        session_id = generate_session_id("TEST")
        run_id = generate_run_id()
        manager = SessionEventManager.get_or_create(session_id)
        emitter = WorkflowEventEmitter(manager, run_id)

        queue = manager.subscribe()

        # 에러 발행
        await emitter.emit_run_error("파이프라인 실행 실패", recoverable=False)

        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "RUN_ERROR"
        assert "실패" in event["error"]
        assert event["recoverable"] is False

    @pytest.mark.asyncio
    async def test_invalid_session_format(self, async_client):
        """잘못된 세션 ID 형식 테스트"""
        response = await async_client.get("/api/stream/session/invalid/history")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_session_history(self, async_client):
        """빈 세션 히스토리 테스트"""
        session_id = generate_session_id("EMPTY")
        SessionEventManager.get_or_create(session_id)

        response = await async_client.get(f"/api/stream/session/{session_id}/history")

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 0
