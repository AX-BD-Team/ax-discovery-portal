"""
LLM Extraction Service 단위 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.database.models.entity import EntityType
from backend.database.models.triple import PredicateType
from backend.services.llm_extraction_service import (
    EvidenceSpan,
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
    LLMExtractionService,
    PromptLoader,
    parse_entity_type,
    parse_predicate_type,
)


class TestPromptLoader:
    """PromptLoader 테스트"""

    def test_load_entity_extraction_prompt(self):
        """엔티티 추출 프롬프트 로드 테스트"""
        loader = PromptLoader()

        try:
            prompts = loader.load("entity-extraction")
            assert "system" in prompts
            assert "user_template" in prompts
            assert len(prompts["system"]) > 0
            assert "{document}" in prompts["user_template"]
        except FileNotFoundError:
            pytest.skip("프롬프트 파일이 없습니다")

    def test_load_relation_extraction_prompt(self):
        """관계 추출 프롬프트 로드 테스트"""
        loader = PromptLoader()

        try:
            prompts = loader.load("relation-extraction")
            assert "system" in prompts
            assert "user_template" in prompts
            assert "{entities}" in prompts["user_template"]
            assert "{document}" in prompts["user_template"]
        except FileNotFoundError:
            pytest.skip("프롬프트 파일이 없습니다")

    def test_load_nonexistent_prompt(self):
        """존재하지 않는 프롬프트 로드 시 예외 발생 테스트"""
        loader = PromptLoader()

        with pytest.raises(FileNotFoundError):
            loader.load("nonexistent-prompt")

    def test_prompt_caching(self):
        """프롬프트 캐싱 테스트"""
        loader = PromptLoader()

        try:
            prompts1 = loader.load("entity-extraction")
            prompts2 = loader.load("entity-extraction")
            assert prompts1 is prompts2  # 같은 객체 (캐시됨)
        except FileNotFoundError:
            pytest.skip("프롬프트 파일이 없습니다")


class TestParseEntityType:
    """EntityType 파싱 테스트"""

    def test_parse_valid_entity_types(self):
        """유효한 EntityType 파싱"""
        assert parse_entity_type("Activity") == EntityType.ACTIVITY
        assert parse_entity_type("Signal") == EntityType.SIGNAL
        assert parse_entity_type("Organization") == EntityType.ORGANIZATION
        assert parse_entity_type("Person") == EntityType.PERSON
        assert parse_entity_type("Technology") == EntityType.TECHNOLOGY
        assert parse_entity_type("Topic") == EntityType.TOPIC

    def test_parse_unknown_entity_type(self):
        """알 수 없는 타입은 TOPIC으로 기본값"""
        assert parse_entity_type("Unknown") == EntityType.TOPIC
        assert parse_entity_type("") == EntityType.TOPIC


class TestParsePredicateType:
    """PredicateType 파싱 테스트"""

    def test_parse_valid_predicate_types(self):
        """유효한 PredicateType 파싱"""
        assert parse_predicate_type("GENERATES") == PredicateType.GENERATES
        assert parse_predicate_type("TARGETS") == PredicateType.TARGETS
        assert parse_predicate_type("HAS_PAIN") == PredicateType.HAS_PAIN
        assert parse_predicate_type("EMPLOYS") == PredicateType.EMPLOYS

    def test_parse_unknown_predicate_type(self):
        """알 수 없는 타입은 RELATED_TO로 기본값"""
        assert parse_predicate_type("Unknown") == PredicateType.RELATED_TO
        assert parse_predicate_type("") == PredicateType.RELATED_TO


class TestLLMExtractionService:
    """LLMExtractionService 테스트"""

    @pytest.fixture
    def mock_anthropic(self):
        """Anthropic 클라이언트 목"""
        with patch("backend.services.llm_extraction_service.AsyncAnthropic") as mock:
            yield mock

    @pytest.fixture
    def service(self, mock_anthropic):
        """테스트용 서비스 인스턴스"""
        return LLMExtractionService()

    @pytest.mark.asyncio
    async def test_extract_entities_success(self, service, mock_anthropic):
        """엔티티 추출 성공 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""```json
{
    "entities": [
        {
            "name": "삼성SDS",
            "type": "Organization",
            "aliases": ["Samsung SDS"],
            "description": "IT 서비스 기업",
            "confidence": 0.95,
            "evidence_span": {"start": 0, "end": 10, "text": "삼성SDS"},
            "properties": {"industry": "IT서비스"}
        }
    ],
    "extraction_notes": "테스트"
}
```"""
            )
        ]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        service.client = mock_client

        # 테스트 실행
        entities = await service.extract_entities("삼성SDS 관련 문서입니다.")

        assert len(entities) == 1
        assert entities[0].name == "삼성SDS"
        assert entities[0].entity_type == EntityType.ORGANIZATION
        assert "Samsung SDS" in entities[0].aliases
        assert entities[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_extract_relations_success(self, service, mock_anthropic):
        """관계 추출 성공 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""```json
{
    "relations": [
        {
            "subject": "삼성SDS",
            "subject_type": "Organization",
            "predicate": "EMPLOYS",
            "object": "김철수",
            "object_type": "Person",
            "confidence": 0.9,
            "properties": {"title": "부장"}
        }
    ],
    "extraction_notes": "테스트"
}
```"""
            )
        ]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        service.client = mock_client

        # 테스트용 엔티티
        entities = [
            ExtractedEntity(name="삼성SDS", entity_type=EntityType.ORGANIZATION),
            ExtractedEntity(name="김철수", entity_type=EntityType.PERSON),
        ]

        # 테스트 실행
        relations = await service.extract_relations("문서 내용", entities)

        assert len(relations) == 1
        assert relations[0].subject == "삼성SDS"
        assert relations[0].predicate == PredicateType.EMPLOYS
        assert relations[0].object == "김철수"

    @pytest.mark.asyncio
    async def test_extract_all_success(self, service, mock_anthropic):
        """전체 추출 성공 테스트"""
        # Entity 추출 응답
        entity_response = MagicMock()
        entity_response.content = [
            MagicMock(
                text="""```json
{
    "entities": [{"name": "테스트", "type": "Topic", "confidence": 0.8}],
    "extraction_notes": ""
}
```"""
            )
        ]

        # Relation 추출 응답
        relation_response = MagicMock()
        relation_response.content = [
            MagicMock(
                text="""```json
{
    "relations": [],
    "extraction_notes": ""
}
```"""
            )
        ]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=[entity_response, relation_response])
        service.client = mock_client

        # 테스트 실행
        result = await service.extract_all("테스트 문서")

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 1
        assert len(result.relations) == 0

    def test_parse_json_response_with_code_block(self, service):
        """코드 블록 내 JSON 파싱 테스트"""
        content = """
Here is the extraction result:

```json
{
    "entities": [{"name": "test"}]
}
```

Done.
"""
        result = service._parse_json_response(content)
        assert result["entities"] == [{"name": "test"}]

    def test_parse_json_response_without_code_block(self, service):
        """코드 블록 없는 JSON 파싱 테스트"""
        content = '{"entities": [{"name": "test"}]}'
        result = service._parse_json_response(content)
        assert result["entities"] == [{"name": "test"}]

    def test_parse_json_response_invalid(self, service):
        """잘못된 JSON 파싱 시 기본값 반환"""
        content = "This is not JSON"
        result = service._parse_json_response(content)
        assert result == {"entities": [], "relations": []}

    def test_parse_entity_with_evidence_span(self, service):
        """EvidenceSpan 포함 엔티티 파싱"""
        data = {
            "name": "테스트",
            "type": "Topic",
            "confidence": 0.85,
            "evidence_span": {"start": 10, "end": 20, "text": "테스트 텍스트"},
        }

        entity = service._parse_entity(data)

        assert entity is not None
        assert entity.name == "테스트"
        assert entity.evidence_span is not None
        assert entity.evidence_span.start == 10
        assert entity.evidence_span.end == 20
        assert entity.evidence_span.text == "테스트 텍스트"

    def test_parse_entity_missing_required_field(self, service):
        """필수 필드 누락 시 None 반환"""
        data = {"type": "Topic"}  # name 누락

        entity = service._parse_entity(data)
        assert entity is None

    def test_parse_relation_success(self, service):
        """관계 파싱 성공 테스트"""
        data = {
            "subject": "A",
            "subject_type": "Organization",
            "predicate": "TARGETS",
            "object": "B",
            "object_type": "Organization",
            "confidence": 0.9,
        }

        relation = service._parse_relation(data)

        assert relation is not None
        assert relation.subject == "A"
        assert relation.predicate == PredicateType.TARGETS
        assert relation.object == "B"


class TestExtractedEntity:
    """ExtractedEntity 데이터 클래스 테스트"""

    def test_default_values(self):
        """기본값 테스트"""
        entity = ExtractedEntity(name="테스트", entity_type=EntityType.TOPIC)

        assert entity.name == "테스트"
        assert entity.entity_type == EntityType.TOPIC
        assert entity.aliases == []
        assert entity.description is None
        assert entity.confidence == 0.85
        assert entity.evidence_span is None
        assert entity.properties == {}

    def test_with_all_fields(self):
        """모든 필드 설정 테스트"""
        span = EvidenceSpan(start=0, end=10, text="test")
        entity = ExtractedEntity(
            name="테스트",
            entity_type=EntityType.ORGANIZATION,
            aliases=["테스트2"],
            description="설명",
            confidence=0.95,
            evidence_span=span,
            properties={"key": "value"},
        )

        assert entity.aliases == ["테스트2"]
        assert entity.description == "설명"
        assert entity.confidence == 0.95
        assert entity.evidence_span.text == "test"
        assert entity.properties["key"] == "value"


class TestExtractionResult:
    """ExtractionResult 데이터 클래스 테스트"""

    def test_default_values(self):
        """기본값 테스트"""
        result = ExtractionResult()

        assert result.entities == []
        assert result.relations == []
        assert result.extraction_notes is None

    def test_with_entities_and_relations(self):
        """엔티티와 관계 포함 테스트"""
        entity = ExtractedEntity(name="테스트", entity_type=EntityType.TOPIC)
        relation = ExtractedRelation(
            subject="A",
            subject_type=EntityType.ORGANIZATION,
            predicate=PredicateType.TARGETS,
            object="B",
            object_type=EntityType.ORGANIZATION,
        )

        result = ExtractionResult(
            entities=[entity],
            relations=[relation],
            extraction_notes="테스트 노트",
        )

        assert len(result.entities) == 1
        assert len(result.relations) == 1
        assert result.extraction_notes == "테스트 노트"
