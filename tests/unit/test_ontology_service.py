"""
Ontology Service 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.database.models.entity import Entity, EntityType
from backend.database.models.triple import PredicateType
from backend.services.ontology_service import OntologyService


class TestOntologyService:
    """OntologyService 단위 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_db = AsyncMock()
        self.mock_entity = MagicMock(spec=Entity)
        self.mock_entity.entity_id = "SIG-001"
        self.mock_entity.entity_type = EntityType.SIGNAL
        self.mock_entity.name = "테스트 신호"

    def test_init_auto_index_enabled(self):
        """자동 인덱싱 활성화 상태로 초기화"""
        service = OntologyService(auto_index=True)
        assert service.auto_index is True

    def test_init_auto_index_disabled(self):
        """자동 인덱싱 비활성화 상태로 초기화"""
        service = OntologyService(auto_index=False)
        assert service.auto_index is False

    @pytest.mark.asyncio
    async def test_create_entity_with_auto_index(self):
        """Entity 생성 + 자동 인덱싱"""
        service = OntologyService(auto_index=True)

        with (
            patch.object(service, "repo") as mock_repo,
            patch.object(service, "_index_entity") as mock_index,
        ):
            mock_repo.create_entity = AsyncMock(return_value=self.mock_entity)
            mock_index.return_value = True

            entity = await service.create_entity(
                db=self.mock_db,
                entity_type=EntityType.SIGNAL,
                name="테스트 신호",
            )

        assert entity == self.mock_entity
        mock_repo.create_entity.assert_called_once()
        mock_index.assert_called_once_with(self.mock_db, self.mock_entity)

    @pytest.mark.asyncio
    async def test_create_entity_without_auto_index(self):
        """Entity 생성 (자동 인덱싱 비활성화)"""
        service = OntologyService(auto_index=False)

        with (
            patch.object(service, "repo") as mock_repo,
            patch.object(service, "_index_entity") as mock_index,
        ):
            mock_repo.create_entity = AsyncMock(return_value=self.mock_entity)

            entity = await service.create_entity(
                db=self.mock_db,
                entity_type=EntityType.SIGNAL,
                name="테스트 신호",
            )

        assert entity == self.mock_entity
        mock_index.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_entity_override_auto_index(self):
        """Entity 생성 시 auto_index 파라미터로 오버라이드"""
        service = OntologyService(auto_index=True)

        with (
            patch.object(service, "repo") as mock_repo,
            patch.object(service, "_index_entity") as mock_index,
        ):
            mock_repo.create_entity = AsyncMock(return_value=self.mock_entity)

            # 서비스는 auto_index=True지만 파라미터로 False 지정
            await service.create_entity(
                db=self.mock_db,
                entity_type=EntityType.SIGNAL,
                name="테스트",
                auto_index=False,
            )

        mock_index.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_entity_batch_with_auto_index(self):
        """Entity 배치 생성 + 자동 인덱싱"""
        service = OntologyService(auto_index=True)

        mock_entities = [
            MagicMock(spec=Entity, entity_id="SIG-001"),
            MagicMock(spec=Entity, entity_id="SIG-002"),
        ]

        with (
            patch.object(service, "repo") as mock_repo,
            patch.object(service, "_index_entities_batch") as mock_batch_index,
        ):
            mock_repo.create_entity = AsyncMock(side_effect=mock_entities)
            mock_batch_index.return_value = {"success": 2, "failed": 0, "total": 2}

            entities_data = [
                {"entity_type": EntityType.SIGNAL, "name": "신호1"},
                {"entity_type": EntityType.SIGNAL, "name": "신호2"},
            ]

            entities = await service.create_entity_batch(
                db=self.mock_db,
                entities_data=entities_data,
            )

        assert len(entities) == 2
        mock_batch_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_entity_with_reindex(self):
        """Entity 업데이트 + 재인덱싱"""
        service = OntologyService(auto_index=True)

        with (
            patch.object(service, "repo") as mock_repo,
            patch.object(service, "_index_entity") as mock_index,
        ):
            mock_repo.update_entity = AsyncMock(return_value=self.mock_entity)
            mock_index.return_value = True

            entity = await service.update_entity(
                db=self.mock_db,
                entity_id="SIG-001",
                name="업데이트된 이름",  # 인덱싱 필드 변경
                reindex=True,
            )

        assert entity == self.mock_entity
        mock_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_entity_no_reindex_needed(self):
        """Entity 업데이트 (인덱싱 필드 아님)"""
        service = OntologyService(auto_index=True)

        with (
            patch.object(service, "repo") as mock_repo,
            patch.object(service, "_index_entity") as mock_index,
        ):
            mock_repo.update_entity = AsyncMock(return_value=self.mock_entity)

            await service.update_entity(
                db=self.mock_db,
                entity_id="SIG-001",
                confidence=0.9,  # 인덱싱 필드가 아님
            )

        mock_index.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_entity_with_index_removal(self):
        """Entity 삭제 + 인덱스 제거"""
        service = OntologyService()

        with (
            patch.object(service, "repo") as mock_repo,
            patch("backend.services.ontology_service.rag_service") as mock_rag,
        ):
            mock_repo.delete_entity = AsyncMock(return_value=True)
            mock_rag.remove_from_index = AsyncMock(return_value=True)

            result = await service.delete_entity(
                db=self.mock_db,
                entity_id="SIG-001",
                remove_from_index=True,
            )

        assert result is True
        mock_rag.remove_from_index.assert_called_once_with("SIG-001")

    @pytest.mark.asyncio
    async def test_delete_entity_without_index_removal(self):
        """Entity 삭제 (인덱스 제거 안 함)"""
        service = OntologyService()

        with (
            patch.object(service, "repo") as mock_repo,
            patch("backend.services.ontology_service.rag_service") as mock_rag,
        ):
            mock_repo.delete_entity = AsyncMock(return_value=True)

            await service.delete_entity(
                db=self.mock_db,
                entity_id="SIG-001",
                remove_from_index=False,
            )

        mock_rag.remove_from_index.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_signal_entity(self):
        """Signal Entity 생성 (편의 메서드)"""
        service = OntologyService(auto_index=True)

        with patch.object(service, "create_entity") as mock_create:
            mock_create.return_value = self.mock_entity

            entity = await service.create_signal_entity(
                db=self.mock_db,
                signal_id="SIG-2025-001",
                title="AI 데이터 분석",
                pain="분석 역량 부족",
                proposed_value="AI 플랫폼",
                customer_segment="금융",
            )

        assert entity == self.mock_entity

        # create_entity 호출 검증
        call_args = mock_create.call_args
        assert call_args.kwargs["entity_type"] == EntityType.SIGNAL
        assert call_args.kwargs["name"] == "AI 데이터 분석"
        assert call_args.kwargs["external_ref_id"] == "SIG-2025-001"
        assert call_args.kwargs["properties"]["pain"] == "분석 역량 부족"

    @pytest.mark.asyncio
    async def test_create_topic_entity_with_parent(self):
        """Topic Entity 생성 (부모 있음)"""
        service = OntologyService(auto_index=True)

        mock_topic = MagicMock(spec=Entity, entity_id="TOP-001")

        with (
            patch.object(service, "create_entity") as mock_create,
            patch.object(service, "create_triple") as mock_triple,
        ):
            mock_create.return_value = mock_topic

            entity = await service.create_topic_entity(
                db=self.mock_db,
                name="하위 토픽",
                parent_topic_id="TOP-PARENT",
            )

        assert entity == mock_topic

        # 부모-자식 관계 생성 확인
        mock_triple.assert_called_once()
        triple_args = mock_triple.call_args
        assert triple_args.kwargs["subject_id"] == "TOP-PARENT"
        assert triple_args.kwargs["predicate"] == PredicateType.PARENT_OF
        assert triple_args.kwargs["object_id"] == "TOP-001"

    @pytest.mark.asyncio
    async def test_create_evidence_entity(self):
        """Evidence Entity 생성"""
        service = OntologyService(auto_index=True)

        mock_evidence = MagicMock(spec=Entity, entity_id="EVD-001")

        with patch.object(service, "create_entity") as mock_create:
            mock_create.return_value = mock_evidence

            entity = await service.create_evidence_entity(
                db=self.mock_db,
                title="2024 시장 리포트",
                evidence_type="MARKET_DATA",
                source_url="https://example.com/report",
                content_summary="시장 동향 분석",
                credibility=0.9,
            )

        assert entity == mock_evidence

        call_args = mock_create.call_args
        assert call_args.kwargs["entity_type"] == EntityType.EVIDENCE
        assert call_args.kwargs["properties"]["evidence_type"] == "MARKET_DATA"
        assert call_args.kwargs["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_index_entity_rag_not_configured(self):
        """RAG 미설정 시 인덱싱 스킵"""
        service = OntologyService(auto_index=True)

        with patch("backend.services.ontology_service.rag_service") as mock_rag:
            mock_rag.is_configured = False

            result = await service._index_entity(self.mock_db, self.mock_entity)

        assert result is False

    @pytest.mark.asyncio
    async def test_index_entity_success(self):
        """Entity 인덱싱 성공"""
        service = OntologyService(auto_index=True)

        with patch("backend.services.ontology_service.rag_service") as mock_rag:
            mock_rag.is_configured = True
            mock_rag.index_entity = AsyncMock(return_value=True)

            result = await service._index_entity(self.mock_db, self.mock_entity)

        assert result is True
        mock_rag.index_entity.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_entity_failure(self):
        """Entity 인덱싱 실패"""
        service = OntologyService(auto_index=True)

        with patch("backend.services.ontology_service.rag_service") as mock_rag:
            mock_rag.is_configured = True
            mock_rag.index_entity = AsyncMock(side_effect=Exception("API Error"))

            result = await service._index_entity(self.mock_db, self.mock_entity)

        assert result is False

    @pytest.mark.asyncio
    async def test_create_triple(self):
        """Triple 생성"""
        service = OntologyService()

        mock_triple = MagicMock()

        with patch.object(service, "repo") as mock_repo:
            mock_repo.create_triple = AsyncMock(return_value=mock_triple)

            triple = await service.create_triple(
                db=self.mock_db,
                subject_id="SIG-001",
                predicate=PredicateType.HAS_PAIN,
                object_id="TOP-001",
            )

        assert triple == mock_triple

    @pytest.mark.asyncio
    async def test_delete_triple(self):
        """Triple 삭제"""
        service = OntologyService()

        with patch.object(service, "repo") as mock_repo:
            mock_repo.delete_triple = AsyncMock(return_value=True)

            result = await service.delete_triple(
                db=self.mock_db,
                triple_id="TRP-001",
            )

        assert result is True


class TestOntologyServiceSingletons:
    """싱글톤 인스턴스 테스트"""

    def test_ontology_service_auto_index_enabled(self):
        """ontology_service는 auto_index=True"""
        from backend.services import ontology_service

        assert ontology_service.auto_index is True

    def test_ontology_service_no_index_disabled(self):
        """ontology_service_no_index는 auto_index=False"""
        from backend.services import ontology_service_no_index

        assert ontology_service_no_index.auto_index is False
