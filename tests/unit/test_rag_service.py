"""
RAG Service 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.database.models.entity import Entity, EntityType
from backend.integrations.cloudflare_vectorize.client import VectorMatch
from backend.services.rag_service import RAGService


class TestRAGService:
    """RAGService 단위 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_embedding = MagicMock()
        self.mock_vectorize = MagicMock()

    def test_is_configured_both_services(self):
        """양쪽 서비스가 모두 설정된 경우"""
        service = RAGService()
        service.embedding = MagicMock(is_configured=True)
        service.vectorize = MagicMock(is_configured=True)

        assert service.is_configured is True

    def test_is_configured_embedding_only(self):
        """임베딩만 설정된 경우"""
        service = RAGService()
        service.embedding = MagicMock(is_configured=True)
        service.vectorize = MagicMock(is_configured=False)

        assert service.is_configured is False

    def test_is_configured_vectorize_only(self):
        """Vectorize만 설정된 경우"""
        service = RAGService()
        service.embedding = MagicMock(is_configured=False)
        service.vectorize = MagicMock(is_configured=True)

        assert service.is_configured is False

    @pytest.mark.asyncio
    async def test_index_entity_success(self):
        """Entity 인덱싱 성공"""
        service = RAGService()

        # Mock 설정
        service.embedding = MagicMock(is_configured=True)
        service.embedding.create_entity_text = MagicMock(return_value="테스트 텍스트")
        service.embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.upsert = AsyncMock(return_value={"mutationId": "123"})

        # Mock Entity
        entity = MagicMock(spec=Entity)
        entity.entity_id = "SIG-001"
        entity.entity_type = EntityType.SIGNAL
        entity.name = "테스트 신호"
        entity.confidence = 0.9
        entity.external_ref_id = None

        # Mock DB
        mock_db = AsyncMock()

        with patch("backend.services.rag_service.ontology_repo") as mock_repo:
            mock_repo.update_entity = AsyncMock()

            result = await service.index_entity(mock_db, entity)

        assert result is True
        service.embedding.generate_embedding.assert_called_once()
        service.vectorize.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_entity_not_configured(self):
        """서비스 미설정 시 인덱싱 실패"""
        service = RAGService()
        service.embedding = MagicMock(is_configured=False)
        service.vectorize = MagicMock(is_configured=False)

        mock_entity = MagicMock(spec=Entity)
        mock_db = AsyncMock()

        result = await service.index_entity(mock_db, mock_entity)

        assert result is False

    @pytest.mark.asyncio
    async def test_search_similar_success(self):
        """유사도 검색 성공"""
        service = RAGService()

        # Mock 설정
        service.embedding = MagicMock(is_configured=True)
        service.embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.query = AsyncMock(
            return_value=[
                VectorMatch(
                    id="SIG-001",
                    score=0.95,
                    metadata={
                        "entity_type": "Signal",
                        "name": "테스트",
                        "confidence": 0.9,
                    },
                ),
                VectorMatch(
                    id="SIG-002",
                    score=0.8,
                    metadata={
                        "entity_type": "Signal",
                        "name": "테스트2",
                        "confidence": 0.85,
                    },
                ),
            ]
        )

        results = await service.search_similar(
            query="테스트 검색",
            top_k=10,
            min_score=0.7,
        )

        assert len(results) == 2
        assert results[0]["entity_id"] == "SIG-001"
        assert results[0]["score"] == 0.95
        assert results[1]["entity_id"] == "SIG-002"

    @pytest.mark.asyncio
    async def test_search_similar_with_filter(self):
        """타입 필터 적용 유사도 검색"""
        service = RAGService()

        service.embedding = MagicMock(is_configured=True)
        service.embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.query = AsyncMock(return_value=[])

        await service.search_similar(
            query="테스트",
            entity_types=[EntityType.SIGNAL, EntityType.TOPIC],
            top_k=5,
        )

        # query 호출 시 filter 파라미터 확인
        call_args = service.vectorize.query.call_args
        assert "filter" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_search_similar_min_score_filter(self):
        """최소 점수 필터링"""
        service = RAGService()

        service.embedding = MagicMock(is_configured=True)
        service.embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.query = AsyncMock(
            return_value=[
                VectorMatch(
                    id="SIG-001",
                    score=0.9,
                    metadata={"entity_type": "Signal", "name": "A", "confidence": 1.0},
                ),
                VectorMatch(
                    id="SIG-002",
                    score=0.6,
                    metadata={"entity_type": "Signal", "name": "B", "confidence": 1.0},
                ),  # 필터링됨
                VectorMatch(
                    id="SIG-003",
                    score=0.85,
                    metadata={"entity_type": "Signal", "name": "C", "confidence": 1.0},
                ),
            ]
        )

        results = await service.search_similar(
            query="테스트",
            min_score=0.7,
        )

        # 0.6 점수는 필터링됨
        assert len(results) == 2
        assert all(r["score"] >= 0.7 for r in results)

    @pytest.mark.asyncio
    async def test_search_similar_not_configured(self):
        """서비스 미설정 시 검색 실패"""
        service = RAGService()
        service.embedding = MagicMock(is_configured=False)
        service.vectorize = MagicMock(is_configured=False)

        with pytest.raises(RuntimeError, match="설정되지 않았습니다"):
            await service.search_similar(query="테스트")

    @pytest.mark.asyncio
    async def test_find_duplicates_success(self):
        """중복 탐지 성공"""
        service = RAGService()

        service.embedding = MagicMock(is_configured=True)
        service.embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.query = AsyncMock(
            return_value=[
                VectorMatch(
                    id="SIG-001",
                    score=0.92,
                    metadata={"entity_type": "Signal", "name": "유사 신호", "confidence": 0.9},
                ),
            ]
        )

        results = await service.find_duplicates(
            text="테스트 신호 설명",
            entity_type=EntityType.SIGNAL,
            threshold=0.85,
        )

        assert len(results) == 1
        assert results[0]["score"] >= 0.85

    @pytest.mark.asyncio
    async def test_find_duplicates_exclude_ids(self):
        """중복 탐지 시 ID 제외"""
        service = RAGService()

        service.embedding = MagicMock(is_configured=True)
        service.embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.query = AsyncMock(
            return_value=[
                VectorMatch(
                    id="SIG-001",
                    score=0.95,
                    metadata={"entity_type": "Signal", "name": "A", "confidence": 1.0},
                ),
                VectorMatch(
                    id="SIG-002",
                    score=0.90,
                    metadata={"entity_type": "Signal", "name": "B", "confidence": 1.0},
                ),
            ]
        )

        results = await service.find_duplicates(
            text="테스트",
            threshold=0.85,
            exclude_ids=["SIG-001"],  # SIG-001 제외
        )

        assert len(results) == 1
        assert results[0]["entity_id"] == "SIG-002"

    @pytest.mark.asyncio
    async def test_check_signal_duplicate(self):
        """Signal 중복 검사"""
        service = RAGService()

        service.embedding = MagicMock(is_configured=True)
        service.embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        service.embedding.create_signal_text = MagicMock(return_value="Signal 텍스트")

        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.query = AsyncMock(
            return_value=[
                VectorMatch(
                    id="SIG-001",
                    score=0.90,
                    metadata={"entity_type": "Signal", "name": "유사 신호", "confidence": 0.9},
                ),
            ]
        )

        result = await service.check_signal_duplicate(
            title="테스트 신호",
            pain="고객 문제점",
            threshold=0.85,
        )

        assert result["is_duplicate"] is True
        assert result["highest_score"] == 0.90
        assert len(result["similar_signals"]) == 1

    @pytest.mark.asyncio
    async def test_check_signal_duplicate_no_match(self):
        """중복 없는 Signal"""
        service = RAGService()

        service.embedding = MagicMock(is_configured=True)
        service.embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        service.embedding.create_signal_text = MagicMock(return_value="Signal 텍스트")

        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.query = AsyncMock(return_value=[])

        result = await service.check_signal_duplicate(
            title="새로운 신호",
            pain="새로운 문제",
        )

        assert result["is_duplicate"] is False
        assert result["highest_score"] == 0.0
        assert len(result["similar_signals"]) == 0

    @pytest.mark.asyncio
    async def test_generate_context_success(self):
        """Context 생성 성공"""
        service = RAGService()

        service.embedding = MagicMock(is_configured=True)
        service.embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        service.embedding.estimate_tokens = MagicMock(return_value=100)

        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.query = AsyncMock(
            return_value=[
                VectorMatch(
                    id="SIG-001",
                    score=0.9,
                    metadata={"entity_type": "Signal", "name": "관련 신호", "confidence": 0.9},
                ),
            ]
        )

        context = await service.generate_context(
            query="테스트 쿼리",
            max_tokens=4000,
        )

        assert "[Signal]" in context
        assert "관련 신호" in context

    @pytest.mark.asyncio
    async def test_generate_context_empty(self):
        """검색 결과 없을 때 빈 Context"""
        service = RAGService()

        service.embedding = MagicMock(is_configured=True)
        service.embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.query = AsyncMock(return_value=[])

        context = await service.generate_context(query="테스트")

        assert context == ""

    @pytest.mark.asyncio
    async def test_generate_context_not_configured(self):
        """서비스 미설정 시 빈 Context"""
        service = RAGService()
        service.embedding = MagicMock(is_configured=False)
        service.vectorize = MagicMock(is_configured=False)

        context = await service.generate_context(query="테스트")

        assert context == ""

    @pytest.mark.asyncio
    async def test_remove_from_index_success(self):
        """인덱스에서 제거 성공"""
        service = RAGService()
        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.delete = AsyncMock(return_value={"mutationId": "123"})

        result = await service.remove_from_index("SIG-001")

        assert result is True
        service.vectorize.delete.assert_called_once_with(["SIG-001"])

    @pytest.mark.asyncio
    async def test_remove_from_index_not_configured(self):
        """서비스 미설정 시 제거 실패"""
        service = RAGService()
        service.vectorize = MagicMock(is_configured=False)

        result = await service.remove_from_index("SIG-001")

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_all_ok(self):
        """헬스체크 - 모두 정상"""
        service = RAGService()
        service.embedding = MagicMock(is_configured=True)
        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.health_check = AsyncMock(return_value=True)

        status = await service.health_check()

        assert status["embedding"] is True
        assert status["vectorize"] is True
        assert status["overall"] is True

    @pytest.mark.asyncio
    async def test_health_check_partial_failure(self):
        """헬스체크 - 일부 실패"""
        service = RAGService()
        service.embedding = MagicMock(is_configured=True)
        service.vectorize = MagicMock(is_configured=True)
        service.vectorize.health_check = AsyncMock(return_value=False)

        status = await service.health_check()

        assert status["embedding"] is True
        assert status["vectorize"] is False
        assert status["overall"] is False
