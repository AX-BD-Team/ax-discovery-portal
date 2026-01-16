"""
API 통합 테스트

pytest + httpx TestClient를 사용한 REST API 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api.deps import get_db
from backend.api.main import app

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
async def mock_db_session():
    """Mock 데이터베이스 세션"""
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    return mock_session


@pytest.fixture
async def async_client(mock_db_session):
    """테스트용 AsyncClient"""

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ============================================================
# Health Check Tests
# ============================================================


class TestHealthEndpoints:
    """헬스 체크 엔드포인트 테스트"""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        """기본 헬스 체크"""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client):
        """루트 엔드포인트"""
        response = await async_client.get("/")

        assert response.status_code == 200


# ============================================================
# Inbox API Tests
# ============================================================


class TestInboxAPI:
    """Inbox (Signal) API 테스트"""

    @pytest.mark.asyncio
    async def test_create_signal(self, async_client):
        """Signal 생성 API"""
        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.create"
        ) as mock_create:
            mock_create.return_value = {
                "signal_id": "SIG-2026-001",
                "title": "테스트 Signal",
                "source": "KT",
                "channel": "데스크리서치",
                "play_id": "TEST_PLAY",
                "pain": "테스트 Pain",
                "status": "S0",
            }

            response = await async_client.post(
                "/api/inbox",
                json={
                    "title": "테스트 Signal",
                    "source": "KT",
                    "channel": "데스크리서치",
                    "play_id": "TEST_PLAY",
                    "pain": "테스트 Pain",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["signal_id"] == "SIG-2026-001"
            assert data["title"] == "테스트 Signal"

    @pytest.mark.asyncio
    async def test_list_signals(self, async_client):
        """Signal 목록 조회 API"""
        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.get_all"
        ) as mock_get_all:
            mock_get_all.return_value = (
                [
                    {
                        "signal_id": "SIG-2026-001",
                        "title": "Signal 1",
                        "source": "KT",
                        "channel": "데스크리서치",
                        "play_id": "PLAY1",
                        "pain": "Pain 1",
                        "status": "S0",
                    },
                    {
                        "signal_id": "SIG-2026-002",
                        "title": "Signal 2",
                        "source": "그룹사",
                        "channel": "영업PM",
                        "play_id": "PLAY2",
                        "pain": "Pain 2",
                        "status": "S1",
                    },
                ],
                2,
            )

            response = await async_client.get("/api/inbox")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_signal_by_id(self, async_client):
        """Signal 상세 조회 API"""
        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.get_by_id"
        ) as mock_get:
            mock_get.return_value = {
                "signal_id": "SIG-2026-001",
                "title": "테스트 Signal",
                "source": "KT",
                "channel": "데스크리서치",
                "play_id": "TEST_PLAY",
                "pain": "테스트 Pain",
                "status": "S0",
            }

            response = await async_client.get("/api/inbox/SIG-2026-001")

            assert response.status_code == 200
            data = response.json()
            assert data["signal_id"] == "SIG-2026-001"

    @pytest.mark.asyncio
    async def test_get_signal_not_found(self, async_client):
        """존재하지 않는 Signal 조회"""
        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.get_by_id"
        ) as mock_get:
            mock_get.return_value = None

            response = await async_client.get("/api/inbox/SIG-NOT-EXIST")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_triage_signal(self, async_client):
        """Signal Triage API"""
        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.update_status"
        ) as mock_update:
            mock_update.return_value = True

            response = await async_client.post("/api/inbox/SIG-2026-001/triage")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "queued"
            assert data["signal_id"] == "SIG-2026-001"

    @pytest.mark.asyncio
    async def test_inbox_stats(self, async_client):
        """Inbox 통계 API"""
        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.get_stats"
        ) as mock_stats:
            mock_stats.return_value = {
                "total": 50,
                "by_status": {"S0": 30, "S1": 15, "S2": 5},
                "by_source": {"KT": 25, "그룹사": 15, "대외": 10},
            }

            response = await async_client.get("/api/inbox/stats/summary")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 50
            assert data["by_status"]["S0"] == 30


# ============================================================
# Workflow API Tests
# ============================================================


class TestWorkflowAPI:
    """Workflow API 테스트"""

    @pytest.mark.asyncio
    async def test_interview_to_brief(self, async_client):
        """WF-02 Interview-to-Brief API"""
        response = await async_client.post(
            "/api/workflows/interview-to-brief",
            json={
                "content": "인터뷰 내용입니다. Pain point: 고객 대기 시간이 깁니다.",
                "play_id": "KT_Sales_S01",
                "customer": "KT",
                "source": "KT",
                "channel": "영업PM",
                "save_to_db": False,  # DB 저장 비활성화
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "completed"]  # 응답 형식에 따라 다를 수 있음
        assert "signals" in data
        assert "scorecards" in data
        assert "briefs" in data

    @pytest.mark.asyncio
    async def test_inbound_triage(self, async_client):
        """WF-04 Inbound Triage API"""
        response = await async_client.post(
            "/api/workflows/inbound-triage",
            json={
                "title": "AI 콜센터 자동화 문의",
                "description": "고객 상담 대기 시간을 줄이고 싶습니다",
                "customer_segment": "KT",
                "pain": "대기 시간이 길어 고객 불만 증가",
                "submitter": "홍길동",
                "urgency": "NORMAL",
                "source": "KT",
                "save_to_db": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "completed"]  # 응답 형식에 따라 다를 수 있음
        assert "signal" in data
        assert "scorecard" in data
        assert "sla" in data

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="DB 연동 필요 - 실제 DB 또는 완전한 Mock 필요")
    async def test_kpi_digest(self, async_client):
        """WF-05 KPI Digest API"""
        # KPI Digest는 GET 메서드 사용
        response = await async_client.get(
            "/api/workflows/kpi-digest",
            params={
                "period": "week",
                "notify": "false",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "completed"]
        assert "digest" in data
        assert data["digest"]["period"] == "week"

    @pytest.mark.asyncio
    async def test_voc_mining_preview(self, async_client):
        """WF-03 VoC Mining Preview API"""
        response = await async_client.post(
            "/api/workflows/voc-mining/preview",
            json={
                "source_type": "text",
                "text_content": "응답 시간이 느립니다\n앱이 자주 튕깁니다\n대기 시간이 깁니다",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # VoC Mining 결과 구조 검증
        assert "status" in data or "themes" in data

    @pytest.mark.asyncio
    async def test_confluence_sync(self, async_client):
        """WF-06 Confluence Sync API"""
        response = await async_client.post(
            "/api/workflows/confluence-sync",
            json={
                "targets": [
                    {
                        "target_type": "signal",
                        "target_id": "SIG-2026-001",
                        "action": "create_page",
                        "data": {
                            "title": "테스트 Signal",
                            "pain": "테스트 Pain",
                        },
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "completed"]  # 응답 형식에 따라 다를 수 있음
        assert "results" in data


# ============================================================
# Error Handling Tests
# ============================================================


class TestAPIErrorHandling:
    """API 에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_validation_error(self, async_client):
        """유효성 검증 에러"""
        # 필수 필드 누락
        response = await async_client.post(
            "/api/inbox",
            json={
                "source": "KT",
                # title, pain 누락
            },
        )

        assert response.status_code == 422  # Validation Error

    @pytest.mark.asyncio
    async def test_invalid_json(self, async_client):
        """잘못된 JSON 형식"""
        response = await async_client.post(
            "/api/inbox",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, async_client):
        """허용되지 않는 HTTP 메서드"""
        response = await async_client.delete("/api/inbox")

        assert response.status_code == 405


# ============================================================
# Pagination Tests
# ============================================================


class TestAPIPagination:
    """API 페이지네이션 테스트"""

    @pytest.mark.asyncio
    async def test_pagination_parameters(self, async_client):
        """페이지네이션 파라미터"""
        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.get_all"
        ) as mock_get_all:
            mock_get_all.return_value = ([], 100)

            response = await async_client.get("/api/inbox?page=2&page_size=10")

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["page_size"] == 10

    @pytest.mark.asyncio
    async def test_filtering_parameters(self, async_client):
        """필터링 파라미터"""
        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.get_all"
        ) as mock_get_all:
            mock_get_all.return_value = ([], 0)

            response = await async_client.get("/api/inbox?source=KT&status=S0")

            assert response.status_code == 200


# ============================================================
# Concurrent Request Tests
# ============================================================


class TestAPIConcurrency:
    """API 동시 요청 테스트"""

    @pytest.mark.asyncio
    async def test_concurrent_signal_creation(self, async_client):
        """동시 Signal 생성"""
        import asyncio

        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.create"
        ) as mock_create:
            # 동적으로 signal_id 생성
            call_count = [0]

            async def create_signal(*args, **kwargs):
                call_count[0] += 1
                return {
                    "signal_id": f"SIG-2026-{call_count[0]:03d}",
                    "title": f"Signal {call_count[0]}",
                    "source": "KT",
                    "channel": "데스크리서치",
                    "play_id": "TEST",
                    "pain": "Test",
                    "status": "S0",
                }

            mock_create.side_effect = create_signal

            # 5개 동시 요청
            tasks = [
                async_client.post(
                    "/api/inbox",
                    json={
                        "title": f"Signal {i}",
                        "pain": f"Pain {i}",
                    },
                )
                for i in range(5)
            ]

            responses = await asyncio.gather(*tasks)

            # 모든 요청 성공 확인
            assert all(r.status_code == 200 for r in responses)

            # 고유 ID 확인
            signal_ids = [r.json()["signal_id"] for r in responses]
            assert len(set(signal_ids)) == 5


# ============================================================
# Response Format Tests
# ============================================================


class TestAPIResponseFormat:
    """API 응답 형식 테스트"""

    @pytest.mark.asyncio
    async def test_signal_response_format(self, async_client):
        """Signal 응답 형식 검증"""
        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.create"
        ) as mock_create:
            mock_create.return_value = {
                "signal_id": "SIG-2026-001",
                "title": "테스트",
                "source": "KT",
                "channel": "데스크리서치",
                "play_id": "TEST",
                "pain": "Pain",
                "status": "S0",
            }

            response = await async_client.post(
                "/api/inbox",
                json={"title": "테스트", "pain": "Pain"},
            )

            data = response.json()

            # 필수 필드 확인
            required_fields = [
                "signal_id",
                "title",
                "source",
                "channel",
                "play_id",
                "pain",
                "status",
            ]

            for field in required_fields:
                assert field in data

    @pytest.mark.asyncio
    async def test_list_response_format(self, async_client):
        """목록 응답 형식 검증"""
        with patch(
            "backend.integrations.cloudflare_d1.repositories.signal_d1_repo.get_all"
        ) as mock_get_all:
            mock_get_all.return_value = ([], 0)

            response = await async_client.get("/api/inbox")

            data = response.json()

            # 페이지네이션 필드 확인
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data


# ============================================================
# Workflow Integration Tests
# ============================================================


class TestWorkflowIntegration:
    """워크플로 통합 API 테스트"""

    @pytest.mark.asyncio
    async def test_seminar_add_command(self, async_client):
        """세미나 추가 커맨드 API"""
        with patch("backend.agent_runtime.runner.runtime.run_workflow") as mock_run:
            # Mock 응답 설정
            from unittest.mock import MagicMock

            mock_activity = MagicMock()
            mock_activity.activity_id = "ACT-2026-001"
            mock_activity.title = "테스트 세미나"
            mock_activity.date = "2026-03-15"
            mock_activity.play_id = "EXT_Desk_D01"

            mock_run.return_value = {
                "activity": mock_activity,
                "confluence_updated": True,
            }

            response = await async_client.post(
                "/api/inbox/seminar",
                params={
                    "url": "https://example.com/seminar",
                    "themes": "AI,DX",
                    "play_id": "EXT_Desk_D01_Seminar",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["activity_id"] == "ACT-2026-001"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="DB 연동 필요 - 실제 DB 또는 완전한 Mock 필요")
    async def test_workflow_chain_execution(self, async_client):
        """워크플로 체인 실행 테스트"""
        # Step 1: Inbound Triage로 Signal 생성
        response1 = await async_client.post(
            "/api/workflows/inbound-triage",
            json={
                "title": "테스트 문의",
                "description": "테스트입니다",
                "save_to_db": False,
            },
        )

        assert response1.status_code == 200
        signal_data = response1.json()
        assert signal_data["status"] in ["success", "completed"]

        # Step 2: KPI Digest 생성 (GET 메서드)
        response2 = await async_client.get(
            "/api/workflows/kpi-digest",
            params={"period": "week", "notify": "false"},
        )

        assert response2.status_code == 200
        kpi_data = response2.json()
        assert kpi_data["status"] in ["success", "completed"]

    @pytest.mark.asyncio
    async def test_confluence_bidirectional_sync(self, async_client):
        """Confluence 양방향 동기화 API"""
        response = await async_client.post(
            "/api/workflows/confluence-sync/bidirectional",
            params={"target_type": "signal"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "export_results" in data
        assert "import_results" in data

    @pytest.mark.asyncio
    async def test_confluence_import(self, async_client):
        """Confluence Import API"""
        response = await async_client.post(
            "/api/workflows/confluence-sync/import",
            json={
                "target_type": "signal",
                "page_ids": ["12345", "67890"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "imported" in data

    @pytest.mark.asyncio
    async def test_confluence_parse_preview(self, async_client):
        """Confluence 파싱 미리보기 API"""
        content = """
# Signal: 테스트

| 필드 | 값 |
|------|-----|
| Signal ID | SIG-2026-001 |
| 상태 | S0 |
"""
        response = await async_client.post(
            "/api/workflows/confluence-sync/parse-preview",
            params={"content": content, "page_type": "signal"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "parsed_data" in data
