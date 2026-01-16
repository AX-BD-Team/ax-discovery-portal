"""
Cloudflare Vectorize 유스케이스 단위 테스트
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.integrations.cloudflare_vectorize.client import VectorMatch, VectorMetadata
from backend.integrations.cloudflare_vectorize.use_cases import (
    DuplicateCandidate,
    EntityLinkCandidate,
    PlayRecommendation,
    VectorIndexType,
    VectorizeUseCases,
)


class TestDataclasses:
    """데이터클래스 테스트"""

    def test_duplicate_candidate_to_dict(self):
        """DuplicateCandidate to_dict 테스트"""
        candidate = DuplicateCandidate(
            signal_id="SIG-001",
            score=0.95,
            title="테스트 Signal",
            status="NEW",
            play_id="PLAY-001",
        )

        result = candidate.to_dict()

        assert result["signal_id"] == "SIG-001"
        assert result["score"] == 0.95
        assert result["title"] == "테스트 Signal"
        assert result["status"] == "NEW"
        assert result["play_id"] == "PLAY-001"

    def test_duplicate_candidate_with_none_values(self):
        """DuplicateCandidate None 값 처리"""
        candidate = DuplicateCandidate(signal_id="SIG-001", score=0.5)

        result = candidate.to_dict()

        assert result["title"] is None
        assert result["status"] is None
        assert result["play_id"] is None

    def test_entity_link_candidate_to_dict(self):
        """EntityLinkCandidate to_dict 테스트"""
        candidate = EntityLinkCandidate(
            entity_id="ENT-001",
            entity_type="Organization",
            name="테스트 회사",
            score=0.85,
            properties={"industry": "IT"},
        )

        result = candidate.to_dict()

        assert result["entity_id"] == "ENT-001"
        assert result["entity_type"] == "Organization"
        assert result["name"] == "테스트 회사"
        assert result["score"] == 0.85
        assert result["properties"]["industry"] == "IT"

    def test_entity_link_candidate_without_properties(self):
        """EntityLinkCandidate 속성 없이"""
        candidate = EntityLinkCandidate(
            entity_id="ENT-001",
            entity_type="Technology",
            name="Python",
            score=0.9,
        )

        result = candidate.to_dict()

        assert result["properties"] is None

    def test_play_recommendation_to_dict(self):
        """PlayRecommendation to_dict 테스트"""
        recommendation = PlayRecommendation(
            play_id="PLAY-001",
            score=0.88,
            similar_signals=["SIG-001", "SIG-002"],
            success_count=5,
        )

        result = recommendation.to_dict()

        assert result["play_id"] == "PLAY-001"
        assert result["score"] == 0.88
        assert len(result["similar_signals"]) == 2
        assert result["success_count"] == 5

    def test_play_recommendation_default_values(self):
        """PlayRecommendation 기본값 테스트"""
        recommendation = PlayRecommendation(play_id="PLAY-001", score=0.7)

        assert recommendation.similar_signals == []
        assert recommendation.success_count == 0

    def test_vector_index_type_enum(self):
        """VectorIndexType enum 테스트"""
        assert VectorIndexType.SIGNAL.value == "signal"
        assert VectorIndexType.ENTITY.value == "entity"
        assert VectorIndexType.EVIDENCE.value == "evidence"


class TestVectorizeUseCases:
    """VectorizeUseCases 테스트"""

    def setup_method(self):
        """테스트 설정"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "test_account",
            "CLOUDFLARE_API_TOKEN": "test_token",
            "VECTORIZE_SIGNAL_INDEX": "test-signals",
            "VECTORIZE_ENTITY_INDEX": "test-entities",
            "VECTORIZE_EVIDENCE_INDEX": "test-evidence",
        }
        with patch.dict("os.environ", env_vars):
            self.use_cases = VectorizeUseCases()

    @pytest.mark.asyncio
    async def test_detect_similar_signals_not_configured(self):
        """미설정 시 빈 목록 반환"""
        with patch.dict("os.environ", {}, clear=True):
            use_cases = VectorizeUseCases()
            use_cases.signal_client._VectorizeClient__is_configured = False

            with patch.object(use_cases.signal_client, "is_configured", False):
                result = await use_cases.detect_similar_signals(
                    embedding=[0.1] * 1536, top_k=5
                )

        assert result == []

    @pytest.mark.asyncio
    async def test_detect_similar_signals_success(self):
        """유사 Signal 탐지 성공"""
        mock_matches = [
            MagicMock(
                id="SIG-001",
                score=0.95,
                metadata=MagicMock(
                    name="테스트 Signal 1",
                    extra={"status": "NEW", "play_id": "PLAY-001"},
                ),
            ),
            MagicMock(
                id="SIG-002",
                score=0.85,
                metadata=MagicMock(
                    name="테스트 Signal 2",
                    extra={"status": "EVALUATED", "play_id": "PLAY-002"},
                ),
            ),
        ]

        self.use_cases.signal_client.query = AsyncMock(return_value=mock_matches)

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.detect_similar_signals(
                embedding=[0.1] * 1536,
                top_k=5,
                min_similarity=0.8,
            )

        assert len(result) == 2
        assert result[0].signal_id == "SIG-001"
        assert result[0].score == 0.95
        assert result[1].signal_id == "SIG-002"

    @pytest.mark.asyncio
    async def test_detect_similar_signals_with_exclude_ids(self):
        """제외 ID 필터링"""
        mock_matches = [
            MagicMock(
                id="SIG-001",
                score=0.95,
                metadata=MagicMock(name="Signal 1", extra={}),
            ),
            MagicMock(
                id="SIG-002",
                score=0.85,
                metadata=MagicMock(name="Signal 2", extra={}),
            ),
        ]

        self.use_cases.signal_client.query = AsyncMock(return_value=mock_matches)

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.detect_similar_signals(
                embedding=[0.1] * 1536,
                top_k=5,
                exclude_ids=["SIG-001"],
            )

        assert len(result) == 1
        assert result[0].signal_id == "SIG-002"

    @pytest.mark.asyncio
    async def test_detect_similar_signals_below_threshold(self):
        """유사도 임계값 미만 필터링"""
        mock_matches = [
            MagicMock(id="SIG-001", score=0.75, metadata=MagicMock(name="", extra={})),
            MagicMock(id="SIG-002", score=0.65, metadata=MagicMock(name="", extra={})),
        ]

        self.use_cases.signal_client.query = AsyncMock(return_value=mock_matches)

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.detect_similar_signals(
                embedding=[0.1] * 1536,
                top_k=5,
                min_similarity=0.8,
            )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_detect_similar_signals_exception(self):
        """예외 시 빈 목록 반환"""
        self.use_cases.signal_client.query = AsyncMock(
            side_effect=Exception("Query failed")
        )

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.detect_similar_signals(
                embedding=[0.1] * 1536
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_find_entity_candidates_not_configured(self):
        """Entity 클라이언트 미설정"""
        with patch.object(self.use_cases.entity_client, "is_configured", False):
            result = await self.use_cases.find_entity_candidates(
                text="삼성전자",
                embedding=[0.1] * 1536,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_find_entity_candidates_success(self):
        """Entity Linking 후보 검색 성공"""
        mock_matches = [
            MagicMock(
                id="ENT-001",
                score=0.9,
                metadata=MagicMock(
                    entity_type="Organization",
                    name="삼성전자",
                    extra={"industry": "Electronics"},
                ),
            ),
        ]

        self.use_cases.entity_client.query = AsyncMock(return_value=mock_matches)

        with patch.object(self.use_cases.entity_client, "is_configured", True):
            result = await self.use_cases.find_entity_candidates(
                text="삼전",
                embedding=[0.1] * 1536,
                entity_types=["Organization"],
                min_similarity=0.7,
            )

        assert len(result) == 1
        assert result[0].entity_id == "ENT-001"
        assert result[0].entity_type == "Organization"
        assert result[0].name == "삼성전자"

    @pytest.mark.asyncio
    async def test_find_entity_candidates_exception(self):
        """Entity 검색 예외 처리"""
        self.use_cases.entity_client.query = AsyncMock(
            side_effect=Exception("Query failed")
        )

        with patch.object(self.use_cases.entity_client, "is_configured", True):
            result = await self.use_cases.find_entity_candidates(
                text="테스트",
                embedding=[0.1] * 1536,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_find_organization_by_alias(self):
        """별칭으로 Organization 찾기"""
        mock_matches = [
            MagicMock(
                id="ENT-001",
                score=0.8,
                metadata=MagicMock(
                    entity_type="Organization",
                    name="KT",
                    extra={},
                ),
            ),
        ]

        self.use_cases.entity_client.query = AsyncMock(return_value=mock_matches)

        with patch.object(self.use_cases.entity_client, "is_configured", True):
            result = await self.use_cases.find_organization_by_alias(
                alias="케이티",
                embedding=[0.1] * 1536,
            )

        assert len(result) == 1
        assert result[0].name == "KT"

    @pytest.mark.asyncio
    async def test_recommend_plays_not_configured(self):
        """Play 추천 미설정"""
        with patch.object(self.use_cases.signal_client, "is_configured", False):
            result = await self.use_cases.recommend_plays(
                signal_embedding=[0.1] * 1536
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_recommend_plays_success(self):
        """Play 추천 성공"""
        mock_matches = [
            MagicMock(
                id="SIG-001",
                score=0.9,
                metadata=MagicMock(extra={"play_id": "PLAY-001", "status": "PILOT_READY"}),
            ),
            MagicMock(
                id="SIG-002",
                score=0.85,
                metadata=MagicMock(extra={"play_id": "PLAY-001", "status": "VALIDATED"}),
            ),
            MagicMock(
                id="SIG-003",
                score=0.8,
                metadata=MagicMock(extra={"play_id": "PLAY-002", "status": "PILOT_READY"}),
            ),
        ]

        self.use_cases.signal_client.query = AsyncMock(return_value=mock_matches)

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.recommend_plays(
                signal_embedding=[0.1] * 1536,
                top_k=3,
            )

        assert len(result) == 2
        # PLAY-001이 더 높은 점수와 더 많은 성공 수
        assert result[0].play_id == "PLAY-001"
        assert result[0].success_count == 2
        assert result[0].score == 0.9

    @pytest.mark.asyncio
    async def test_recommend_plays_no_play_id(self):
        """play_id 없는 결과 무시"""
        mock_matches = [
            MagicMock(
                id="SIG-001",
                score=0.9,
                metadata=MagicMock(extra={}),  # play_id 없음
            ),
        ]

        self.use_cases.signal_client.query = AsyncMock(return_value=mock_matches)

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.recommend_plays(
                signal_embedding=[0.1] * 1536
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_recommend_plays_exception(self):
        """Play 추천 예외 처리"""
        self.use_cases.signal_client.query = AsyncMock(
            side_effect=Exception("Query failed")
        )

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.recommend_plays(
                signal_embedding=[0.1] * 1536
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_index_signal_not_configured(self):
        """Signal 인덱싱 미설정"""
        with patch.object(self.use_cases.signal_client, "is_configured", False):
            result = await self.use_cases.index_signal(
                signal_id="SIG-001",
                embedding=[0.1] * 1536,
                title="테스트",
                status="NEW",
                channel="데스크리서치",
                play_id="PLAY-001",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_index_signal_success(self):
        """Signal 인덱싱 성공"""
        self.use_cases.signal_client.upsert = AsyncMock(return_value={})

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.index_signal(
                signal_id="SIG-001",
                embedding=[0.1] * 1536,
                title="테스트 Signal",
                status="NEW",
                channel="데스크리서치",
                play_id="PLAY-001",
                created_at=datetime(2026, 1, 15, tzinfo=UTC),
            )

        assert result is True
        self.use_cases.signal_client.upsert.assert_called_once()
        call_args = self.use_cases.signal_client.upsert.call_args[0][0]
        assert call_args[0]["id"] == "SIG-001"
        assert call_args[0]["metadata"]["created_at_bucket"] == "2026-01"

    @pytest.mark.asyncio
    async def test_index_signal_exception(self):
        """Signal 인덱싱 예외"""
        self.use_cases.signal_client.upsert = AsyncMock(
            side_effect=Exception("Upsert failed")
        )

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.index_signal(
                signal_id="SIG-001",
                embedding=[0.1] * 1536,
                title="테스트",
                status="NEW",
                channel="CH",
                play_id="PLAY",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_index_entity_not_configured(self):
        """Entity 인덱싱 미설정"""
        with patch.object(self.use_cases.entity_client, "is_configured", False):
            result = await self.use_cases.index_entity(
                entity_id="ENT-001",
                entity_type="Organization",
                name="테스트 회사",
                embedding=[0.1] * 1536,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_index_entity_success(self):
        """Entity 인덱싱 성공"""
        self.use_cases.entity_client.upsert = AsyncMock(return_value={})

        with patch.object(self.use_cases.entity_client, "is_configured", True):
            result = await self.use_cases.index_entity(
                entity_id="ENT-001",
                entity_type="Organization",
                name="테스트 회사",
                embedding=[0.1] * 1536,
                properties={"industry": "IT", "canonical_name": "Test Corp"},
            )

        assert result is True
        call_args = self.use_cases.entity_client.upsert.call_args[0][0]
        assert call_args[0]["metadata"]["industry"] == "IT"
        assert call_args[0]["metadata"]["canonical_name"] == "Test Corp"

    @pytest.mark.asyncio
    async def test_index_entity_exception(self):
        """Entity 인덱싱 예외"""
        self.use_cases.entity_client.upsert = AsyncMock(
            side_effect=Exception("Upsert failed")
        )

        with patch.object(self.use_cases.entity_client, "is_configured", True):
            result = await self.use_cases.index_entity(
                entity_id="ENT-001",
                entity_type="Organization",
                name="테스트",
                embedding=[0.1] * 1536,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_from_index_not_configured(self):
        """인덱스 삭제 미설정"""
        with patch.object(self.use_cases.signal_client, "is_configured", False):
            result = await self.use_cases.remove_from_index(
                ids=["SIG-001"],
                index_type=VectorIndexType.SIGNAL,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_from_index_signal(self):
        """Signal 인덱스에서 삭제"""
        self.use_cases.signal_client.delete = AsyncMock(return_value={})

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.remove_from_index(
                ids=["SIG-001", "SIG-002"],
                index_type=VectorIndexType.SIGNAL,
            )

        assert result is True
        self.use_cases.signal_client.delete.assert_called_once_with(
            ["SIG-001", "SIG-002"]
        )

    @pytest.mark.asyncio
    async def test_remove_from_index_entity(self):
        """Entity 인덱스에서 삭제"""
        self.use_cases.entity_client.delete = AsyncMock(return_value={})

        with patch.object(self.use_cases.entity_client, "is_configured", True):
            result = await self.use_cases.remove_from_index(
                ids=["ENT-001"],
                index_type=VectorIndexType.ENTITY,
            )

        assert result is True
        self.use_cases.entity_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_from_index_evidence(self):
        """Evidence 인덱스에서 삭제"""
        self.use_cases.evidence_client.delete = AsyncMock(return_value={})

        with patch.object(self.use_cases.evidence_client, "is_configured", True):
            result = await self.use_cases.remove_from_index(
                ids=["EVI-001"],
                index_type=VectorIndexType.EVIDENCE,
            )

        assert result is True
        self.use_cases.evidence_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_from_index_exception(self):
        """인덱스 삭제 예외"""
        self.use_cases.signal_client.delete = AsyncMock(
            side_effect=Exception("Delete failed")
        )

        with patch.object(self.use_cases.signal_client, "is_configured", True):
            result = await self.use_cases.remove_from_index(
                ids=["SIG-001"],
                index_type=VectorIndexType.SIGNAL,
            )

        assert result is False


class TestVectorMetadata:
    """VectorMetadata 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환"""
        metadata = VectorMetadata(
            entity_type="Signal",
            name="테스트",
            confidence=0.95,
            external_ref_id="EXT-001",
            custom_field="value",
        )

        result = metadata.to_dict()

        assert result["entity_type"] == "Signal"
        assert result["name"] == "테스트"
        assert result["confidence"] == 0.95
        assert result["external_ref_id"] == "EXT-001"
        assert result["custom_field"] == "value"

    def test_from_dict(self):
        """딕셔너리에서 생성"""
        data = {
            "entity_type": "Organization",
            "name": "테스트 회사",
            "confidence": 0.8,
            "external_ref_id": "EXT-002",
            "industry": "IT",
        }

        metadata = VectorMetadata.from_dict(data)

        assert metadata.entity_type == "Organization"
        assert metadata.name == "테스트 회사"
        assert metadata.confidence == 0.8
        assert metadata.external_ref_id == "EXT-002"
        assert metadata.extra["industry"] == "IT"

    def test_from_dict_defaults(self):
        """기본값 처리"""
        data = {}

        metadata = VectorMetadata.from_dict(data)

        assert metadata.entity_type == ""
        assert metadata.name == ""
        assert metadata.confidence == 1.0
        assert metadata.external_ref_id is None


class TestVectorMatch:
    """VectorMatch 테스트"""

    def test_with_metadata(self):
        """메타데이터가 있는 경우"""
        match = VectorMatch(
            id="SIG-001",
            score=0.95,
            metadata={"entity_type": "Signal", "name": "테스트", "confidence": 0.9},
        )

        assert match.id == "SIG-001"
        assert match.score == 0.95
        assert match.metadata.entity_type == "Signal"
        assert match.metadata.name == "테스트"

    def test_without_metadata(self):
        """메타데이터가 없는 경우"""
        match = VectorMatch(id="SIG-001", score=0.8, metadata=None)

        assert match.id == "SIG-001"
        assert match.metadata is None

    def test_to_dict(self):
        """딕셔너리 변환"""
        match = VectorMatch(
            id="SIG-001",
            score=0.9,
            metadata={"entity_type": "Signal", "name": "테스트", "confidence": 1.0},
        )

        result = match.to_dict()

        assert result["id"] == "SIG-001"
        assert result["score"] == 0.9
        assert result["metadata"]["entity_type"] == "Signal"

    def test_to_dict_without_metadata(self):
        """메타데이터 없이 딕셔너리 변환"""
        match = VectorMatch(id="SIG-001", score=0.8, metadata=None)

        result = match.to_dict()

        assert result["metadata"] is None
