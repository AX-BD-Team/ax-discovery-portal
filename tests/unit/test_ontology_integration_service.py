"""
Ontology Integration Service 단위 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.database.models.entity import Entity, EntityType
from backend.database.models.triple import PredicateType, Triple
from backend.services.entity_resolution_service import EntityMatch, ResolutionResult
from backend.services.llm_extraction_service import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
)
from backend.services.ontology_integration_service import (
    OntologyCreationResult,
    OntologyIntegrationService,
)


class TestOntologyCreationResult:
    """OntologyCreationResult 테스트"""

    def test_default_values(self):
        """기본값 테스트"""
        result = OntologyCreationResult()

        assert result.created_entities == []
        assert result.merged_entities == []
        assert result.created_triples == []
        assert result.skipped_triples == []
        assert result.same_as_triples == []
        assert result.errors == []
        assert result.entity_created_count == 0
        assert result.entity_merged_count == 0
        assert result.triple_created_count == 0
        assert result.triple_skipped_count == 0

    def test_to_dict(self):
        """to_dict 변환 테스트"""
        # 가짜 Entity 생성
        entity = MagicMock(spec=Entity)
        entity.to_dict.return_value = {
            "entity_id": "ORG-12345678",
            "name": "테스트",
        }
        entity.entity_id = "ORG-12345678"

        extracted = ExtractedEntity(name="테스트", entity_type=EntityType.ORGANIZATION)

        result = OntologyCreationResult(
            created_entities=[entity],
            merged_entities=[(extracted, entity)],
            entity_created_count=1,
            entity_merged_count=1,
        )

        dict_result = result.to_dict()

        assert "created_entities" in dict_result
        assert "merged_entities" in dict_result
        assert "statistics" in dict_result
        assert dict_result["statistics"]["entity_created"] == 1
        assert dict_result["statistics"]["entity_merged"] == 1


class TestOntologyIntegrationService:
    """OntologyIntegrationService 테스트"""

    @pytest.fixture
    def mock_resolution_service(self):
        """목 Entity Resolution 서비스"""
        service = MagicMock()
        service.resolve_entities = AsyncMock()
        return service

    @pytest.fixture
    def service(self, mock_resolution_service):
        """테스트용 서비스 인스턴스"""
        return OntologyIntegrationService(resolution_service=mock_resolution_service)

    @pytest.fixture
    def mock_db(self):
        """목 데이터베이스 세션"""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_create_activity_entity(self, service, mock_db):
        """Activity Entity 생성 테스트"""
        # 목 ontology_repo 설정
        mock_entity = MagicMock(spec=Entity)
        mock_entity.entity_id = "ACT-12345678"
        mock_entity.name = "AWS re:Invent 2025"

        with patch("backend.services.ontology_integration_service.ontology_repo") as mock_repo:
            mock_repo.create_entity = AsyncMock(return_value=mock_entity)

            entity = await service.create_activity_entity(
                db=mock_db,
                activity_id="ACT-2026-0115120000",
                title="AWS re:Invent 2025",
                activity_type="seminar",
                url="https://example.com/event",
                date="2026-01-15",
                created_by="test-user",
            )

            assert entity.entity_id == "ACT-12345678"
            mock_repo.create_entity.assert_called_once()

            # 호출 인자 확인
            call_args = mock_repo.create_entity.call_args
            assert call_args.kwargs["entity_type"] == EntityType.ACTIVITY
            assert call_args.kwargs["name"] == "AWS re:Invent 2025"
            assert call_args.kwargs["properties"]["activity_type"] == "seminar"
            assert call_args.kwargs["properties"]["url"] == "https://example.com/event"

    @pytest.mark.asyncio
    async def test_create_signal_entity_with_activity(self, service, mock_db):
        """Signal Entity 생성 (Activity 연결 포함) 테스트"""
        # 목 Entity와 Triple
        mock_signal = MagicMock(spec=Entity)
        mock_signal.entity_id = "SIG-12345678"
        mock_signal.name = "레거시 현대화 기회"

        mock_triple = MagicMock(spec=Triple)
        mock_triple.triple_id = "TRP-123456789012"

        with patch("backend.services.ontology_integration_service.ontology_repo") as mock_repo:
            mock_repo.create_entity = AsyncMock(return_value=mock_signal)
            mock_repo.create_triple = AsyncMock(return_value=mock_triple)

            signal, triples = await service.create_signal_entity(
                db=mock_db,
                title="레거시 현대화 기회",
                pain="레거시 시스템으로 인한 운영 비용 증가",
                activity_entity_id="ACT-12345678",
                target_org_id="ORG-87654321",
                created_by="test-user",
            )

            assert signal.entity_id == "SIG-12345678"
            assert len(triples) == 2  # GENERATES + TARGETS

    @pytest.mark.asyncio
    async def test_create_from_extraction_entities_only(
        self, service, mock_resolution_service, mock_db
    ):
        """추출 결과에서 엔티티만 생성 테스트"""
        # 추출 결과
        extraction = ExtractionResult(
            entities=[
                ExtractedEntity(name="삼성SDS", entity_type=EntityType.ORGANIZATION),
                ExtractedEntity(name="김철수", entity_type=EntityType.PERSON),
            ],
            relations=[],
        )

        # Resolution 결과 (모두 새로 생성)
        mock_resolution_service.resolve_entities.return_value = ResolutionResult(
            matches=[
                EntityMatch(
                    new_entity=extraction.entities[0],
                    existing_entity=None,
                    confidence=1.0,
                    rationale="새 엔티티",
                    action="create",
                ),
                EntityMatch(
                    new_entity=extraction.entities[1],
                    existing_entity=None,
                    confidence=1.0,
                    rationale="새 엔티티",
                    action="create",
                ),
            ],
            created_count=2,
        )

        # 목 Entity
        mock_org = MagicMock(spec=Entity)
        mock_org.entity_id = "ORG-12345678"
        mock_org.entity_type = MagicMock()
        mock_org.entity_type.value = "Organization"

        mock_person = MagicMock(spec=Entity)
        mock_person.entity_id = "PER-12345678"
        mock_person.entity_type = MagicMock()
        mock_person.entity_type.value = "Person"

        with patch("backend.services.ontology_integration_service.ontology_repo") as mock_repo:
            mock_repo.create_entity = AsyncMock(side_effect=[mock_org, mock_person])
            mock_repo.query_triples = AsyncMock(return_value=([], 0))

            result = await service.create_from_extraction(
                db=mock_db,
                extraction_result=extraction,
                source_ref="ACT-123",
                created_by="test",
            )

            assert result.entity_created_count == 2
            assert len(result.created_entities) == 2
            assert result.triple_created_count == 0

    @pytest.mark.asyncio
    async def test_create_from_extraction_with_relations(
        self, service, mock_resolution_service, mock_db
    ):
        """추출 결과에서 엔티티와 관계 생성 테스트"""
        # 추출 결과
        extraction = ExtractionResult(
            entities=[
                ExtractedEntity(name="삼성SDS", entity_type=EntityType.ORGANIZATION),
                ExtractedEntity(name="김철수", entity_type=EntityType.PERSON),
            ],
            relations=[
                ExtractedRelation(
                    subject="삼성SDS",
                    subject_type=EntityType.ORGANIZATION,
                    predicate=PredicateType.EMPLOYS,
                    object="김철수",
                    object_type=EntityType.PERSON,
                    confidence=0.9,
                ),
            ],
        )

        # Resolution 결과
        mock_resolution_service.resolve_entities.return_value = ResolutionResult(
            matches=[
                EntityMatch(
                    new_entity=extraction.entities[0],
                    existing_entity=None,
                    confidence=1.0,
                    rationale="새 엔티티",
                    action="create",
                ),
                EntityMatch(
                    new_entity=extraction.entities[1],
                    existing_entity=None,
                    confidence=1.0,
                    rationale="새 엔티티",
                    action="create",
                ),
            ],
            created_count=2,
        )

        # 목 Entity
        mock_org = MagicMock(spec=Entity)
        mock_org.entity_id = "ORG-12345678"
        mock_org.entity_type = MagicMock()
        mock_org.entity_type.value = "Organization"

        mock_person = MagicMock(spec=Entity)
        mock_person.entity_id = "PER-12345678"
        mock_person.entity_type = MagicMock()
        mock_person.entity_type.value = "Person"

        mock_triple = MagicMock(spec=Triple)
        mock_triple.triple_id = "TRP-123456789012"

        with patch("backend.services.ontology_integration_service.ontology_repo") as mock_repo:
            mock_repo.create_entity = AsyncMock(side_effect=[mock_org, mock_person])
            mock_repo.query_triples = AsyncMock(return_value=([], 0))
            mock_repo.create_triple = AsyncMock(return_value=mock_triple)

            result = await service.create_from_extraction(
                db=mock_db,
                extraction_result=extraction,
                source_ref="ACT-123",
                created_by="test",
            )

            assert result.entity_created_count == 2
            assert result.triple_created_count == 1
            assert len(result.created_triples) == 1

    @pytest.mark.asyncio
    async def test_create_from_extraction_skips_duplicate_triple(
        self, service, mock_resolution_service, mock_db
    ):
        """중복 Triple 스킵 테스트"""
        extraction = ExtractionResult(
            entities=[
                ExtractedEntity(name="A", entity_type=EntityType.ORGANIZATION),
                ExtractedEntity(name="B", entity_type=EntityType.ORGANIZATION),
            ],
            relations=[
                ExtractedRelation(
                    subject="A",
                    subject_type=EntityType.ORGANIZATION,
                    predicate=PredicateType.COMPETES_WITH,
                    object="B",
                    object_type=EntityType.ORGANIZATION,
                ),
            ],
        )

        mock_resolution_service.resolve_entities.return_value = ResolutionResult(
            matches=[
                EntityMatch(
                    new_entity=extraction.entities[0],
                    existing_entity=None,
                    confidence=1.0,
                    rationale="새 엔티티",
                    action="create",
                ),
                EntityMatch(
                    new_entity=extraction.entities[1],
                    existing_entity=None,
                    confidence=1.0,
                    rationale="새 엔티티",
                    action="create",
                ),
            ],
            created_count=2,
        )

        mock_org_a = MagicMock(spec=Entity)
        mock_org_a.entity_id = "ORG-A"
        mock_org_a.entity_type = MagicMock()
        mock_org_a.entity_type.value = "Organization"

        mock_org_b = MagicMock(spec=Entity)
        mock_org_b.entity_id = "ORG-B"
        mock_org_b.entity_type = MagicMock()
        mock_org_b.entity_type.value = "Organization"

        # 이미 존재하는 Triple 반환
        existing_triple = MagicMock(spec=Triple)

        with patch("backend.services.ontology_integration_service.ontology_repo") as mock_repo:
            mock_repo.create_entity = AsyncMock(side_effect=[mock_org_a, mock_org_b])
            mock_repo.query_triples = AsyncMock(return_value=([existing_triple], 1))

            result = await service.create_from_extraction(
                db=mock_db,
                extraction_result=extraction,
            )

            assert result.triple_created_count == 0
            assert result.triple_skipped_count == 1
            assert len(result.skipped_triples) == 1
            assert "Duplicate" in result.skipped_triples[0]["reason"]

    @pytest.mark.asyncio
    async def test_create_from_extraction_handles_merge(
        self, service, mock_resolution_service, mock_db
    ):
        """엔티티 병합 처리 테스트"""
        extraction = ExtractionResult(
            entities=[
                ExtractedEntity(name="삼성SDS", entity_type=EntityType.ORGANIZATION),
            ],
            relations=[],
        )

        # 기존 엔티티
        existing_entity = MagicMock(spec=Entity)
        existing_entity.entity_id = "ORG-EXISTING"

        mock_resolution_service.resolve_entities.return_value = ResolutionResult(
            matches=[
                EntityMatch(
                    new_entity=extraction.entities[0],
                    existing_entity=existing_entity,
                    confidence=0.95,
                    rationale="정확 일치",
                    action="merge",
                ),
            ],
            merged_count=1,
        )

        result = await service.create_from_extraction(
            db=mock_db,
            extraction_result=extraction,
        )

        assert result.entity_created_count == 0
        assert result.entity_merged_count == 1
        assert len(result.merged_entities) == 1


class TestTripleValidation:
    """Triple 검증 관련 테스트"""

    @pytest.fixture
    def service(self):
        """테스트용 서비스 인스턴스"""
        mock_resolution = MagicMock()
        mock_resolution.resolve_entities = AsyncMock(
            return_value=ResolutionResult(matches=[], created_count=0)
        )
        return OntologyIntegrationService(resolution_service=mock_resolution)

    @pytest.mark.asyncio
    async def test_invalid_triple_skipped(self, service):
        """검증 실패한 Triple은 스킵"""
        extraction = ExtractionResult(
            entities=[
                ExtractedEntity(name="Topic1", entity_type=EntityType.TOPIC),
                ExtractedEntity(name="Signal1", entity_type=EntityType.SIGNAL),
            ],
            relations=[
                # GENERATES는 Activity → Signal이어야 하지만
                # Topic → Signal로 잘못된 관계
                ExtractedRelation(
                    subject="Topic1",
                    subject_type=EntityType.TOPIC,
                    predicate=PredicateType.GENERATES,
                    object="Signal1",
                    object_type=EntityType.SIGNAL,
                ),
            ],
        )

        mock_db = AsyncMock()

        service.resolution_service.resolve_entities.return_value = ResolutionResult(
            matches=[
                EntityMatch(
                    new_entity=extraction.entities[0],
                    existing_entity=None,
                    confidence=1.0,
                    rationale="새 엔티티",
                    action="create",
                ),
                EntityMatch(
                    new_entity=extraction.entities[1],
                    existing_entity=None,
                    confidence=1.0,
                    rationale="새 엔티티",
                    action="create",
                ),
            ],
            created_count=2,
        )

        mock_topic = MagicMock(spec=Entity)
        mock_topic.entity_id = "TOP-123"
        mock_topic.entity_type = MagicMock()
        mock_topic.entity_type.value = "Topic"

        mock_signal = MagicMock(spec=Entity)
        mock_signal.entity_id = "SIG-123"
        mock_signal.entity_type = MagicMock()
        mock_signal.entity_type.value = "Signal"

        with patch("backend.services.ontology_integration_service.ontology_repo") as mock_repo:
            mock_repo.create_entity = AsyncMock(side_effect=[mock_topic, mock_signal])
            mock_repo.query_triples = AsyncMock(return_value=([], 0))

            result = await service.create_from_extraction(
                db=mock_db,
                extraction_result=extraction,
            )

            # GENERATES는 Activity → Signal만 허용하므로 스킵됨
            assert result.triple_skipped_count == 1
            # 에러 메시지에 'Topic'이 허용되지 않는다는 내용이 포함됨
            assert "Topic" in result.skipped_triples[0]["reason"]
            assert "Activity" in result.skipped_triples[0]["reason"]
