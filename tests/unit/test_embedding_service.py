"""
Embedding Service 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.database.models.entity import Entity, EntityType
from backend.services.embedding_service import EmbeddingService


class TestEmbeddingService:
    """EmbeddingService 단위 테스트"""

    def test_init_default_model(self):
        """기본 모델로 초기화"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        assert service.model == "text-embedding-3-small"
        assert service.dimension == 1536
        assert service.is_configured is True

    def test_init_large_model(self):
        """large 모델로 초기화"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService(model="text-embedding-3-large")

        assert service.model == "text-embedding-3-large"
        assert service.dimension == 3072

    def test_init_invalid_model(self):
        """지원하지 않는 모델로 초기화 시 오류"""
        with pytest.raises(ValueError, match="지원하지 않는 모델"):
            EmbeddingService(model="invalid-model")

    def test_is_configured_without_api_key(self):
        """API 키 없이 초기화"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=True):
            service = EmbeddingService()

        assert service.is_configured is False

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self):
        """임베딩 생성 성공"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        mock_embedding = [0.1] * 1536

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": mock_embedding}],
            "usage": {"prompt_tokens": 10, "total_tokens": 10},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await service.generate_embedding("테스트 텍스트")

        assert result == mock_embedding
        assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self):
        """빈 텍스트로 임베딩 생성 시 오류"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        with pytest.raises(ValueError, match="비어있습니다"):
            await service.generate_embedding("")

    @pytest.mark.asyncio
    async def test_generate_embedding_not_configured(self):
        """API 키 미설정 시 오류"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=True):
            service = EmbeddingService()

        with pytest.raises(RuntimeError, match="설정되지 않았습니다"):
            await service.generate_embedding("테스트")

    @pytest.mark.asyncio
    async def test_generate_batch_success(self):
        """배치 임베딩 생성 성공"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        mock_embeddings = [[0.1] * 1536, [0.2] * 1536]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"embedding": mock_embeddings[0]},
                {"embedding": mock_embeddings[1]},
            ],
            "usage": {"prompt_tokens": 20, "total_tokens": 20},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await service.generate_batch(["텍스트1", "텍스트2"])

        assert len(result) == 2
        assert result == mock_embeddings

    @pytest.mark.asyncio
    async def test_generate_batch_empty_list(self):
        """빈 리스트로 배치 임베딩 생성"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        result = await service.generate_batch([])
        assert result == []

    def test_create_entity_text_signal(self):
        """Signal Entity 텍스트 변환"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        entity = MagicMock(spec=Entity)
        entity.entity_type = EntityType.SIGNAL
        entity.name = "고객 데이터 분석 기회"
        entity.description = "금융권 고객 데이터 분석 솔루션 제안"
        entity.properties = {
            "pain": "데이터 분석 역량 부족",
            "proposed_value": "AI 기반 분석 플랫폼",
        }

        text = service.create_entity_text(entity)

        assert "[Signal]" in text
        assert "고객 데이터 분석 기회" in text
        assert "Pain:" in text
        assert "Value:" in text

    def test_create_entity_text_customer(self):
        """Customer Entity 텍스트 변환"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        entity = MagicMock(spec=Entity)
        entity.entity_type = EntityType.CUSTOMER
        entity.name = "KT 금융IT"
        entity.description = "KT 그룹 금융 IT 사업부"
        entity.properties = {"segment": "금융"}

        text = service.create_entity_text(entity)

        assert "[Customer]" in text
        assert "KT 금융IT" in text
        assert "Segment:" in text

    def test_create_signal_text(self):
        """Signal 데이터 텍스트 변환"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        text = service.create_signal_text(
            title="AI 데이터 분석",
            pain="분석 역량 부족",
            proposed_value="AI 플랫폼",
            customer_segment="금융",
        )

        assert "[Signal]" in text
        assert "AI 데이터 분석" in text
        assert "Pain:" in text
        assert "Value:" in text
        assert "Customer:" in text

    @pytest.mark.asyncio
    async def test_compute_similarity(self):
        """코사인 유사도 계산"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        # 동일한 벡터 → 유사도 1.0
        vec = [1.0, 0.0, 0.0]
        similarity = await service.compute_similarity(vec, vec)
        assert similarity == pytest.approx(1.0)

        # 직교 벡터 → 유사도 0.5 (정규화 후)
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = await service.compute_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.5)

        # 반대 벡터 → 유사도 0.0
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = await service.compute_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_compute_similarity_dimension_mismatch(self):
        """차원 불일치 시 오류"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        with pytest.raises(ValueError, match="차원이 일치하지"):
            await service.compute_similarity([1.0, 0.0], [1.0, 0.0, 0.0])

    def test_estimate_tokens(self):
        """토큰 수 추정"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EmbeddingService()

        # 10자 → 약 5토큰
        tokens = service.estimate_tokens("1234567890")
        assert tokens == 5

        # 한글 10자 → 약 5토큰
        tokens = service.estimate_tokens("가나다라마바사아자차")
        assert tokens == 5
