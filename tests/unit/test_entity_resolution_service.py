"""
Entity Resolution Service 단위 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.database.models.entity import Entity, EntityType
from backend.services.entity_resolution_service import (
    EntityMatch,
    EntityResolutionService,
    ResolutionResult,
    SameAsPair,
)
from backend.services.llm_extraction_service import ExtractedEntity


class TestEntityResolutionService:
    """EntityResolutionService 테스트"""

    @pytest.fixture
    def service(self):
        """테스트용 서비스 인스턴스"""
        with patch("backend.services.entity_resolution_service.AsyncAnthropic"):
            return EntityResolutionService()

    @pytest.fixture
    def mock_db(self):
        """목 데이터베이스 세션"""
        return AsyncMock()

    def test_calculate_similarity_exact_match(self, service):
        """정확한 이름 일치 테스트"""
        new_entity = ExtractedEntity(name="삼성SDS", entity_type=EntityType.ORGANIZATION)
        existing = MagicMock(spec=Entity)
        existing.name = "삼성SDS"

        score = service._calculate_similarity(new_entity, existing)
        assert score == 1.0

    def test_calculate_similarity_case_insensitive(self, service):
        """대소문자 무시 일치 테스트"""
        new_entity = ExtractedEntity(name="Samsung SDS", entity_type=EntityType.ORGANIZATION)
        existing = MagicMock(spec=Entity)
        existing.name = "samsung sds"

        score = service._calculate_similarity(new_entity, existing)
        assert score == 1.0

    def test_calculate_similarity_partial_match(self, service):
        """부분 일치 테스트"""
        new_entity = ExtractedEntity(name="삼성", entity_type=EntityType.ORGANIZATION)
        existing = MagicMock(spec=Entity)
        existing.name = "삼성SDS"

        score = service._calculate_similarity(new_entity, existing)
        assert score == 0.8  # 포함 관계

    def test_calculate_similarity_alias_match(self, service):
        """별칭 일치 테스트"""
        new_entity = ExtractedEntity(
            name="삼성에스디에스",
            entity_type=EntityType.ORGANIZATION,
            aliases=["삼성SDS", "Samsung SDS"],
        )
        existing = MagicMock(spec=Entity)
        existing.name = "삼성SDS"

        score = service._calculate_similarity(new_entity, existing)
        assert score == 0.9  # 별칭 정확 일치

    def test_calculate_similarity_word_overlap(self, service):
        """단어 겹침 테스트"""
        new_entity = ExtractedEntity(
            name="삼성 클라우드 사업부",
            entity_type=EntityType.TEAM,
        )
        existing = MagicMock(spec=Entity)
        existing.name = "삼성 인프라 사업부"

        score = service._calculate_similarity(new_entity, existing)
        # 겹치는 단어: "삼성", "사업부" → 2/4 = 0.5
        assert 0.4 <= score <= 0.6

    def test_calculate_similarity_no_match(self, service):
        """일치 없음 테스트"""
        new_entity = ExtractedEntity(name="LG CNS", entity_type=EntityType.ORGANIZATION)
        existing = MagicMock(spec=Entity)
        existing.name = "SK C&C"

        score = service._calculate_similarity(new_entity, existing)
        assert score < 0.5

    @pytest.mark.asyncio
    async def test_rule_based_match_finds_best(self, service):
        """규칙 기반 매칭이 최고 점수 후보를 반환하는지 테스트"""
        new_entity = ExtractedEntity(
            name="삼성SDS",
            entity_type=EntityType.ORGANIZATION,
        )

        candidate1 = MagicMock(spec=Entity)
        candidate1.name = "LG CNS"

        candidate2 = MagicMock(spec=Entity)
        candidate2.name = "삼성SDS"  # 정확히 일치

        candidate3 = MagicMock(spec=Entity)
        candidate3.name = "SK C&C"

        result = await service._rule_based_match(new_entity, [candidate1, candidate2, candidate3])

        assert result is not None
        assert result["entity"] == candidate2
        assert result["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_rule_based_match_returns_none_for_low_score(self, service):
        """낮은 점수면 None 반환 테스트"""
        new_entity = ExtractedEntity(
            name="완전히 다른 회사",
            entity_type=EntityType.ORGANIZATION,
        )

        candidate = MagicMock(spec=Entity)
        candidate.name = "아무 관련 없는 기업"

        result = await service._rule_based_match(new_entity, [candidate])

        # 유사도가 0.5 미만이면 None
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_entities_creates_new(self, service, mock_db):
        """후보 없을 때 새 엔티티 생성 액션 테스트"""
        with patch.object(service, "_find_candidates", return_value=[]):
            new_entities = [ExtractedEntity(name="새 회사", entity_type=EntityType.ORGANIZATION)]

            result = await service.resolve_entities(mock_db, new_entities)

            assert isinstance(result, ResolutionResult)
            assert result.created_count == 1
            assert result.merged_count == 0
            assert len(result.matches) == 1
            assert result.matches[0].action == "create"

    @pytest.mark.asyncio
    async def test_resolve_entities_merges_high_confidence(self, service, mock_db):
        """높은 신뢰도 매칭 시 병합 테스트"""
        existing_entity = MagicMock(spec=Entity)
        existing_entity.entity_id = "ORG-12345678"
        existing_entity.name = "삼성SDS"

        with patch.object(service, "_find_candidates", return_value=[existing_entity]):
            with patch.object(
                service,
                "_find_best_match",
                return_value={
                    "entity": existing_entity,
                    "confidence": 0.95,  # 높은 신뢰도
                    "rationale": "정확히 일치",
                },
            ):
                new_entities = [
                    ExtractedEntity(name="삼성SDS", entity_type=EntityType.ORGANIZATION)
                ]

                result = await service.resolve_entities(mock_db, new_entities)

                assert result.merged_count == 1
                assert result.created_count == 0
                assert result.matches[0].action == "merge"
                assert result.matches[0].existing_entity == existing_entity

    @pytest.mark.asyncio
    async def test_resolve_entities_same_as_for_medium_confidence(self, service, mock_db):
        """중간 신뢰도 매칭 시 SAME_AS 테스트"""
        existing_entity = MagicMock(spec=Entity)
        existing_entity.entity_id = "ORG-12345678"
        existing_entity.name = "삼성SDS"

        with patch.object(service, "_find_candidates", return_value=[existing_entity]):
            with patch.object(
                service,
                "_find_best_match",
                return_value={
                    "entity": existing_entity,
                    "confidence": 0.7,  # 중간 신뢰도
                    "rationale": "유사하지만 확실하지 않음",
                },
            ):
                new_entities = [
                    ExtractedEntity(
                        name="삼성에스디에스",
                        entity_type=EntityType.ORGANIZATION,
                    )
                ]

                result = await service.resolve_entities(mock_db, new_entities)

                assert result.same_as_count == 1
                assert result.matches[0].action == "same_as"
                assert len(result.uncertain_pairs) == 1


class TestResolutionResult:
    """ResolutionResult 데이터 클래스 테스트"""

    def test_default_values(self):
        """기본값 테스트"""
        result = ResolutionResult()

        assert result.matches == []
        assert result.uncertain_pairs == []
        assert result.merged_count == 0
        assert result.created_count == 0
        assert result.same_as_count == 0

    def test_with_matches(self):
        """매칭 결과 포함 테스트"""
        entity = ExtractedEntity(name="테스트", entity_type=EntityType.TOPIC)
        match = EntityMatch(
            new_entity=entity,
            existing_entity=None,
            confidence=1.0,
            rationale="새 엔티티",
            action="create",
        )

        result = ResolutionResult(matches=[match], created_count=1)

        assert len(result.matches) == 1
        assert result.created_count == 1


class TestEntityMatch:
    """EntityMatch 데이터 클래스 테스트"""

    def test_create_action(self):
        """생성 액션 테스트"""
        entity = ExtractedEntity(name="테스트", entity_type=EntityType.TOPIC)
        match = EntityMatch(
            new_entity=entity,
            existing_entity=None,
            confidence=1.0,
            rationale="후보 없음",
            action="create",
        )

        assert match.action == "create"
        assert match.existing_entity is None

    def test_merge_action(self):
        """병합 액션 테스트"""
        new_entity = ExtractedEntity(name="삼성SDS", entity_type=EntityType.ORGANIZATION)
        existing = MagicMock(spec=Entity)
        existing.entity_id = "ORG-12345678"

        match = EntityMatch(
            new_entity=new_entity,
            existing_entity=existing,
            confidence=0.95,
            rationale="정확 일치",
            action="merge",
        )

        assert match.action == "merge"
        assert match.existing_entity is not None
        assert match.confidence >= 0.85


class TestSameAsPair:
    """SameAsPair 데이터 클래스 테스트"""

    def test_with_extracted_entities(self):
        """추출된 엔티티로 쌍 생성 테스트"""
        entity_a = ExtractedEntity(name="삼성SDS", entity_type=EntityType.ORGANIZATION)
        entity_b = ExtractedEntity(name="삼성에스디에스", entity_type=EntityType.ORGANIZATION)

        pair = SameAsPair(
            entity_a=entity_a,
            entity_b=entity_b,
            confidence=0.7,
            reason="이름 유사",
        )

        assert pair.confidence == 0.7
        assert "유사" in pair.reason

    def test_with_db_entity(self):
        """DB 엔티티 포함 쌍 테스트"""
        extracted = ExtractedEntity(name="삼성SDS", entity_type=EntityType.ORGANIZATION)
        db_entity = MagicMock(spec=Entity)
        db_entity.entity_id = "ORG-12345678"

        pair = SameAsPair(
            entity_a=extracted,
            entity_b=db_entity,
            confidence=0.6,
            reason="불확실한 매칭",
        )

        assert isinstance(pair.entity_a, ExtractedEntity)
        assert pair.entity_b == db_entity
