"""
API 라우터 단위 테스트

테스트 대상:
- stream.py: SSE 기반 워크플로 스트리밍
- xai.py: Explainable AI (Evidence Chain, Reasoning Path)
- auth.py: JWT 인증
- workflows.py: REST 기반 워크플로 실행
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.database.models.user import User, UserRole

# ============================================================
# Test Fixtures
# ============================================================


@pytest.fixture
def client():
    """FastAPI TestClient"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock User 객체"""
    user = MagicMock(spec=User)
    user.user_id = "test-user-id"
    user.email = "test@example.com"
    user.name = "Test User"
    user.role = UserRole.USER
    user.is_active = True
    user.hashed_password = "$2b$12$test_hash"
    user.last_login_at = datetime.now(UTC)
    return user


@pytest.fixture
def mock_admin_user():
    """Mock Admin User 객체"""
    user = MagicMock(spec=User)
    user.user_id = "admin-user-id"
    user.email = "admin@example.com"
    user.name = "Admin User"
    user.role = UserRole.ADMIN
    user.is_active = True
    user.hashed_password = "$2b$12$admin_hash"
    user.last_login_at = datetime.now(UTC)
    return user


@pytest.fixture
def mock_db_session():
    """Mock AsyncSession"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


# ============================================================
# Stream Router Tests (stream.py)
# ============================================================


class TestStreamRouter:
    """Stream API 라우터 테스트 (SSE 기반 워크플로)"""

    def setup_method(self):
        """테스트 설정"""
        self.client = TestClient(app)

    # -------------------- WF-01 세미나 파이프라인 --------------------

    def test_stream_seminar_pipeline_success(self):
        """WF-01 세미나 파이프라인 스트림 시작 성공"""
        with (
            patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.stream.SeminarPipelineWithEvents"),
        ):
            # Mock 설정
            mock_manager = MagicMock()
            mock_queue = asyncio.Queue()
            mock_manager.subscribe.return_value = mock_queue
            mock_manager.stream = AsyncMock(return_value=iter([]))
            mock_manager_cls.get_or_create.return_value = mock_manager

            # 스트림 요청 (SSE이므로 응답만 확인)
            response = self.client.get(
                "/api/stream/workflow/WF-01",
                params={"url": "https://example.com/seminar"},
            )

            # SSE 응답 확인
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_stream_seminar_pipeline_with_themes(self):
        """WF-01 세미나 파이프라인 - 테마 포함"""
        with (
            patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.stream.SeminarPipelineWithEvents"),
        ):
            mock_manager = MagicMock()
            mock_queue = asyncio.Queue()
            mock_manager.subscribe.return_value = mock_queue
            mock_manager.stream = AsyncMock(return_value=iter([]))
            mock_manager_cls.get_or_create.return_value = mock_manager

            response = self.client.get(
                "/api/stream/workflow/WF-01",
                params={
                    "url": "https://example.com/seminar",
                    "themes": "AI,Cloud,Security",
                    "play_id": "EXT_Desk_D01_Seminar",
                },
            )

            assert response.status_code == 200

    def test_stream_seminar_pipeline_missing_url(self):
        """WF-01 세미나 파이프라인 - URL 누락"""
        response = self.client.get("/api/stream/workflow/WF-01")

        assert response.status_code == 422  # Validation Error

    # -------------------- WF-02 인터뷰 파이프라인 --------------------

    def test_stream_interview_pipeline_success(self):
        """WF-02 인터뷰 파이프라인 스트림 시작 성공"""
        with (
            patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.stream.InterviewToBriefPipelineWithEvents"),
        ):
            mock_manager = MagicMock()
            mock_queue = asyncio.Queue()
            mock_manager.subscribe.return_value = mock_queue
            mock_manager.stream = AsyncMock(return_value=iter([]))
            mock_manager_cls.get_or_create.return_value = mock_manager

            response = self.client.post(
                "/api/stream/workflow/WF-02",
                params={"content": "인터뷰 노트 내용입니다."},
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_stream_interview_pipeline_with_all_params(self):
        """WF-02 인터뷰 파이프라인 - 모든 파라미터"""
        with (
            patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.stream.InterviewToBriefPipelineWithEvents"),
        ):
            mock_manager = MagicMock()
            mock_queue = asyncio.Queue()
            mock_manager.subscribe.return_value = mock_queue
            mock_manager.stream = AsyncMock(return_value=iter([]))
            mock_manager_cls.get_or_create.return_value = mock_manager

            response = self.client.post(
                "/api/stream/workflow/WF-02",
                params={
                    "content": "인터뷰 내용",
                    "play_id": "KT_Sales_S01",
                    "customer": "대기업",
                    "source": "KT",
                    "channel": "영업PM",
                    "interviewee": "김담당",
                },
            )

            assert response.status_code == 200

    def test_stream_interview_pipeline_missing_content(self):
        """WF-02 인터뷰 파이프라인 - content 누락"""
        response = self.client.post("/api/stream/workflow/WF-02")

        assert response.status_code == 422

    # -------------------- WF-04 인바운드 Triage --------------------

    def test_stream_inbound_triage_success(self):
        """WF-04 인바운드 Triage 스트림 시작 성공"""
        with (
            patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.stream.InboundTriagePipelineWithEvents"),
        ):
            mock_manager = MagicMock()
            mock_queue = asyncio.Queue()
            mock_manager.subscribe.return_value = mock_queue
            mock_manager.stream = AsyncMock(return_value=iter([]))
            mock_manager_cls.get_or_create.return_value = mock_manager

            response = self.client.post(
                "/api/stream/workflow/WF-04",
                params={
                    "title": "신규 기회",
                    "description": "AI 솔루션 도입 문의",
                },
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_stream_inbound_triage_with_urgency(self):
        """WF-04 인바운드 Triage - 긴급도 설정"""
        with (
            patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.stream.InboundTriagePipelineWithEvents"),
        ):
            mock_manager = MagicMock()
            mock_queue = asyncio.Queue()
            mock_manager.subscribe.return_value = mock_queue
            mock_manager.stream = AsyncMock(return_value=iter([]))
            mock_manager_cls.get_or_create.return_value = mock_manager

            response = self.client.post(
                "/api/stream/workflow/WF-04",
                params={
                    "title": "긴급 요청",
                    "description": "긴급 처리 필요",
                    "urgency": "URGENT",
                    "source": "그룹사",
                },
            )

            assert response.status_code == 200

    def test_stream_inbound_triage_missing_required(self):
        """WF-04 인바운드 Triage - 필수 파라미터 누락"""
        response = self.client.post(
            "/api/stream/workflow/WF-04",
            params={"title": "제목만"},  # description 누락
        )

        assert response.status_code == 422

    # -------------------- WF-05 KPI Digest --------------------

    def test_stream_kpi_digest_success(self):
        """WF-05 KPI Digest 스트림 시작 성공"""
        with (
            patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.stream.KPIDigestPipelineWithEvents"),
        ):
            mock_manager = MagicMock()
            mock_queue = asyncio.Queue()
            mock_manager.subscribe.return_value = mock_queue
            mock_manager.stream = AsyncMock(return_value=iter([]))
            mock_manager_cls.get_or_create.return_value = mock_manager

            response = self.client.get("/api/stream/workflow/WF-05")

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_stream_kpi_digest_with_params(self):
        """WF-05 KPI Digest - 파라미터 설정"""
        with (
            patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.stream.KPIDigestPipelineWithEvents"),
        ):
            mock_manager = MagicMock()
            mock_queue = asyncio.Queue()
            mock_manager.subscribe.return_value = mock_queue
            mock_manager.stream = AsyncMock(return_value=iter([]))
            mock_manager_cls.get_or_create.return_value = mock_manager

            response = self.client.get(
                "/api/stream/workflow/WF-05",
                params={"period": "month", "notify": True},
            )

            assert response.status_code == 200

    # -------------------- 범용 워크플로 엔드포인트 --------------------

    def test_stream_workflow_wf01_redirect(self):
        """범용 엔드포인트 - WF-01 리다이렉트 안내"""
        response = self.client.get("/api/stream/workflow/WF-01")

        # WF-01은 전용 엔드포인트 사용 안내 (422: url 파라미터 필수)
        assert response.status_code == 422

    def test_stream_workflow_unsupported(self):
        """범용 엔드포인트 - 지원하지 않는 워크플로"""
        response = self.client.get("/api/stream/workflow/WF-99")

        assert response.status_code == 501
        assert "지원하지 않습니다" in response.json()["detail"]

    # -------------------- 세션 관리 --------------------

    def test_get_session_history_success(self):
        """세션 히스토리 조회 성공"""
        with patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls:
            mock_manager = MagicMock()
            mock_manager.get_history.return_value = [
                {"type": "run_started", "timestamp": "2024-01-01T00:00:00"},
                {"type": "step_completed", "step": "extract_signals"},
            ]
            mock_manager.history = [1, 2]
            mock_manager_cls._instances = {"test-session-id": mock_manager}

            response = self.client.get("/api/stream/session/test-session-id/history")

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session-id"
            assert len(data["events"]) == 2

    def test_get_session_history_not_found(self):
        """세션 히스토리 조회 - 세션 없음"""
        with patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls:
            mock_manager_cls._instances = {}

            response = self.client.get("/api/stream/session/invalid-session/history")

            assert response.status_code == 404

    def test_close_session_success(self):
        """세션 종료 성공"""
        with patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls:
            mock_manager = MagicMock()
            mock_manager_cls._instances = {"test-session-id": mock_manager}
            mock_manager_cls.remove = MagicMock()

            response = self.client.delete("/api/stream/session/test-session-id")

            assert response.status_code == 200
            assert response.json()["status"] == "closed"

    def test_close_session_not_found(self):
        """세션 종료 - 세션 없음"""
        with patch("backend.api.routers.stream.SessionEventManager") as mock_manager_cls:
            mock_manager_cls._instances = {}

            response = self.client.delete("/api/stream/session/invalid-session")

            assert response.status_code == 404


# ============================================================
# XAI Router Tests (xai.py)
# ============================================================


class TestXAIRouter:
    """XAI (Explainable AI) API 라우터 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.client = TestClient(app)

    # -------------------- Scorecard 설명 --------------------

    def test_explain_scorecard_success(self):
        """Scorecard 평가 설명 - 성공"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db") as mock_get_db,
        ):
            # Mock DB 세션
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock Scorecard 엔티티
            mock_entity = MagicMock()
            mock_entity.entity_id = "scorecard-001"
            mock_entity.name = "Test Scorecard"
            mock_entity.description = "테스트 스코어카드"
            mock_entity.confidence = 0.85
            mock_entity.properties = {
                "total_score": 75,
                "decision": "GO",
                "problem_severity_score": 15,
                "willingness_to_pay_score": 14,
            }

            mock_repo.get_entity_by_external_ref = AsyncMock(return_value=mock_entity)
            mock_repo.query_triples = AsyncMock(return_value=([], 0))
            mock_repo.get_reasoning_path = AsyncMock(return_value=[])

            response = self.client.get("/api/xai/explain/scorecard/SC-001")

            assert response.status_code == 200
            data = response.json()
            assert data["scorecard_id"] == "SC-001"

    def test_explain_scorecard_not_found(self):
        """Scorecard 평가 설명 - 엔티티 없음"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_repo.get_entity_by_external_ref = AsyncMock(return_value=None)

            response = self.client.get("/api/xai/explain/scorecard/invalid-id")

            assert response.status_code == 200
            data = response.json()
            # 엔티티 없으면 기본 응답 반환
            assert data["total_score"] == 0
            assert data["decision"] == "UNKNOWN"

    # -------------------- Signal 추적 --------------------

    def test_trace_signal_origin_success(self):
        """Signal 출처 추적 - 성공"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            # Mock Signal 엔티티
            mock_signal = MagicMock()
            mock_signal.entity_id = "signal-001"
            mock_signal.name = "Test Signal"

            mock_repo.get_entity_by_external_ref = AsyncMock(return_value=mock_signal)
            mock_repo.query_triples = AsyncMock(return_value=([], 0))

            response = self.client.get("/api/xai/trace/signal/SIG-001")

            assert response.status_code == 200
            data = response.json()
            assert data["signal_id"] == "SIG-001"
            assert "traces" in data

    def test_trace_signal_origin_not_found(self):
        """Signal 출처 추적 - Signal 없음"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_repo.get_entity_by_external_ref = AsyncMock(return_value=None)
            mock_repo.get_entity = AsyncMock(return_value=None)

            response = self.client.get("/api/xai/trace/signal/invalid-signal")

            assert response.status_code == 404

    def test_trace_signal_with_max_depth(self):
        """Signal 출처 추적 - max_depth 설정"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_signal = MagicMock()
            mock_signal.entity_id = "signal-001"
            mock_repo.get_entity_by_external_ref = AsyncMock(return_value=mock_signal)
            mock_repo.query_triples = AsyncMock(return_value=([], 0))

            response = self.client.get("/api/xai/trace/signal/SIG-001", params={"max_depth": 3})

            assert response.status_code == 200

    def test_trace_signal_max_depth_validation(self):
        """Signal 출처 추적 - max_depth 유효성 검증"""
        response = self.client.get(
            "/api/xai/trace/signal/SIG-001",
            params={"max_depth": 15},  # 최대 10
        )

        assert response.status_code == 422

    # -------------------- 신뢰도 분석 --------------------

    def test_calculate_confidence_success(self):
        """신뢰도 분석 - 성공"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_entity = MagicMock()
            mock_entity.entity_id = "entity-001"
            mock_entity.confidence = 0.8
            mock_entity.properties = {"field1": "value1", "field2": "value2"}

            mock_repo.get_entity = AsyncMock(return_value=mock_entity)
            mock_repo.query_triples = AsyncMock(return_value=([], 0))

            response = self.client.get("/api/xai/confidence/entity-001")

            assert response.status_code == 200
            data = response.json()
            assert data["entity_id"] == "entity-001"
            assert "factors" in data
            assert "recommendations" in data

    def test_calculate_confidence_not_found(self):
        """신뢰도 분석 - 엔티티 없음"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_repo.get_entity = AsyncMock(return_value=None)

            response = self.client.get("/api/xai/confidence/invalid-entity")

            assert response.status_code == 404

    def test_calculate_confidence_with_evidence(self):
        """신뢰도 분석 - Evidence 포함"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_entity = MagicMock()
            mock_entity.entity_id = "entity-001"
            mock_entity.confidence = 0.7
            mock_entity.properties = {}

            # Evidence 트리플 Mock
            mock_triple = MagicMock()
            mock_triple.confidence = 0.9

            mock_repo.get_entity = AsyncMock(return_value=mock_entity)
            mock_repo.query_triples = AsyncMock(side_effect=[([mock_triple], 1), ([], 0), ([], 0)])

            response = self.client.get("/api/xai/confidence/entity-001")

            assert response.status_code == 200
            data = response.json()
            # Evidence가 있으므로 positive factor 포함
            assert any(f["factor_name"] == "Evidence Support" for f in data["factors"])

    # -------------------- Evidence Chain --------------------

    def test_get_evidence_chain_success(self):
        """Evidence Chain 조회 - 성공"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_entity = MagicMock()
            mock_entity.entity_id = "entity-001"
            mock_entity.entity_type = MagicMock()
            mock_entity.entity_type.value = "Signal"

            mock_repo.get_entity = AsyncMock(return_value=mock_entity)
            mock_repo.query_triples = AsyncMock(return_value=([], 0))

            response = self.client.get("/api/xai/evidence-chain/entity-001")

            assert response.status_code == 200
            data = response.json()
            assert data["target_id"] == "entity-001"
            assert data["target_type"] == "Signal"

    def test_get_evidence_chain_not_found(self):
        """Evidence Chain 조회 - 엔티티 없음"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_repo.get_entity = AsyncMock(return_value=None)

            response = self.client.get("/api/xai/evidence-chain/invalid-entity")

            assert response.status_code == 404

    # -------------------- Reasoning Path --------------------

    def test_get_reasoning_path_success(self):
        """추론 경로 조회 - 성공"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_entity = MagicMock()
            mock_entity.entity_id = "entity-001"
            mock_entity.name = "Test Entity"
            mock_entity.description = "테스트 결론"

            mock_repo.get_entity = AsyncMock(return_value=mock_entity)
            mock_repo.get_reasoning_path = AsyncMock(return_value=[])

            response = self.client.get("/api/xai/reasoning-path/entity-001")

            assert response.status_code == 200
            data = response.json()
            assert data["final_conclusion"] == "테스트 결론"

    def test_get_reasoning_path_not_found(self):
        """추론 경로 조회 - 엔티티 없음"""
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_repo.get_entity = AsyncMock(return_value=None)

            response = self.client.get("/api/xai/reasoning-path/invalid-entity")

            assert response.status_code == 404


# ============================================================
# Auth Router Tests (auth.py)
# ============================================================


class TestAuthRouter:
    """Auth API 라우터 테스트 (JWT 인증)"""

    def setup_method(self):
        """테스트 설정"""
        self.client = TestClient(app)

    # -------------------- JSON 로그인 --------------------

    def test_login_success(self, mock_user):
        """로그인 성공 (JSON)"""
        with (
            patch("backend.api.routers.auth.authenticate_user") as mock_auth,
            patch("backend.api.routers.auth.update_last_login") as mock_update,
            patch("backend.api.routers.auth.get_db"),
        ):
            mock_auth.return_value = mock_user
            mock_update.return_value = None

            response = self.client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "password123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self):
        """로그인 실패 - 잘못된 인증 정보"""
        with (
            patch("backend.api.routers.auth.authenticate_user") as mock_auth,
            patch("backend.api.routers.auth.get_db"),
        ):
            mock_auth.return_value = None

            response = self.client.post(
                "/api/auth/login",
                json={"email": "wrong@example.com", "password": "wrongpassword"},
            )

            assert response.status_code == 401
            assert "올바르지 않습니다" in response.json()["detail"]

    def test_login_invalid_email_format(self):
        """로그인 실패 - 잘못된 이메일 형식"""
        response = self.client.post(
            "/api/auth/login", json={"email": "not-an-email", "password": "password123"}
        )

        assert response.status_code == 422

    def test_login_empty_password(self):
        """로그인 실패 - 빈 비밀번호"""
        response = self.client.post(
            "/api/auth/login", json={"email": "test@example.com", "password": ""}
        )

        assert response.status_code == 422

    # -------------------- OAuth2 Form 로그인 --------------------

    def test_token_login_success(self, mock_user):
        """토큰 로그인 성공 (OAuth2 Form)"""
        with (
            patch("backend.api.routers.auth.authenticate_user") as mock_auth,
            patch("backend.api.routers.auth.update_last_login") as mock_update,
            patch("backend.api.routers.auth.get_db"),
        ):
            mock_auth.return_value = mock_user
            mock_update.return_value = None

            response = self.client.post(
                "/api/auth/token",
                data={"username": "test@example.com", "password": "password123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data

    def test_token_login_invalid_credentials(self):
        """토큰 로그인 실패 - 잘못된 인증 정보"""
        with (
            patch("backend.api.routers.auth.authenticate_user") as mock_auth,
            patch("backend.api.routers.auth.get_db"),
        ):
            mock_auth.return_value = None

            response = self.client.post(
                "/api/auth/token",
                data={"username": "wrong@example.com", "password": "wrongpassword"},
            )

            assert response.status_code == 401

    # -------------------- 현재 사용자 정보 --------------------

    def test_get_me_success(self, mock_user):
        """현재 사용자 정보 조회 - 성공"""
        from backend.api.deps import get_current_user

        # 의존성 오버라이드 (DB 연결 우회)
        async def mock_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            response = self.client.get(
                "/api/auth/me", headers={"Authorization": "Bearer mock-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["user"]["email"] == mock_user.email
        finally:
            app.dependency_overrides.clear()

    def test_get_me_no_token(self):
        """현재 사용자 정보 조회 - 토큰 없음"""
        response = self.client.get("/api/auth/me")

        assert response.status_code == 401

    def test_get_me_invalid_token(self):
        """현재 사용자 정보 조회 - 유효하지 않은 토큰"""
        response = self.client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401


# ============================================================
# Workflows Router Tests (workflows.py)
# ============================================================


class TestWorkflowsRouter:
    """Workflows API 라우터 테스트 (REST 기반)"""

    def setup_method(self):
        """테스트 설정"""
        self.client = TestClient(app)

    # -------------------- WF-02 Interview-to-Brief --------------------

    def test_interview_to_brief_success(self):
        """WF-02 인터뷰-to-Brief - 성공"""
        with (
            patch("backend.api.routers.workflows.InterviewToBriefPipeline") as mock_pipeline_cls,
            patch("backend.api.routers.workflows.get_db"),
        ):
            # Mock 결과
            mock_result = MagicMock()
            mock_result.signals = [{"signal_id": "SIG-001", "title": "테스트 신호"}]
            mock_result.scorecards = [{"scorecard_id": "SC-001", "total_score": 75}]
            mock_result.briefs = [{"brief_id": "BRF-001", "title": "테스트 Brief"}]
            mock_result.pending_approvals = ["BRF-001"]
            mock_result.summary = {"total_signals": 1}

            mock_pipeline = AsyncMock()
            mock_pipeline.run = AsyncMock(return_value=mock_result)
            mock_pipeline_cls.return_value = mock_pipeline

            response = self.client.post(
                "/api/workflows/interview-to-brief",
                json={
                    "content": "인터뷰 노트 내용입니다. 고객이 AI 솔루션에 관심을 보였습니다.",
                    "save_to_db": False,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert len(data["signals"]) == 1

    def test_interview_to_brief_with_db_save(self):
        """WF-02 인터뷰-to-Brief - DB 저장 포함"""
        with (
            patch(
                "backend.api.routers.workflows.InterviewToBriefPipelineWithDB"
            ) as mock_pipeline_cls,
            patch("backend.api.routers.workflows.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.workflows.get_db"),
        ):
            mock_manager_cls.get_or_create.return_value = MagicMock()
            mock_manager_cls.remove = MagicMock()

            mock_result = MagicMock()
            mock_result.signals = []
            mock_result.scorecards = []
            mock_result.briefs = []
            mock_result.pending_approvals = []
            mock_result.summary = {}

            mock_pipeline = AsyncMock()
            mock_pipeline.run = AsyncMock(return_value=mock_result)
            mock_pipeline.save_to_db = AsyncMock(
                return_value={"signals": [], "scorecards": [], "briefs": []}
            )
            mock_pipeline_cls.return_value = mock_pipeline

            response = self.client.post(
                "/api/workflows/interview-to-brief",
                json={
                    "content": "테스트 인터뷰 내용",
                    "save_to_db": True,
                },
            )

            assert response.status_code == 200

    def test_interview_to_brief_missing_content(self):
        """WF-02 인터뷰-to-Brief - content 누락"""
        response = self.client.post("/api/workflows/interview-to-brief", json={})

        assert response.status_code == 422

    def test_interview_to_brief_preview(self):
        """인터뷰 Signal 추출 미리보기"""
        with patch(
            "backend.agent_runtime.workflows.wf_interview_to_brief.extract_signals_from_interview"
        ) as mock_extract:
            mock_signal = MagicMock()
            mock_signal.title = "테스트 신호"
            mock_signal.pain = "고객 문제"
            mock_signal.confidence = 0.85
            mock_extract.return_value = [mock_signal]

            response = self.client.post(
                "/api/workflows/interview-to-brief/preview",
                params={"content": "인터뷰 내용"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "preview"
            assert data["signals_count"] == 1

    # -------------------- WF-04 Inbound Triage --------------------

    def test_inbound_triage_success(self):
        """WF-04 인바운드 Triage - 성공"""
        with (
            patch("backend.api.routers.workflows.InboundTriagePipeline") as mock_pipeline_cls,
            patch("backend.api.routers.workflows.get_db"),
        ):
            # InboundOutput 필드에 맞춤
            mock_result = MagicMock()
            mock_result.signal_id = "SIG-001"
            mock_result.is_duplicate = False
            mock_result.duplicate_of = None
            mock_result.play_id = "KT_Inbound_I01"
            mock_result.scorecard = {"scorecard_id": "SC-001"}
            mock_result.sla_deadline = "2024-01-03T00:00:00"
            mock_result.next_action = "Triage"
            mock_result.summary = {}

            mock_pipeline = AsyncMock()
            mock_pipeline.run = AsyncMock(return_value=mock_result)
            mock_pipeline_cls.return_value = mock_pipeline

            response = self.client.post(
                "/api/workflows/inbound-triage",
                json={
                    "title": "신규 문의",
                    "description": "AI 솔루션 도입 관련 문의",
                    "save_to_db": False,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["is_duplicate"] is False

    def test_inbound_triage_duplicate_detected(self):
        """WF-04 인바운드 Triage - 중복 감지"""
        with (
            patch("backend.api.routers.workflows.InboundTriagePipeline") as mock_pipeline_cls,
            patch("backend.api.routers.workflows.get_db"),
        ):
            # InboundOutput 필드에 맞춤 (중복 케이스)
            mock_result = MagicMock()
            mock_result.signal_id = None
            mock_result.is_duplicate = True
            mock_result.duplicate_of = "SIG-existing"
            mock_result.play_id = ""
            mock_result.scorecard = None
            mock_result.sla_deadline = ""
            mock_result.next_action = ""
            mock_result.summary = {
                "similar_signals": [{"signal_id": "SIG-existing"}],
                "duplicate_count": 1,
            }

            mock_pipeline = AsyncMock()
            mock_pipeline.run = AsyncMock(return_value=mock_result)
            mock_pipeline_cls.return_value = mock_pipeline

            response = self.client.post(
                "/api/workflows/inbound-triage",
                json={
                    "title": "중복 문의",
                    "description": "이미 있는 내용",
                    "save_to_db": False,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_duplicate"] is True
            assert data["signal"] is None

    def test_inbound_triage_missing_required(self):
        """WF-04 인바운드 Triage - 필수 필드 누락"""
        response = self.client.post(
            "/api/workflows/inbound-triage",
            json={"title": "제목만"},  # description 누락
        )

        assert response.status_code == 422

    def test_inbound_triage_preview(self):
        """인바운드 Triage 미리보기"""
        with patch("backend.agent_runtime.workflows.wf_inbound_triage.route_to_play") as mock_route:
            mock_route.return_value = "KT_Inbound_I01"

            response = self.client.post(
                "/api/workflows/inbound-triage/preview",
                params={
                    "title": "테스트",
                    "description": "테스트 설명",
                    "urgency": "URGENT",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "preview"
            assert data["sla"]["hours"] == 24  # URGENT

    def test_inbound_triage_preview_invalid_urgency(self):
        """인바운드 Triage 미리보기 - 잘못된 urgency"""
        with patch("backend.agent_runtime.workflows.wf_inbound_triage.route_to_play") as mock_route:
            mock_route.return_value = "KT_Inbound_I01"

            response = self.client.post(
                "/api/workflows/inbound-triage/preview",
                params={
                    "title": "테스트",
                    "description": "테스트 설명",
                    "urgency": "INVALID",  # 잘못된 값 -> NORMAL로 폴백
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["sla"]["hours"] == 48  # NORMAL 기본값

    # -------------------- WF-05 KPI Digest --------------------

    def test_kpi_digest_success(self):
        """WF-05 KPI Digest - 성공"""
        with (
            patch("backend.api.routers.workflows.KPIDigestPipelineWithDB") as mock_pipeline_cls,
            patch("backend.api.routers.workflows.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.workflows.get_db"),
        ):
            mock_manager_cls.get_or_create.return_value = MagicMock()
            mock_manager_cls.remove = MagicMock()

            mock_result = MagicMock()
            mock_result.period = "week"
            mock_result.period_start = "2024-01-01"
            mock_result.period_end = "2024-01-07"
            mock_result.metrics = {
                "activity": {"current": 25, "target": 20, "achievement": "125%"},
                "signal": {"current": 35, "target": 30, "achievement": "117%"},
                "brief": {"current": 6, "target": 6, "achievement": "100%"},
                "s2": {"current": 3, "target": 3, "achievement": "100%"},
            }
            mock_result.lead_times = {
                "signal_to_brief": 5,
                "brief_to_s2": 10,
            }
            mock_result.alerts = []
            mock_result.top_plays = []
            mock_result.recommendations = ["권고사항1"]
            mock_result.status_summary = {"G": 5, "Y": 2, "R": 1}
            mock_result.confluence_url = "https://confluence.example.com/page"
            mock_result.generated_at = "2024-01-07T12:00:00"

            mock_pipeline = AsyncMock()
            mock_pipeline.run = AsyncMock(return_value=mock_result)
            mock_pipeline_cls.return_value = mock_pipeline

            response = self.client.get("/api/workflows/kpi-digest")

            assert response.status_code == 200
            data = response.json()
            assert data["period"] == "week"
            assert "metrics" in data

    def test_kpi_digest_with_params(self):
        """WF-05 KPI Digest - 파라미터 설정"""
        with (
            patch("backend.api.routers.workflows.KPIDigestPipelineWithDB") as mock_pipeline_cls,
            patch("backend.api.routers.workflows.SessionEventManager") as mock_manager_cls,
            patch("backend.api.routers.workflows.get_db"),
        ):
            mock_manager_cls.get_or_create.return_value = MagicMock()
            mock_manager_cls.remove = MagicMock()

            mock_result = MagicMock()
            mock_result.period = "month"
            mock_result.period_start = "2024-01-01"
            mock_result.period_end = "2024-01-31"
            mock_result.metrics = {
                "activity": {"achievement": "100%"},
                "signal": {"achievement": "100%"},
                "brief": {"achievement": "100%"},
                "s2": {"achievement": "100%"},
            }
            mock_result.lead_times = {}
            mock_result.alerts = []
            mock_result.top_plays = []
            mock_result.recommendations = []
            mock_result.status_summary = {}
            mock_result.confluence_url = None
            mock_result.generated_at = "2024-01-31T12:00:00"

            mock_pipeline = AsyncMock()
            mock_pipeline.run = AsyncMock(return_value=mock_result)
            mock_pipeline_cls.return_value = mock_pipeline

            response = self.client.get(
                "/api/workflows/kpi-digest", params={"period": "month", "notify": True}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["period"] == "month"

    def test_kpi_digest_summary(self):
        """KPI 요약 미리보기"""
        with (
            patch("backend.api.routers.workflows.KPIDigestPipeline") as mock_pipeline_cls,
            patch(
                "backend.agent_runtime.workflows.wf_kpi_digest.calculate_period_range"
            ) as mock_range,
        ):
            from datetime import datetime

            mock_range.return_value = (
                datetime(2024, 1, 1),
                datetime(2024, 1, 7),
            )

            mock_result = MagicMock()
            mock_result.metrics = {
                "activity": {"achievement": "100%"},
                "signal": {"achievement": "100%"},
                "brief": {"achievement": "100%"},
                "s2": {"achievement": "100%"},
            }
            mock_result.alerts = []

            mock_pipeline = AsyncMock()
            mock_pipeline.run = AsyncMock(return_value=mock_result)
            mock_pipeline_cls.return_value = mock_pipeline

            response = self.client.get("/api/workflows/kpi-digest/summary")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "preview"
            assert "metrics_summary" in data


# ============================================================
# Integration Tests (Cross-Router)
# ============================================================


class TestRouterIntegration:
    """라우터 간 통합 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.client = TestClient(app)

    def test_api_prefix_consistency(self):
        """API 접두사 일관성 테스트"""
        # Stream 라우터
        response = self.client.get("/api/stream/workflow/WF-99")
        assert response.status_code in [404, 501]

        # XAI 라우터
        with (
            patch("backend.api.routers.xai.ontology_repo") as mock_repo,
            patch("backend.api.routers.xai.get_db"),
        ):
            mock_repo.get_entity = AsyncMock(return_value=None)
            response = self.client.get("/api/xai/confidence/test")
            assert response.status_code in [404, 500]

        # Auth 라우터
        response = self.client.get("/api/auth/me")
        assert response.status_code == 401

        # Workflows 라우터
        response = self.client.post(
            "/api/workflows/interview-to-brief",
            json={},
        )
        assert response.status_code == 422

    def test_error_response_format(self):
        """에러 응답 형식 일관성"""
        # 모든 라우터가 동일한 형식의 에러 응답 반환 확인
        response = self.client.post(
            "/api/workflows/inbound-triage",
            json={},
        )
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data


# ============================================================
# Helper function for fixture access
# ============================================================


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    """각 테스트 후 의존성 오버라이드 초기화"""
    yield
    app.dependency_overrides.clear()
