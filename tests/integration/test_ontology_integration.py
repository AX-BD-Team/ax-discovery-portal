"""
온톨로지 통합 테스트

LLM 추출 → Entity Resolution → 온톨로지 생성 전체 흐름 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.database.models.entity import Entity, EntityType
from backend.database.models.triple import PredicateType, Triple
from backend.services.entity_resolution_service import (
    EntityMatch,
    EntityResolutionService,
    ResolutionResult,
)
from backend.services.llm_extraction_service import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
    LLMExtractionService,
)
from backend.services.ontology_integration_service import OntologyIntegrationService


class TestOntologyIntegrationFlow:
    """온톨로지 통합 흐름 테스트"""

    @pytest.fixture
    def mock_db(self):
        """목 데이터베이스 세션"""
        return AsyncMock()

    @pytest.fixture
    def sample_aar_content(self):
        """샘플 AAR 문서"""
        return """
## After Action Review: AWS re:Invent 2025

**일시**: 2026-01-15
**주최**: AWS
**참석자**: 김영희 과장 (BD팀)

---

### 1. 핵심 인사이트

1. 삼성SDS 클라우드 사업부 이철수 부장과 미팅
2. 삼성SDS는 현재 레거시 시스템 현대화 프로젝트를 검토 중
3. 예상 규모 50억원, 2026년 상반기 착수 희망

### 2. AX BD 관련성
- 관련 Play: EXT_Desk_D01_Seminar
- 잠재 기회: 삼성SDS 레거시 현대화 프로젝트 수주

### 3. Signal 후보
| 제목 | Pain/Need | 근거 |
|------|----------|------|
| 삼성SDS 레거시 현대화 | 레거시 시스템 운영 비용 | 이철수 부장 언급 |

### 4. 종합 평가
- 참석 가치: ⭐⭐⭐⭐☆
- 경쟁사로 LG CNS, SK C&C가 언급됨
"""

    @pytest.mark.asyncio
    async def test_full_extraction_flow(self, mock_db, sample_aar_content):
        """전체 추출 흐름 테스트 (목 사용)"""
        # LLM 추출 서비스 목
        llm_service = LLMExtractionService()

        # LLM 응답 목
        entity_response = MagicMock()
        entity_response.content = [
            MagicMock(
                text="""```json
{
    "entities": [
        {"name": "삼성SDS", "type": "Organization", "aliases": ["Samsung SDS"], "confidence": 0.95},
        {"name": "이철수", "type": "Person", "confidence": 0.9, "properties": {"title": "부장"}},
        {"name": "레거시 시스템 현대화", "type": "Topic", "confidence": 0.9},
        {"name": "삼성SDS 레거시 현대화 기회", "type": "Signal", "confidence": 0.85},
        {"name": "LG CNS", "type": "Organization", "confidence": 0.9},
        {"name": "SK C&C", "type": "Organization", "confidence": 0.9}
    ],
    "extraction_notes": "세미나 참석 보고서에서 추출"
}
```"""
            )
        ]

        relation_response = MagicMock()
        relation_response.content = [
            MagicMock(
                text="""```json
{
    "relations": [
        {"subject": "삼성SDS", "subject_type": "Organization", "predicate": "EMPLOYS", "object": "이철수", "object_type": "Person", "confidence": 0.95},
        {"subject": "삼성SDS 레거시 현대화 기회", "subject_type": "Signal", "predicate": "TARGETS", "object": "삼성SDS", "object_type": "Organization", "confidence": 0.9},
        {"subject": "삼성SDS 레거시 현대화 기회", "subject_type": "Signal", "predicate": "HAS_PAIN", "object": "레거시 시스템 현대화", "object_type": "Topic", "confidence": 0.9},
        {"subject": "삼성SDS", "subject_type": "Organization", "predicate": "COMPETES_WITH", "object": "LG CNS", "object_type": "Organization", "confidence": 0.85}
    ]
}
```"""
            )
        ]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=[entity_response, relation_response])
        llm_service.client = mock_client

        # 추출 실행
        result = await llm_service.extract_all(sample_aar_content)

        # 검증
        assert len(result.entities) == 6
        assert len(result.relations) == 4

        # 엔티티 타입 확인
        org_entities = [e for e in result.entities if e.entity_type == EntityType.ORGANIZATION]
        assert len(org_entities) == 3  # 삼성SDS, LG CNS, SK C&C

        person_entities = [e for e in result.entities if e.entity_type == EntityType.PERSON]
        assert len(person_entities) == 1

        signal_entities = [e for e in result.entities if e.entity_type == EntityType.SIGNAL]
        assert len(signal_entities) == 1

    @pytest.mark.asyncio
    async def test_entity_resolution_with_existing_entities(self, mock_db):
        """기존 엔티티와의 해결 테스트"""
        # Entity Resolution 서비스
        with patch("backend.services.entity_resolution_service.AsyncAnthropic"):
            resolution_service = EntityResolutionService()

        # 기존 엔티티 설정
        existing_samsung = MagicMock(spec=Entity)
        existing_samsung.entity_id = "ORG-SAMSUNG"
        existing_samsung.name = "삼성SDS"
        existing_samsung.entity_type = EntityType.ORGANIZATION

        # 후보 검색 목
        with patch.object(
            resolution_service,
            "_find_candidates",
            return_value=[existing_samsung],
        ):
            with patch.object(
                resolution_service,
                "_find_best_match",
                return_value={
                    "entity": existing_samsung,
                    "confidence": 0.98,
                    "rationale": "정확히 일치하는 기존 엔티티",
                },
            ):
                new_entities = [
                    ExtractedEntity(
                        name="삼성SDS",
                        entity_type=EntityType.ORGANIZATION,
                        aliases=["Samsung SDS"],
                    )
                ]

                result = await resolution_service.resolve_entities(mock_db, new_entities)

                assert result.merged_count == 1
                assert result.created_count == 0
                assert result.matches[0].action == "merge"
                assert result.matches[0].existing_entity.entity_id == "ORG-SAMSUNG"

    @pytest.mark.asyncio
    async def test_ontology_creation_end_to_end(self, mock_db):
        """온톨로지 생성 E2E 테스트"""
        # 추출 결과 (실제 LLM 없이 수동 생성)
        extraction_result = ExtractionResult(
            entities=[
                ExtractedEntity(
                    name="삼성SDS",
                    entity_type=EntityType.ORGANIZATION,
                    confidence=0.95,
                ),
                ExtractedEntity(
                    name="이철수",
                    entity_type=EntityType.PERSON,
                    confidence=0.9,
                    properties={"title": "부장", "department": "클라우드 사업부"},
                ),
                ExtractedEntity(
                    name="레거시 현대화 기회",
                    entity_type=EntityType.SIGNAL,
                    confidence=0.85,
                    properties={"pain": "레거시 시스템 운영 비용 증가"},
                ),
            ],
            relations=[
                ExtractedRelation(
                    subject="삼성SDS",
                    subject_type=EntityType.ORGANIZATION,
                    predicate=PredicateType.EMPLOYS,
                    object="이철수",
                    object_type=EntityType.PERSON,
                    confidence=0.9,
                ),
                ExtractedRelation(
                    subject="레거시 현대화 기회",
                    subject_type=EntityType.SIGNAL,
                    predicate=PredicateType.TARGETS,
                    object="삼성SDS",
                    object_type=EntityType.ORGANIZATION,
                    confidence=0.85,
                ),
            ],
        )

        # Resolution 서비스 목 (모두 새로 생성)
        mock_resolution = MagicMock()
        mock_resolution.resolve_entities = AsyncMock(
            return_value=ResolutionResult(
                matches=[
                    EntityMatch(
                        new_entity=extraction_result.entities[0],
                        existing_entity=None,
                        confidence=1.0,
                        rationale="새 엔티티",
                        action="create",
                    ),
                    EntityMatch(
                        new_entity=extraction_result.entities[1],
                        existing_entity=None,
                        confidence=1.0,
                        rationale="새 엔티티",
                        action="create",
                    ),
                    EntityMatch(
                        new_entity=extraction_result.entities[2],
                        existing_entity=None,
                        confidence=1.0,
                        rationale="새 엔티티",
                        action="create",
                    ),
                ],
                created_count=3,
            )
        )

        # 온톨로지 통합 서비스
        integration_service = OntologyIntegrationService(resolution_service=mock_resolution)

        # 목 Entity
        mock_org = MagicMock(spec=Entity)
        mock_org.entity_id = "ORG-12345678"
        mock_org.entity_type = MagicMock()
        mock_org.entity_type.value = "Organization"

        mock_person = MagicMock(spec=Entity)
        mock_person.entity_id = "PER-12345678"
        mock_person.entity_type = MagicMock()
        mock_person.entity_type.value = "Person"

        mock_signal = MagicMock(spec=Entity)
        mock_signal.entity_id = "SIG-12345678"
        mock_signal.entity_type = MagicMock()
        mock_signal.entity_type.value = "Signal"

        mock_triple = MagicMock(spec=Triple)
        mock_triple.triple_id = "TRP-123456789012"

        with patch("backend.services.ontology_integration_service.ontology_repo") as mock_repo:
            mock_repo.create_entity = AsyncMock(side_effect=[mock_org, mock_person, mock_signal])
            mock_repo.query_triples = AsyncMock(return_value=([], 0))
            mock_repo.create_triple = AsyncMock(return_value=mock_triple)

            result = await integration_service.create_from_extraction(
                db=mock_db,
                extraction_result=extraction_result,
                source_ref="ACT-TEST-001",
                created_by="test-integration",
            )

            # 검증
            assert result.entity_created_count == 3
            assert result.triple_created_count == 2
            assert len(result.errors) == 0

            # Entity 생성 호출 확인
            assert mock_repo.create_entity.call_count == 3

            # Triple 생성 호출 확인
            assert mock_repo.create_triple.call_count == 2


class TestSeminarPipelineWithOntologyIntegration:
    """세미나 파이프라인 + 온톨로지 통합 테스트"""

    @pytest.fixture
    def mock_event_emitter(self):
        """목 이벤트 발행기"""
        emitter = MagicMock()
        emitter.emit_run_started = AsyncMock()
        emitter.emit_step_started = AsyncMock()
        emitter.emit_step_finished = AsyncMock()
        emitter.emit_surface = AsyncMock()
        emitter.emit_run_finished = AsyncMock()
        emitter.emit_run_error = AsyncMock()
        return emitter

    @pytest.fixture
    def mock_db(self):
        """목 데이터베이스 세션"""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_pipeline_without_aar_content(self, mock_event_emitter, mock_db):
        """AAR 내용 없이 파이프라인 실행"""
        from backend.agent_runtime.workflows.wf_seminar_pipeline import (
            SeminarOntologyInput,
            SeminarPipelineWithOntology,
        )

        pipeline = SeminarPipelineWithOntology(
            emitter=mock_event_emitter,
            db_session=mock_db,
        )

        # URL 메타데이터 추출 목
        with patch.object(
            pipeline,
            "_extract_metadata",
            return_value={
                "url": "https://example.com",
                "title": "테스트 세미나",
                "date": "2026-01-15",
                "organizer": "AWS",
            },
        ):
            # Confluence 업데이트 목
            with patch.object(pipeline, "_update_confluence", return_value=True):
                # Activity Entity 생성 목
                mock_entity = MagicMock()
                mock_entity.entity_id = "ACT-12345678"

                with patch(
                    "backend.services.ontology_integration_service.ontology_repo"
                ) as mock_repo:
                    mock_repo.create_entity = AsyncMock(return_value=mock_entity)

                    input_data = SeminarOntologyInput(
                        url="https://example.com/event",
                        aar_content=None,  # AAR 없음
                    )

                    result = await pipeline.run_with_ontology(input_data)

                    # 기본 결과 확인
                    assert result.activity.activity_id is not None
                    assert result.aar_template is not None
                    assert result.ontology.activity_entity_id == "ACT-12345678"

                    # 엔티티 추출 단계가 스킵되었는지 확인
                    # (AAR 없으므로 스킵됨)
                    assert result.ontology.entity_count == 1  # Activity만

    @pytest.mark.asyncio
    async def test_pipeline_with_aar_content(self, mock_event_emitter, mock_db):
        """AAR 내용으로 파이프라인 실행"""
        from backend.agent_runtime.workflows.wf_seminar_pipeline import (
            SeminarOntologyInput,
            SeminarPipelineWithOntology,
        )

        pipeline = SeminarPipelineWithOntology(
            emitter=mock_event_emitter,
            db_session=mock_db,
        )

        # 목 설정
        with patch.object(
            pipeline,
            "_extract_metadata",
            return_value={
                "url": "https://example.com",
                "title": "테스트 세미나",
                "date": "2026-01-15",
            },
        ):
            with patch.object(pipeline, "_update_confluence", return_value=True):
                # LLM 추출 목
                mock_entities = [
                    ExtractedEntity(
                        name="테스트 회사",
                        entity_type=EntityType.ORGANIZATION,
                    )
                ]

                mock_relations = [
                    ExtractedRelation(
                        subject="테스트 Activity",
                        subject_type=EntityType.ACTIVITY,
                        predicate=PredicateType.GENERATES,
                        object="테스트 Signal",
                        object_type=EntityType.SIGNAL,
                    )
                ]

                with patch(
                    "backend.services.llm_extraction_service.llm_extraction_service"
                ) as mock_llm:
                    mock_llm.extract_entities = AsyncMock(return_value=mock_entities)
                    mock_llm.extract_relations = AsyncMock(return_value=mock_relations)

                    # 온톨로지 통합 목
                    mock_creation_result = MagicMock()
                    mock_creation_result.entity_created_count = 2
                    mock_creation_result.entity_merged_count = 0
                    mock_creation_result.triple_created_count = 1
                    mock_creation_result.created_entities = []

                    with patch(
                        "backend.services.ontology_integration_service.ontology_integration_service"
                    ) as mock_integration:
                        mock_integration.create_activity_entity = AsyncMock(
                            return_value=MagicMock(entity_id="ACT-12345678")
                        )
                        mock_integration.create_from_extraction = AsyncMock(
                            return_value=mock_creation_result
                        )

                        input_data = SeminarOntologyInput(
                            url="https://example.com/event",
                            aar_content="테스트 AAR 내용",
                        )

                        result = await pipeline.run_with_ontology(input_data)

                        # 결과 확인
                        assert result.activity is not None
                        assert result.ontology.entity_count >= 1

                        # LLM 추출 호출 확인
                        mock_llm.extract_entities.assert_called_once()
                        mock_llm.extract_relations.assert_called_once()

                        # 온톨로지 통합 호출 확인
                        mock_integration.create_from_extraction.assert_called_once()
