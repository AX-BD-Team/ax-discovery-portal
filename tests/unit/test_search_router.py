"""
Search Router 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.api.main import app


class TestSearchRouter:
    """Search API 라우터 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.client = TestClient(app)

    def test_health_check_configured(self):
        """헬스체크 - 설정됨"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.health_check = AsyncMock(
                return_value={
                    "embedding": True,
                    "vectorize": True,
                    "overall": True,
                }
            )

            response = self.client.get("/api/search/health")

        assert response.status_code == 200
        data = response.json()
        assert data["embedding"] is True
        assert data["vectorize"] is True
        assert data["overall"] is True

    def test_health_check_not_configured(self):
        """헬스체크 - 미설정"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.health_check = AsyncMock(
                return_value={
                    "embedding": False,
                    "vectorize": False,
                    "overall": False,
                }
            )

            response = self.client.get("/api/search/health")

        assert response.status_code == 200
        data = response.json()
        assert data["overall"] is False

    def test_semantic_search_success(self):
        """의미 검색 성공"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = True
            mock_service.search_similar = AsyncMock(
                return_value=[
                    {
                        "entity_id": "SIG-001",
                        "score": 0.95,
                        "metadata": {
                            "entity_type": "Signal",
                            "name": "테스트 신호",
                            "confidence": 0.9,
                        },
                    },
                ]
            )

            response = self.client.get(
                "/api/search/semantic",
                params={"query": "테스트 검색", "top_k": 10, "min_score": 0.7},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "테스트 검색"
        assert data["total"] == 1
        assert data["items"][0]["entity_id"] == "SIG-001"
        assert data["items"][0]["score"] == 0.95

    def test_semantic_search_with_entity_types(self):
        """Entity 타입 필터 적용 검색"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = True
            mock_service.search_similar = AsyncMock(return_value=[])

            response = self.client.get(
                "/api/search/semantic",
                params={
                    "query": "테스트",
                    "entity_types": ["Signal", "Topic"],
                },
            )

        assert response.status_code == 200
        mock_service.search_similar.assert_called_once()

    def test_semantic_search_invalid_entity_type(self):
        """유효하지 않은 Entity 타입"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = True

            response = self.client.get(
                "/api/search/semantic",
                params={
                    "query": "테스트",
                    "entity_types": ["InvalidType"],
                },
            )

        assert response.status_code == 400
        assert "유효하지 않은 Entity 타입" in response.json()["detail"]

    def test_semantic_search_not_configured(self):
        """서비스 미설정 시 503 오류"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = False

            response = self.client.get(
                "/api/search/semantic",
                params={"query": "테스트"},
            )

        assert response.status_code == 503
        assert "설정되지 않았습니다" in response.json()["detail"]

    def test_semantic_search_post(self):
        """POST 방식 의미 검색"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = True
            mock_service.search_similar = AsyncMock(return_value=[])

            response = self.client.post(
                "/api/search/semantic",
                json={
                    "query": "긴 검색 쿼리 텍스트",
                    "entity_types": ["Signal"],
                    "top_k": 20,
                    "min_score": 0.8,
                },
            )

        assert response.status_code == 200

    def test_duplicate_check_success(self):
        """중복 검사 성공"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = True
            mock_service.check_signal_duplicate = AsyncMock(
                return_value={
                    "is_duplicate": True,
                    "highest_score": 0.92,
                    "threshold": 0.85,
                    "similar_signals": [
                        {
                            "entity_id": "SIG-001",
                            "score": 0.92,
                            "metadata": {
                                "entity_type": "Signal",
                                "name": "유사 신호",
                                "confidence": 0.9,
                            },
                        },
                    ],
                }
            )

            response = self.client.post(
                "/api/search/duplicates",
                json={
                    "title": "테스트 신호",
                    "pain": "고객 문제점",
                    "threshold": 0.85,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_duplicate"] is True
        assert data["highest_score"] == 0.92
        assert len(data["similar_signals"]) == 1

    def test_duplicate_check_no_duplicate(self):
        """중복 없음"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = True
            mock_service.check_signal_duplicate = AsyncMock(
                return_value={
                    "is_duplicate": False,
                    "highest_score": 0.0,
                    "threshold": 0.85,
                    "similar_signals": [],
                }
            )

            response = self.client.post(
                "/api/search/duplicates",
                json={
                    "title": "새로운 신호",
                    "pain": "새로운 문제",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_duplicate"] is False

    def test_duplicate_check_not_configured(self):
        """서비스 미설정 시 503 오류"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = False

            response = self.client.post(
                "/api/search/duplicates",
                json={
                    "title": "테스트",
                    "pain": "문제",
                },
            )

        assert response.status_code == 503

    def test_context_generate_success(self):
        """Context 생성 성공"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = True
            mock_service.generate_context = AsyncMock(
                return_value="[Signal] 관련 신호\n설명 텍스트"
            )
            mock_service.embedding = MagicMock()
            mock_service.embedding.estimate_tokens = MagicMock(return_value=50)

            response = self.client.post(
                "/api/search/context",
                json={
                    "query": "테스트 쿼리",
                    "max_tokens": 4000,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "[Signal]" in data["context"]
        assert data["estimated_tokens"] == 50

    def test_context_generate_not_configured(self):
        """서비스 미설정 시 503 오류"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = False

            response = self.client.post(
                "/api/search/context",
                json={"query": "테스트"},
            )

        assert response.status_code == 503

    def test_list_entity_types(self):
        """Entity 타입 목록 조회"""
        response = self.client.get("/api/search/entity-types")

        assert response.status_code == 200
        data = response.json()
        assert "entity_types" in data
        assert len(data["entity_types"]) > 0

        # 필수 타입 확인
        type_values = [t["value"] for t in data["entity_types"]]
        assert "Signal" in type_values
        assert "Topic" in type_values
        assert "Customer" in type_values

    def test_semantic_search_empty_query(self):
        """빈 쿼리로 검색 시 오류"""
        response = self.client.get(
            "/api/search/semantic",
            params={"query": ""},
        )

        assert response.status_code == 422  # Validation error

    def test_duplicate_check_validation(self):
        """중복 검사 입력 검증"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = True

            # title 누락
            response = self.client.post(
                "/api/search/duplicates",
                json={"pain": "문제만 있음"},
            )

        assert response.status_code == 422  # Validation error

    def test_semantic_search_top_k_limit(self):
        """top_k 최대값 제한"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = True

            response = self.client.get(
                "/api/search/semantic",
                params={"query": "테스트", "top_k": 100},  # 최대 50
            )

        assert response.status_code == 422  # Validation error

    def test_context_generate_with_entity_types(self):
        """Entity 타입 필터 적용 Context 생성"""
        with patch("backend.api.routers.search.rag_service") as mock_service:
            mock_service.is_configured = True
            mock_service.generate_context = AsyncMock(return_value="Context")
            mock_service.embedding = MagicMock()
            mock_service.embedding.estimate_tokens = MagicMock(return_value=10)

            response = self.client.post(
                "/api/search/context",
                json={
                    "query": "테스트",
                    "entity_types": ["Signal", "Evidence"],
                },
            )

        assert response.status_code == 200
