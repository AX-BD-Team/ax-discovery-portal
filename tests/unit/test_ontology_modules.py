"""
Ontology 모듈 단위 테스트

테스트 대상:
- backend/agent_runtime/ontology/graph_query.py
- backend/agent_runtime/ontology/validator.py
- backend/database/repositories/ontology.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agent_runtime.ontology.graph_query import (
    GraphQuery,
    PathMode,
    PathOptions,
    PathResult,
    PathStep,
    find_evidence_chain,
)
from backend.agent_runtime.ontology.validator import (
    PREDICATE_CONSTRAINTS,
    TripleValidator,
    ValidationErrorCode,
    ValidationResult,
)
from backend.database.models.entity import Entity, EntityType
from backend.database.models.triple import (
    AssertionType,
    PredicateType,
    Triple,
    TripleStatus,
)
from backend.database.repositories.ontology import OntologyRepository

# =============================================================================
# TripleValidator 테스트
# =============================================================================


class TestTripleValidator:
    """TripleValidator 단위 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.validator = TripleValidator()

    # ----- 기본 검증 테스트 -----

    def test_validate_has_scorecard_valid(self):
        """HAS_SCORECARD: Signal -> Scorecard (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.HAS_SCORECARD,
            object_type=EntityType.SCORECARD,
            confidence=0.9,
        )
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_has_scorecard_invalid_subject(self):
        """HAS_SCORECARD: Topic -> Scorecard (잘못된 subject)"""
        result = self.validator.validate(
            subject_type=EntityType.TOPIC,
            predicate=PredicateType.HAS_SCORECARD,
            object_type=EntityType.SCORECARD,
        )
        assert result.is_valid is False
        assert any(e.code == ValidationErrorCode.INVALID_SUBJECT_TYPE for e in result.errors)

    def test_validate_has_scorecard_invalid_object(self):
        """HAS_SCORECARD: Signal -> Topic (잘못된 object)"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.HAS_SCORECARD,
            object_type=EntityType.TOPIC,
        )
        assert result.is_valid is False
        assert any(e.code == ValidationErrorCode.INVALID_OBJECT_TYPE for e in result.errors)

    def test_validate_has_brief_valid(self):
        """HAS_BRIEF: Signal -> Brief (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.HAS_BRIEF,
            object_type=EntityType.BRIEF,
        )
        assert result.is_valid is True

    def test_validate_belongs_to_play_signal(self):
        """BELONGS_TO_PLAY: Signal -> Play (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.BELONGS_TO_PLAY,
            object_type=EntityType.PLAY,
        )
        assert result.is_valid is True

    def test_validate_belongs_to_play_brief(self):
        """BELONGS_TO_PLAY: Brief -> Play (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.BRIEF,
            predicate=PredicateType.BELONGS_TO_PLAY,
            object_type=EntityType.PLAY,
        )
        assert result.is_valid is True

    def test_validate_has_pain_valid(self):
        """HAS_PAIN: Signal -> Topic (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.HAS_PAIN,
            object_type=EntityType.TOPIC,
        )
        assert result.is_valid is True

    # ----- 토픽 관계 테스트 -----

    def test_validate_similar_to_topics(self):
        """SIMILAR_TO: Topic -> Topic (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.TOPIC,
            predicate=PredicateType.SIMILAR_TO,
            object_type=EntityType.TOPIC,
        )
        assert result.is_valid is True

    def test_validate_similar_to_signals(self):
        """SIMILAR_TO: Signal -> Signal (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.SIMILAR_TO,
            object_type=EntityType.SIGNAL,
        )
        assert result.is_valid is True

    def test_validate_parent_of_valid(self):
        """PARENT_OF: Topic -> Topic (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.TOPIC,
            predicate=PredicateType.PARENT_OF,
            object_type=EntityType.TOPIC,
        )
        assert result.is_valid is True

    def test_validate_parent_of_invalid(self):
        """PARENT_OF: Signal -> Topic (잘못됨)"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.PARENT_OF,
            object_type=EntityType.TOPIC,
        )
        assert result.is_valid is False
        assert any(e.code == ValidationErrorCode.INVALID_SUBJECT_TYPE for e in result.errors)

    def test_validate_related_to_valid(self):
        """RELATED_TO: Technology -> Technology (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.TECHNOLOGY,
            predicate=PredicateType.RELATED_TO,
            object_type=EntityType.TECHNOLOGY,
        )
        assert result.is_valid is True

    # ----- 맥락 관계 테스트 -----

    def test_validate_targets_organization(self):
        """TARGETS: Signal -> Organization (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.TARGETS,
            object_type=EntityType.ORGANIZATION,
        )
        assert result.is_valid is True

    def test_validate_uses_technology_valid(self):
        """USES_TECHNOLOGY: Signal -> Technology (유효, deprecated)"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.USES_TECHNOLOGY,
            object_type=EntityType.TECHNOLOGY,
        )
        # v2: USES_TECHNOLOGY는 deprecated (ADDRESSES 사용 권장)
        assert result.is_valid is True
        assert any(e.code == ValidationErrorCode.DEPRECATED_PREDICATE for e in result.warnings)

    def test_validate_in_industry_valid(self):
        """IN_INDUSTRY: Organization -> Industry (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.ORGANIZATION,
            predicate=PredicateType.IN_INDUSTRY,
            object_type=EntityType.INDUSTRY,
        )
        assert result.is_valid is True

    # ----- HAS_ROLE 테스트 -----

    def test_validate_has_role_with_valid_properties(self):
        """HAS_ROLE: Organization -> Play (역할 속성 포함)"""
        result = self.validator.validate(
            subject_type=EntityType.ORGANIZATION,
            predicate=PredicateType.HAS_ROLE,
            object_type=EntityType.PLAY,
            properties={"role": "customer"},
        )
        assert result.is_valid is True

    def test_validate_has_role_missing_properties(self):
        """HAS_ROLE: 역할 속성 누락"""
        result = self.validator.validate(
            subject_type=EntityType.ORGANIZATION,
            predicate=PredicateType.HAS_ROLE,
            object_type=EntityType.PLAY,
            properties=None,
        )
        assert result.is_valid is False
        assert any(e.code == ValidationErrorCode.MISSING_REQUIRED_EVIDENCE for e in result.errors)

    def test_validate_has_role_invalid_role(self):
        """HAS_ROLE: 알 수 없는 역할 값"""
        result = self.validator.validate(
            subject_type=EntityType.ORGANIZATION,
            predicate=PredicateType.HAS_ROLE,
            object_type=EntityType.PLAY,
            properties={"role": "unknown"},
        )
        assert result.is_valid is True  # 경고만 발생
        assert any(e.code == ValidationErrorCode.INVALID_OBJECT_TYPE for e in result.warnings)

    def test_validate_has_role_competitor(self):
        """HAS_ROLE: competitor 역할"""
        result = self.validator.validate(
            subject_type=EntityType.ORGANIZATION,
            predicate=PredicateType.HAS_ROLE,
            object_type=EntityType.SIGNAL,
            properties={"role": "competitor"},
        )
        assert result.is_valid is True

    def test_validate_has_role_partner(self):
        """HAS_ROLE: partner 역할"""
        result = self.validator.validate(
            subject_type=EntityType.ORGANIZATION,
            predicate=PredicateType.HAS_ROLE,
            object_type=EntityType.PLAY,
            properties={"role": "partner"},
        )
        assert result.is_valid is True

    # ----- 증거 관계 테스트 -----

    def test_validate_supported_by_valid(self):
        """SUPPORTED_BY: Signal -> Evidence (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.SUPPORTED_BY,
            object_type=EntityType.EVIDENCE,
        )
        assert result.is_valid is True

    def test_validate_sourced_from_valid(self):
        """SOURCED_FROM: Evidence -> Source (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.EVIDENCE,
            predicate=PredicateType.SOURCED_FROM,
            object_type=EntityType.SOURCE,
        )
        assert result.is_valid is True

    def test_validate_inferred_from_valid(self):
        """INFERRED_FROM: Brief -> ReasoningStep (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.BRIEF,
            predicate=PredicateType.INFERRED_FROM,
            object_type=EntityType.REASONING_STEP,
        )
        assert result.is_valid is True

    def test_validate_leads_to_valid(self):
        """LEADS_TO: ReasoningStep -> ReasoningStep (유효)"""
        result = self.validator.validate(
            subject_type=EntityType.REASONING_STEP,
            predicate=PredicateType.LEADS_TO,
            object_type=EntityType.REASONING_STEP,
        )
        assert result.is_valid is True

    # ----- deprecated 테스트 -----

    def test_validate_competes_with_valid(self):
        """COMPETES_WITH: Organization -> Organization (v2에서 활성화)"""
        result = self.validator.validate(
            subject_type=EntityType.ORGANIZATION,
            predicate=PredicateType.COMPETES_WITH,
            object_type=EntityType.ORGANIZATION,
        )
        # v2: COMPETES_WITH는 더 이상 deprecated가 아님
        assert result.is_valid is True
        assert not any(e.code == ValidationErrorCode.DEPRECATED_PREDICATE for e in result.warnings)

    # ----- 신뢰도 테스트 -----

    def test_validate_low_confidence_warning(self):
        """낮은 신뢰도 + 경고 있으면 PROPOSED 상태 제안"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.HAS_SCORECARD,
            object_type=EntityType.SCORECARD,
            confidence=0.5,
        )
        assert result.is_valid is True
        assert result.suggested_status == TripleStatus.PROPOSED

    def test_validate_high_confidence_verified(self):
        """높은 신뢰도 + 경고 없으면 VERIFIED 상태 제안"""
        # v2: EVALUATES_TO 사용 (HAS_SCORECARD는 deprecated)
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.EVALUATES_TO,
            object_type=EntityType.SCORECARD,
            confidence=0.9,
            evidence_ids=["EVD-001"],
        )
        assert result.is_valid is True
        assert result.suggested_status == TripleStatus.VERIFIED

    def test_validate_error_rejected(self):
        """검증 오류 시 REJECTED 상태 제안"""
        result = self.validator.validate(
            subject_type=EntityType.TOPIC,
            predicate=PredicateType.HAS_SCORECARD,
            object_type=EntityType.SCORECARD,
        )
        assert result.is_valid is False
        assert result.suggested_status == TripleStatus.REJECTED

    # ----- OBSERVED 증거 경고 테스트 -----

    def test_validate_observed_without_evidence_warning(self):
        """OBSERVED인데 증거 없으면 경고"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.HAS_PAIN,
            object_type=EntityType.TOPIC,
            assertion_type=AssertionType.OBSERVED,
            evidence_ids=None,
        )
        assert result.is_valid is True
        assert any(e.code == ValidationErrorCode.NO_EVIDENCE_FOR_OBSERVED for e in result.warnings)

    def test_validate_observed_with_evidence_no_warning(self):
        """OBSERVED + 증거 있으면 경고 없음"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.HAS_PAIN,
            object_type=EntityType.TOPIC,
            assertion_type=AssertionType.OBSERVED,
            evidence_ids=["EVD-001"],
        )
        assert not any(
            e.code == ValidationErrorCode.NO_EVIDENCE_FOR_OBSERVED for e in result.warnings
        )

    def test_validate_supported_by_no_evidence_warning(self):
        """SUPPORTED_BY는 자체가 증거 연결이므로 경고 없음"""
        result = self.validator.validate(
            subject_type=EntityType.SIGNAL,
            predicate=PredicateType.SUPPORTED_BY,
            object_type=EntityType.EVIDENCE,
            assertion_type=AssertionType.OBSERVED,
            evidence_ids=None,
        )
        assert not any(
            e.code == ValidationErrorCode.NO_EVIDENCE_FOR_OBSERVED for e in result.warnings
        )

    # ----- get_allowed_predicates 테스트 -----

    def test_get_allowed_predicates_signal_topic(self):
        """Signal -> Topic 허용 predicates"""
        allowed = self.validator.get_allowed_predicates(
            subject_type=EntityType.SIGNAL,
            object_type=EntityType.TOPIC,
        )
        assert PredicateType.HAS_PAIN in allowed
        assert PredicateType.SIMILAR_TO in allowed
        # v2: RELATED_TO는 deprecated이므로 제외됨
        assert PredicateType.RELATED_TO not in allowed

    def test_get_allowed_predicates_signal_evidence(self):
        """Signal -> Evidence 허용 predicates"""
        allowed = self.validator.get_allowed_predicates(
            subject_type=EntityType.SIGNAL,
            object_type=EntityType.EVIDENCE,
        )
        assert PredicateType.SUPPORTED_BY in allowed

    def test_get_allowed_predicates_excludes_deprecated(self):
        """deprecated predicates 제외"""
        allowed = self.validator.get_allowed_predicates(
            subject_type=EntityType.SIGNAL,
            object_type=EntityType.ORGANIZATION,
        )
        assert PredicateType.COMPETES_WITH not in allowed

    # ----- get_path_safe_predicates 테스트 -----

    def test_get_path_safe_predicates_excludes_inferred_from(self):
        """경로 안전 predicates에서 INFERRED_FROM 제외"""
        safe = self.validator.get_path_safe_predicates()
        assert PredicateType.INFERRED_FROM not in safe

    def test_get_path_safe_predicates_excludes_leads_to(self):
        """경로 안전 predicates에서 LEADS_TO 제외"""
        safe = self.validator.get_path_safe_predicates()
        assert PredicateType.LEADS_TO not in safe

    def test_get_path_safe_predicates_excludes_deprecated(self):
        """경로 안전 predicates에서 deprecated 제외"""
        safe = self.validator.get_path_safe_predicates()
        # v2: HAS_SCORECARD, HAS_BRIEF, RELATED_TO 등이 deprecated
        assert PredicateType.HAS_SCORECARD not in safe
        assert PredicateType.HAS_BRIEF not in safe
        assert PredicateType.RELATED_TO not in safe

    def test_get_path_safe_predicates_includes_core(self):
        """경로 안전 predicates에 핵심 관계 포함"""
        safe = self.validator.get_path_safe_predicates()
        # v2: EVALUATES_TO, SUMMARIZED_IN 사용 (HAS_SCORECARD, HAS_BRIEF는 deprecated)
        assert PredicateType.EVALUATES_TO in safe
        assert PredicateType.SUMMARIZED_IN in safe
        assert PredicateType.BELONGS_TO_PLAY in safe
        assert PredicateType.SUPPORTED_BY in safe


class TestValidationResult:
    """ValidationResult 단위 테스트"""

    def test_add_error_sets_invalid(self):
        """add_error 시 is_valid=False"""
        result = ValidationResult(is_valid=True)
        result.add_error(
            ValidationErrorCode.INVALID_SUBJECT_TYPE,
            "Test error message",
        )
        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_add_warning_keeps_valid(self):
        """add_warning 시 is_valid 유지"""
        result = ValidationResult(is_valid=True)
        result.add_warning(
            ValidationErrorCode.NO_EVIDENCE_FOR_OBSERVED,
            "Test warning message",
        )
        assert result.is_valid is True
        assert len(result.warnings) == 1

    def test_add_error_with_field(self):
        """add_error에 field 정보 포함"""
        result = ValidationResult(is_valid=True)
        result.add_error(
            ValidationErrorCode.INVALID_SUBJECT_TYPE,
            "Test error",
            field="subject_type",
        )
        assert result.errors[0].field == "subject_type"

    def test_add_error_with_context(self):
        """add_error에 context 정보 포함"""
        result = ValidationResult(is_valid=True)
        result.add_error(
            ValidationErrorCode.INVALID_SUBJECT_TYPE,
            "Test error",
            context={"expected": "Signal", "actual": "Topic"},
        )
        assert result.errors[0].context == {"expected": "Signal", "actual": "Topic"}


class TestPredicateConstraints:
    """PREDICATE_CONSTRAINTS 정의 테스트"""

    def test_has_scorecard_constraint(self):
        """HAS_SCORECARD 제약 확인"""
        constraint = PREDICATE_CONSTRAINTS[PredicateType.HAS_SCORECARD]
        assert EntityType.SIGNAL in constraint.subject_types
        assert EntityType.SCORECARD in constraint.object_types
        assert constraint.requires_evidence is False

    def test_inferred_from_exclude_from_path(self):
        """INFERRED_FROM은 경로 탐색에서 제외"""
        constraint = PREDICATE_CONSTRAINTS[PredicateType.INFERRED_FROM]
        assert constraint.exclude_from_path is True

    def test_leads_to_exclude_from_path(self):
        """LEADS_TO는 경로 탐색에서 제외"""
        constraint = PREDICATE_CONSTRAINTS[PredicateType.LEADS_TO]
        assert constraint.exclude_from_path is True

    def test_competes_with_not_deprecated(self):
        """COMPETES_WITH는 v2에서 활성화 (deprecated 아님)"""
        constraint = PREDICATE_CONSTRAINTS[PredicateType.COMPETES_WITH]
        assert constraint.deprecated is False
        assert EntityType.ORGANIZATION in constraint.subject_types
        assert EntityType.ORGANIZATION in constraint.object_types


# =============================================================================
# GraphQuery 테스트
# =============================================================================


class TestPathOptions:
    """PathOptions 단위 테스트"""

    def test_safe_mode_defaults(self):
        """SAFE 모드 기본값"""
        options = PathOptions(mode=PathMode.SAFE)
        assert options.include_proposed is False
        assert options.include_inferred is False

    def test_normal_mode_defaults(self):
        """NORMAL 모드 기본값"""
        options = PathOptions(mode=PathMode.NORMAL)
        assert options.include_proposed is False
        assert options.include_inferred is True

    def test_full_mode_defaults(self):
        """FULL 모드 기본값"""
        options = PathOptions(mode=PathMode.FULL)
        assert options.include_proposed is True
        assert options.include_inferred is True

    def test_default_values(self):
        """기본값 확인"""
        options = PathOptions()
        assert options.mode == PathMode.SAFE
        assert options.max_hops == 5
        assert options.max_results == 10
        assert options.min_confidence == 0.5
        assert options.inferred_weight_penalty == 0.5


class TestPathResult:
    """PathResult 단위 테스트"""

    def test_to_dict_empty_path(self):
        """빈 경로 to_dict"""
        result = PathResult()
        d = result.to_dict()
        assert d["path"] == []
        assert d["total_confidence"] == 1.0
        assert d["hop_count"] == 0

    def test_to_dict_with_path(self):
        """경로 있는 to_dict"""
        step1 = PathStep(
            entity_id="SIG-001",
            entity_type=EntityType.SIGNAL,
            entity_name="테스트 신호",
        )
        step2 = PathStep(
            entity_id="TOP-001",
            entity_type=EntityType.TOPIC,
            entity_name="테스트 토픽",
            predicate=PredicateType.HAS_PAIN,
            triple_id="TRP-001",
            confidence=0.9,
            is_inferred=False,
        )
        result = PathResult(
            path=[step1, step2],
            total_confidence=0.9,
            hop_count=1,
            contains_inferred=False,
            explanation="'테스트 신호' --[has_pain]--> '테스트 토픽'",
        )
        d = result.to_dict()
        assert len(d["path"]) == 2
        assert d["path"][0]["entity_id"] == "SIG-001"
        assert d["path"][1]["predicate"] == "has_pain"
        assert d["total_confidence"] == 0.9
        assert d["hop_count"] == 1


class TestGraphQuery:
    """GraphQuery 단위 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.graph_query = GraphQuery()
        self.mock_session = AsyncMock()

    # ----- 필터 빌드 테스트 -----

    def test_build_status_filter_safe_mode(self):
        """SAFE 모드 상태 필터"""
        options = PathOptions(mode=PathMode.SAFE)
        statuses = self.graph_query._build_status_filter(options)
        assert TripleStatus.VERIFIED in statuses
        assert TripleStatus.PROPOSED not in statuses

    def test_build_status_filter_full_mode(self):
        """FULL 모드 상태 필터"""
        options = PathOptions(mode=PathMode.FULL)
        statuses = self.graph_query._build_status_filter(options)
        assert TripleStatus.VERIFIED in statuses
        assert TripleStatus.PROPOSED in statuses

    def test_build_status_filter_with_deprecated(self):
        """deprecated 포함 상태 필터"""
        options = PathOptions(include_deprecated=True)
        statuses = self.graph_query._build_status_filter(options)
        assert TripleStatus.DEPRECATED in statuses

    def test_build_predicate_filter_default(self):
        """기본 predicate 필터 (경로 안전 predicates)"""
        options = PathOptions()
        predicates = self.graph_query._build_predicate_filter(options)
        # v2: EVALUATES_TO 사용 (HAS_SCORECARD는 deprecated)
        assert PredicateType.EVALUATES_TO in predicates
        assert PredicateType.INFERRED_FROM not in predicates

    def test_build_predicate_filter_allowed_only(self):
        """특정 predicates만 허용"""
        options = PathOptions(allowed_predicates=[PredicateType.HAS_PAIN, PredicateType.HAS_BRIEF])
        predicates = self.graph_query._build_predicate_filter(options)
        assert predicates == {PredicateType.HAS_PAIN, PredicateType.HAS_BRIEF}

    def test_build_predicate_filter_with_exclusion(self):
        """특정 predicates 제외"""
        options = PathOptions(excluded_predicates=[PredicateType.SUPPORTED_BY])
        predicates = self.graph_query._build_predicate_filter(options)
        assert PredicateType.SUPPORTED_BY not in predicates

    # ----- 엣지 가중치 계산 테스트 -----

    def test_calculate_edge_weight_observed(self):
        """OBSERVED 타입 가중치"""
        options = PathOptions()
        weight = self.graph_query._calculate_edge_weight(
            confidence=0.8,
            assertion_type=AssertionType.OBSERVED,
            options=options,
        )
        assert weight == 0.8

    def test_calculate_edge_weight_inferred(self):
        """INFERRED 타입 가중치 (페널티 적용)"""
        options = PathOptions(inferred_weight_penalty=0.5)
        weight = self.graph_query._calculate_edge_weight(
            confidence=0.8,
            assertion_type=AssertionType.INFERRED,
            options=options,
        )
        assert weight == 0.4  # 0.8 * 0.5

    # ----- 경로 설명 생성 테스트 -----

    def test_generate_path_explanation_single_node(self):
        """단일 노드 경로 설명"""
        step = PathStep(
            entity_id="SIG-001",
            entity_type=EntityType.SIGNAL,
            entity_name="신호",
        )
        explanation = self.graph_query._generate_path_explanation([step])
        assert explanation == ""

    def test_generate_path_explanation_two_nodes(self):
        """2개 노드 경로 설명"""
        step1 = PathStep(
            entity_id="SIG-001",
            entity_type=EntityType.SIGNAL,
            entity_name="신호",
        )
        step2 = PathStep(
            entity_id="TOP-001",
            entity_type=EntityType.TOPIC,
            entity_name="토픽",
            predicate=PredicateType.HAS_PAIN,
            confidence=0.9,
        )
        explanation = self.graph_query._generate_path_explanation([step1, step2])
        assert "'신호'" in explanation
        assert "--[has_pain]-->" in explanation
        assert "'토픽'" in explanation

    def test_generate_path_explanation_inferred(self):
        """추론 노드 포함 경로 설명"""
        step1 = PathStep(
            entity_id="SIG-001",
            entity_type=EntityType.SIGNAL,
            entity_name="신호",
        )
        step2 = PathStep(
            entity_id="TOP-001",
            entity_type=EntityType.TOPIC,
            entity_name="토픽",
            predicate=PredicateType.HAS_PAIN,
            is_inferred=True,
        )
        explanation = self.graph_query._generate_path_explanation([step1, step2])
        assert "(추론)" in explanation

    def test_generate_path_explanation_low_confidence(self):
        """낮은 신뢰도 노드 포함 경로 설명"""
        step1 = PathStep(
            entity_id="SIG-001",
            entity_type=EntityType.SIGNAL,
            entity_name="신호",
        )
        step2 = PathStep(
            entity_id="TOP-001",
            entity_type=EntityType.TOPIC,
            entity_name="토픽",
            predicate=PredicateType.HAS_PAIN,
            confidence=0.5,
        )
        explanation = self.graph_query._generate_path_explanation([step1, step2])
        assert "(신뢰도:" in explanation

    # ----- BFS 경로 탐색 테스트 -----

    @pytest.mark.asyncio
    async def test_find_path_bfs_source_not_found(self):
        """시작 엔티티가 없는 경우"""
        self.mock_session.get = AsyncMock(return_value=None)

        results = await self.graph_query.find_path_bfs(
            session=self.mock_session,
            source_id="SIG-001",
            target_id="TOP-001",
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_find_path_bfs_same_source_target(self):
        """시작과 목표가 같은 경우"""
        mock_entity = MagicMock(spec=Entity)
        mock_entity.entity_id = "SIG-001"
        mock_entity.entity_type = EntityType.SIGNAL
        mock_entity.name = "테스트 신호"

        self.mock_session.get = AsyncMock(return_value=mock_entity)
        self.mock_session.execute = AsyncMock(return_value=MagicMock(all=lambda: []))

        results = await self.graph_query.find_path_bfs(
            session=self.mock_session,
            source_id="SIG-001",
            target_id="SIG-001",
        )
        assert len(results) == 1
        assert results[0].hop_count == 0

    @pytest.mark.asyncio
    async def test_find_path_bfs_direct_path(self):
        """직접 연결된 경로"""
        # 시작 엔티티
        mock_source = MagicMock(spec=Entity)
        mock_source.entity_id = "SIG-001"
        mock_source.entity_type = EntityType.SIGNAL
        mock_source.name = "테스트 신호"

        # 목표 엔티티
        mock_target = MagicMock(spec=Entity)
        mock_target.entity_id = "TOP-001"
        mock_target.entity_type = EntityType.TOPIC
        mock_target.name = "테스트 토픽"

        # Triple
        mock_triple = MagicMock(spec=Triple)
        mock_triple.object_id = "TOP-001"
        mock_triple.predicate = PredicateType.HAS_PAIN
        mock_triple.triple_id = "TRP-001"
        mock_triple.confidence = 0.9
        mock_triple.assertion_type = AssertionType.OBSERVED

        self.mock_session.get = AsyncMock(return_value=mock_source)

        # 첫 번째 execute 호출 (인접 엣지 조회)
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[(mock_triple, mock_target)])
        self.mock_session.execute = AsyncMock(return_value=mock_result)

        results = await self.graph_query.find_path_bfs(
            session=self.mock_session,
            source_id="SIG-001",
            target_id="TOP-001",
        )

        assert len(results) == 1
        assert results[0].hop_count == 1
        assert results[0].total_confidence == 0.9

    # ----- 인접 엔티티 조회 테스트 -----

    @pytest.mark.asyncio
    async def test_get_neighbors_outgoing(self):
        """outgoing 방향 인접 엔티티 조회"""
        mock_entity = MagicMock(spec=Entity)
        mock_entity.entity_id = "TOP-001"
        mock_entity.to_dict = MagicMock(return_value={"entity_id": "TOP-001"})

        mock_triple = MagicMock(spec=Triple)
        mock_triple.to_dict = MagicMock(return_value={"triple_id": "TRP-001"})

        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[(mock_triple, mock_entity)])
        self.mock_session.execute = AsyncMock(return_value=mock_result)

        neighbors = await self.graph_query.get_neighbors(
            session=self.mock_session,
            entity_id="SIG-001",
            direction="outgoing",
        )

        assert len(neighbors) == 1
        assert neighbors[0]["direction"] == "outgoing"

    @pytest.mark.asyncio
    async def test_get_neighbors_incoming(self):
        """incoming 방향 인접 엔티티 조회"""
        mock_entity = MagicMock(spec=Entity)
        mock_entity.entity_id = "SIG-001"
        mock_entity.to_dict = MagicMock(return_value={"entity_id": "SIG-001"})

        mock_triple = MagicMock(spec=Triple)
        mock_triple.to_dict = MagicMock(return_value={"triple_id": "TRP-001"})

        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[(mock_triple, mock_entity)])
        self.mock_session.execute = AsyncMock(return_value=mock_result)

        neighbors = await self.graph_query.get_neighbors(
            session=self.mock_session,
            entity_id="TOP-001",
            direction="incoming",
        )

        assert len(neighbors) == 1
        assert neighbors[0]["direction"] == "incoming"

    @pytest.mark.asyncio
    async def test_get_neighbors_both(self):
        """양방향 인접 엔티티 조회"""
        mock_entity = MagicMock(spec=Entity)
        mock_entity.entity_id = "ENT-001"
        mock_entity.to_dict = MagicMock(return_value={"entity_id": "ENT-001"})

        mock_triple = MagicMock(spec=Triple)
        mock_triple.to_dict = MagicMock(return_value={"triple_id": "TRP-001"})

        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[(mock_triple, mock_entity)])
        self.mock_session.execute = AsyncMock(return_value=mock_result)

        neighbors = await self.graph_query.get_neighbors(
            session=self.mock_session,
            entity_id="SIG-001",
            direction="both",
        )

        # outgoing + incoming 각각 1개씩
        assert len(neighbors) == 2


class TestFindEvidenceChain:
    """find_evidence_chain 헬퍼 함수 테스트"""

    @pytest.mark.asyncio
    async def test_find_evidence_chain_empty(self):
        """근거 체인이 없는 경우"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[])
        mock_session.execute = AsyncMock(return_value=mock_result)

        chain = await find_evidence_chain(
            session=mock_session,
            entity_id="SIG-001",
        )
        assert chain == []

    @pytest.mark.asyncio
    async def test_find_evidence_chain_one_level(self):
        """1단계 근거 체인"""
        mock_session = AsyncMock()

        mock_entity = MagicMock(spec=Entity)
        mock_entity.entity_id = "EVD-001"
        mock_entity.to_dict = MagicMock(return_value={"entity_id": "EVD-001"})

        mock_triple = MagicMock(spec=Triple)
        mock_triple.subject_id = "SIG-001"
        mock_triple.object_id = "EVD-001"
        mock_triple.predicate = PredicateType.SUPPORTED_BY
        mock_triple.evidence_span = {"text": "근거 텍스트"}

        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[(mock_triple, mock_entity)])

        # 두 번째 호출은 빈 결과
        mock_empty_result = MagicMock()
        mock_empty_result.all = MagicMock(return_value=[])

        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_empty_result])

        chain = await find_evidence_chain(
            session=mock_session,
            entity_id="SIG-001",
            max_depth=2,
        )

        assert len(chain) == 1
        assert chain[0]["from_id"] == "SIG-001"
        assert chain[0]["to_id"] == "EVD-001"


# =============================================================================
# OntologyRepository 테스트
# =============================================================================


class TestOntologyRepository:
    """OntologyRepository 단위 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.repo = OntologyRepository()
        self.mock_db = AsyncMock()

    # ----- ID 생성 테스트 -----

    def test_generate_entity_id_signal(self):
        """Signal 엔티티 ID 생성"""
        entity_id = self.repo._generate_entity_id(EntityType.SIGNAL)
        assert entity_id.startswith("SIG-")
        assert len(entity_id) == 12  # SIG- + 8

    def test_generate_entity_id_topic(self):
        """Topic 엔티티 ID 생성"""
        entity_id = self.repo._generate_entity_id(EntityType.TOPIC)
        assert entity_id.startswith("TOP-")

    def test_generate_entity_id_scorecard(self):
        """Scorecard 엔티티 ID 생성"""
        entity_id = self.repo._generate_entity_id(EntityType.SCORECARD)
        assert entity_id.startswith("SCR-")

    def test_generate_entity_id_brief(self):
        """Brief 엔티티 ID 생성"""
        entity_id = self.repo._generate_entity_id(EntityType.BRIEF)
        assert entity_id.startswith("BRF-")

    def test_generate_entity_id_evidence(self):
        """Evidence 엔티티 ID 생성"""
        entity_id = self.repo._generate_entity_id(EntityType.EVIDENCE)
        assert entity_id.startswith("EVD-")

    def test_generate_entity_id_source(self):
        """Source 엔티티 ID 생성"""
        entity_id = self.repo._generate_entity_id(EntityType.SOURCE)
        assert entity_id.startswith("SRC-")

    def test_generate_entity_id_play(self):
        """Play 엔티티 ID 생성"""
        entity_id = self.repo._generate_entity_id(EntityType.PLAY)
        assert entity_id.startswith("PLY-")

    def test_generate_entity_id_organization(self):
        """Organization 엔티티 ID 생성"""
        entity_id = self.repo._generate_entity_id(EntityType.ORGANIZATION)
        assert entity_id.startswith("ORG-")  # P1: Customer/Competitor 통합

    def test_generate_triple_id(self):
        """Triple ID 생성"""
        triple_id = self.repo._generate_triple_id()
        assert triple_id.startswith("TRP-")
        assert len(triple_id) == 16  # TRP- + 12

    # ----- Entity CRUD 테스트 -----

    @pytest.mark.asyncio
    async def test_create_entity(self):
        """Entity 생성"""
        entity = await self.repo.create_entity(
            db=self.mock_db,
            entity_type=EntityType.SIGNAL,
            name="테스트 신호",
            description="테스트 설명",
            properties={"key": "value"},
            confidence=0.9,
        )

        self.mock_db.add.assert_called_once()
        self.mock_db.flush.assert_called_once()
        assert entity.entity_type == EntityType.SIGNAL
        assert entity.name == "테스트 신호"
        assert entity.entity_id.startswith("SIG-")

    @pytest.mark.asyncio
    async def test_get_entity_found(self):
        """Entity 조회 (존재)"""
        mock_entity = MagicMock(spec=Entity)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_entity)
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        entity = await self.repo.get_entity(self.mock_db, "SIG-001")
        assert entity == mock_entity

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self):
        """Entity 조회 (미존재)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        entity = await self.repo.get_entity(self.mock_db, "SIG-999")
        assert entity is None

    @pytest.mark.asyncio
    async def test_get_entity_by_external_ref(self):
        """외부 참조 ID로 Entity 조회"""
        mock_entity = MagicMock(spec=Entity)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_entity)
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        entity = await self.repo.get_entity_by_external_ref(
            self.mock_db,
            external_ref_id="EXT-001",
        )
        assert entity == mock_entity

    @pytest.mark.asyncio
    async def test_list_entities_with_type_filter(self):
        """Entity 목록 조회 (타입 필터)"""
        mock_entities = [MagicMock(spec=Entity), MagicMock(spec=Entity)]
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=mock_entities))
        )

        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.scalar = AsyncMock(return_value=2)

        entities, total = await self.repo.list_entities(
            db=self.mock_db,
            entity_type=EntityType.SIGNAL,
            skip=0,
            limit=20,
        )

        assert len(entities) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_entities_with_search(self):
        """Entity 목록 조회 (검색어)"""
        mock_entities = [MagicMock(spec=Entity)]
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=mock_entities))
        )

        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.scalar = AsyncMock(return_value=1)

        entities, total = await self.repo.list_entities(
            db=self.mock_db,
            search="테스트",
        )

        assert len(entities) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_update_entity_found(self):
        """Entity 업데이트 (존재)"""
        mock_entity = MagicMock(spec=Entity)
        mock_entity.name = "기존 이름"

        with patch.object(self.repo, "get_entity", return_value=mock_entity):
            entity = await self.repo.update_entity(
                db=self.mock_db,
                entity_id="SIG-001",
                name="새 이름",
            )

        assert entity.name == "새 이름"
        self.mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_entity_not_found(self):
        """Entity 업데이트 (미존재)"""
        with patch.object(self.repo, "get_entity", return_value=None):
            entity = await self.repo.update_entity(
                db=self.mock_db,
                entity_id="SIG-999",
                name="새 이름",
            )

        assert entity is None

    @pytest.mark.asyncio
    async def test_delete_entity_found(self):
        """Entity 삭제 (존재)"""
        mock_entity = MagicMock(spec=Entity)

        with patch.object(self.repo, "get_entity", return_value=mock_entity):
            result = await self.repo.delete_entity(self.mock_db, "SIG-001")

        assert result is True
        self.mock_db.delete.assert_called_once_with(mock_entity)
        self.mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_entity_not_found(self):
        """Entity 삭제 (미존재)"""
        with patch.object(self.repo, "get_entity", return_value=None):
            result = await self.repo.delete_entity(self.mock_db, "SIG-999")

        assert result is False

    # ----- Triple CRUD 테스트 -----

    @pytest.mark.asyncio
    async def test_create_triple(self):
        """Triple 생성"""
        triple = await self.repo.create_triple(
            db=self.mock_db,
            subject_id="SIG-001",
            predicate=PredicateType.HAS_PAIN,
            object_id="TOP-001",
            weight=1.0,
            confidence=0.9,
            evidence_ids=["EVD-001"],
        )

        self.mock_db.add.assert_called_once()
        self.mock_db.flush.assert_called_once()
        assert triple.subject_id == "SIG-001"
        assert triple.predicate == PredicateType.HAS_PAIN
        assert triple.object_id == "TOP-001"
        assert triple.triple_id.startswith("TRP-")

    @pytest.mark.asyncio
    async def test_get_triple_found(self):
        """Triple 조회 (존재)"""
        mock_triple = MagicMock(spec=Triple)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_triple)
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        triple = await self.repo.get_triple(self.mock_db, "TRP-001")
        assert triple == mock_triple

    @pytest.mark.asyncio
    async def test_get_triple_not_found(self):
        """Triple 조회 (미존재)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        triple = await self.repo.get_triple(self.mock_db, "TRP-999")
        assert triple is None

    @pytest.mark.asyncio
    async def test_query_triples_by_subject(self):
        """Triple 쿼리 (subject_id 기준)"""
        mock_triples = [MagicMock(spec=Triple), MagicMock(spec=Triple)]
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=mock_triples))
        )

        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.scalar = AsyncMock(return_value=2)

        triples, total = await self.repo.query_triples(
            db=self.mock_db,
            subject_id="SIG-001",
        )

        assert len(triples) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_query_triples_by_predicate(self):
        """Triple 쿼리 (predicate 기준)"""
        mock_triples = [MagicMock(spec=Triple)]
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=mock_triples))
        )

        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.scalar = AsyncMock(return_value=1)

        triples, total = await self.repo.query_triples(
            db=self.mock_db,
            predicate=PredicateType.HAS_PAIN,
        )

        assert len(triples) == 1

    @pytest.mark.asyncio
    async def test_query_triples_by_object(self):
        """Triple 쿼리 (object_id 기준)"""
        mock_triples = [MagicMock(spec=Triple)]
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=mock_triples))
        )

        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.scalar = AsyncMock(return_value=1)

        triples, total = await self.repo.query_triples(
            db=self.mock_db,
            object_id="TOP-001",
        )

        assert len(triples) == 1

    @pytest.mark.asyncio
    async def test_query_triples_with_min_confidence(self):
        """Triple 쿼리 (최소 신뢰도)"""
        mock_triples = [MagicMock(spec=Triple)]
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=mock_triples))
        )

        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.scalar = AsyncMock(return_value=1)

        triples, total = await self.repo.query_triples(
            db=self.mock_db,
            min_confidence=0.7,
        )

        assert len(triples) == 1

    @pytest.mark.asyncio
    async def test_delete_triple_found(self):
        """Triple 삭제 (존재)"""
        mock_triple = MagicMock(spec=Triple)

        with patch.object(self.repo, "get_triple", return_value=mock_triple):
            result = await self.repo.delete_triple(self.mock_db, "TRP-001")

        assert result is True
        self.mock_db.delete.assert_called_once_with(mock_triple)

    @pytest.mark.asyncio
    async def test_delete_triple_not_found(self):
        """Triple 삭제 (미존재)"""
        with patch.object(self.repo, "get_triple", return_value=None):
            result = await self.repo.delete_triple(self.mock_db, "TRP-999")

        assert result is False

    # ----- Graph Queries 테스트 -----

    @pytest.mark.asyncio
    async def test_get_entity_graph_center_not_found(self):
        """Entity 그래프 조회 (중심 엔티티 없음)"""
        with patch.object(self.repo, "get_entity", return_value=None):
            graph = await self.repo.get_entity_graph(
                db=self.mock_db,
                entity_id="SIG-999",
            )

        assert graph["center"] is None
        assert graph["nodes"] == []
        assert graph["edges"] == []

    @pytest.mark.asyncio
    async def test_get_entity_graph_with_center(self):
        """Entity 그래프 조회 (중심 엔티티만)"""
        mock_center = MagicMock(spec=Entity)
        mock_center.entity_id = "SIG-001"

        # execute 결과 mock (scalars().all() 체인 지원)
        def make_execute_result(data):
            scalars_result = MagicMock()
            scalars_result.all.return_value = data
            result = MagicMock()
            result.scalars.return_value = scalars_result
            return result

        # 호출 순서: outgoing, incoming, nodes batch fetch
        self.mock_db.execute = AsyncMock(
            side_effect=[
                make_execute_result([]),  # outgoing triples
                make_execute_result([]),  # incoming triples
                make_execute_result([mock_center]),  # nodes batch fetch (center만)
            ]
        )

        with patch.object(self.repo, "get_entity", return_value=mock_center):
            graph = await self.repo.get_entity_graph(
                db=self.mock_db,
                entity_id="SIG-001",
                depth=1,
            )

        assert graph["center"] == mock_center
        assert len(graph["nodes"]) == 1

    @pytest.mark.asyncio
    async def test_get_entity_graph_with_edges(self):
        """Entity 그래프 조회 (엣지 포함)"""
        mock_center = MagicMock(spec=Entity)
        mock_center.entity_id = "SIG-001"

        mock_neighbor = MagicMock(spec=Entity)
        mock_neighbor.entity_id = "TOP-001"

        mock_triple = MagicMock(spec=Triple)
        mock_triple.triple_id = "TRP-001"
        mock_triple.subject_id = "SIG-001"
        mock_triple.object_id = "TOP-001"
        mock_triple.predicate = PredicateType.HAS_PAIN

        # execute 결과 mock (scalars().all() 체인 지원)
        def make_execute_result(data):
            scalars_result = MagicMock()
            scalars_result.all.return_value = data
            result = MagicMock()
            result.scalars.return_value = scalars_result
            return result

        async def mock_get_entity(db, entity_id):
            if entity_id == "SIG-001":
                return mock_center
            elif entity_id == "TOP-001":
                return mock_neighbor
            return None

        # execute 호출 순서: outgoing, incoming, nodes batch fetch
        # visited_nodes = {SIG-001, TOP-001} 이므로 두 노드 모두 반환
        self.mock_db.execute = AsyncMock(
            side_effect=[
                make_execute_result([mock_triple]),  # outgoing triples (depth 1)
                make_execute_result([]),  # incoming triples (depth 1)
                make_execute_result([mock_center, mock_neighbor]),  # nodes batch fetch
            ]
        )

        with patch.object(self.repo, "get_entity", side_effect=mock_get_entity):
            graph = await self.repo.get_entity_graph(
                db=self.mock_db,
                entity_id="SIG-001",
                depth=1,
            )

        assert len(graph["edges"]) == 1
        assert len(graph["nodes"]) == 2

    @pytest.mark.asyncio
    async def test_get_entity_graph_with_predicate_filter(self):
        """Entity 그래프 조회 (predicate 필터)"""
        mock_center = MagicMock(spec=Entity)
        mock_center.entity_id = "SIG-001"

        mock_neighbor = MagicMock(spec=Entity)
        mock_neighbor.entity_id = "TOP-001"

        # HAS_PAIN만 필터링되므로 하나만 포함
        mock_triple_pain = MagicMock(spec=Triple)
        mock_triple_pain.triple_id = "TRP-001"
        mock_triple_pain.subject_id = "SIG-001"
        mock_triple_pain.object_id = "TOP-001"
        mock_triple_pain.predicate = PredicateType.HAS_PAIN

        # execute 결과 mock (scalars().all() 체인 지원)
        def make_execute_result(data):
            scalars_result = MagicMock()
            scalars_result.all.return_value = data
            result = MagicMock()
            result.scalars.return_value = scalars_result
            return result

        # execute 호출 순서: outgoing (필터 적용됨), incoming, nodes batch fetch
        self.mock_db.execute = AsyncMock(
            side_effect=[
                make_execute_result([mock_triple_pain]),  # outgoing (HAS_PAIN만)
                make_execute_result([]),  # incoming
                make_execute_result([mock_center, mock_neighbor]),  # nodes batch fetch
            ]
        )

        with patch.object(self.repo, "get_entity", return_value=mock_center):
            graph = await self.repo.get_entity_graph(
                db=self.mock_db,
                entity_id="SIG-001",
                depth=1,
                predicates=[PredicateType.HAS_PAIN],
            )

        # HAS_PAIN만 포함
        assert len(graph["edges"]) == 1
        assert graph["edges"][0].predicate == PredicateType.HAS_PAIN

    # ----- 경로 탐색 테스트 -----

    @pytest.mark.asyncio
    async def test_find_path_same_entity(self):
        """경로 탐색 (같은 엔티티)"""
        path = await self.repo.find_path(
            db=self.mock_db,
            source_id="SIG-001",
            target_id="SIG-001",
        )
        assert path == []

    @pytest.mark.asyncio
    async def test_find_path_direct_connection(self):
        """경로 탐색 (직접 연결)"""
        mock_triple = MagicMock(spec=Triple)
        mock_triple.object_id = "TOP-001"

        with patch.object(self.repo, "query_triples", return_value=([mock_triple], 1)):
            path = await self.repo.find_path(
                db=self.mock_db,
                source_id="SIG-001",
                target_id="TOP-001",
            )

        assert len(path) == 1
        assert path[0] == mock_triple

    @pytest.mark.asyncio
    async def test_find_path_no_connection(self):
        """경로 탐색 (연결 없음)"""
        with patch.object(self.repo, "query_triples", return_value=([], 0)):
            path = await self.repo.find_path(
                db=self.mock_db,
                source_id="SIG-001",
                target_id="TOP-999",
            )

        assert path == []

    @pytest.mark.asyncio
    async def test_find_path_max_depth_reached(self):
        """경로 탐색 (최대 깊이 초과)"""
        mock_triple = MagicMock(spec=Triple)
        mock_triple.object_id = "NEXT-001"

        with patch.object(self.repo, "query_triples", return_value=([mock_triple], 1)):
            path = await self.repo.find_path(
                db=self.mock_db,
                source_id="SIG-001",
                target_id="TOP-999",
                max_depth=1,
            )

        # 깊이 1에서 찾지 못하면 빈 경로
        assert path == []

    # ----- 유사 엔티티 검색 테스트 -----

    @pytest.mark.asyncio
    async def test_get_similar_entities_empty(self):
        """유사 엔티티 검색 (결과 없음)"""

        # execute 결과 mock (scalars().all() 체인 지원)
        def make_execute_result(data):
            scalars_result = MagicMock()
            scalars_result.all.return_value = data
            result = MagicMock()
            result.scalars.return_value = scalars_result
            return result

        self.mock_db.execute = AsyncMock(return_value=make_execute_result([]))

        results = await self.repo.get_similar_entities(
            db=self.mock_db,
            entity_id="SIG-001",
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_get_similar_entities_found(self):
        """유사 엔티티 검색 (결과 있음)"""
        mock_similar_entity = MagicMock(spec=Entity)
        mock_similar_entity.entity_id = "SIG-002"

        mock_triple = MagicMock(spec=Triple)
        mock_triple.subject_id = "SIG-001"
        mock_triple.object_id = "SIG-002"
        mock_triple.weight = 0.9
        mock_triple.subject = None  # subject는 source entity
        mock_triple.object = mock_similar_entity  # object는 유사 엔티티

        # execute 결과 mock (scalars().all() 체인 지원)
        def make_execute_result(data):
            scalars_result = MagicMock()
            scalars_result.all.return_value = data
            result = MagicMock()
            result.scalars.return_value = scalars_result
            return result

        self.mock_db.execute = AsyncMock(return_value=make_execute_result([mock_triple]))

        results = await self.repo.get_similar_entities(
            db=self.mock_db,
            entity_id="SIG-001",
        )

        assert len(results) == 1
        assert results[0][0] == mock_similar_entity
        assert results[0][1] == 0.9

    # ----- 추론 경로 역추적 테스트 -----

    @pytest.mark.asyncio
    async def test_get_reasoning_path_empty(self):
        """추론 경로 역추적 (경로 없음)"""
        with patch.object(self.repo, "query_triples", return_value=([], 0)):
            path = await self.repo.get_reasoning_path(
                db=self.mock_db,
                conclusion_entity_id="RST-001",
            )

        assert path == []

    @pytest.mark.asyncio
    async def test_get_reasoning_path_found(self):
        """추론 경로 역추적 (경로 있음)"""
        mock_triple1 = MagicMock(spec=Triple)
        mock_triple1.subject_id = "RST-001"
        mock_triple1.object_id = "RST-002"

        mock_triple2 = MagicMock(spec=Triple)
        mock_triple2.subject_id = "RST-000"
        mock_triple2.object_id = "RST-001"

        call_count = [0]

        async def mock_query_triples(db, object_id=None, predicate=None, limit=1):
            call_count[0] += 1
            if call_count[0] == 1:
                return ([mock_triple1], 1)
            elif call_count[0] == 2:
                return ([mock_triple2], 1)
            return ([], 0)

        with patch.object(self.repo, "query_triples", side_effect=mock_query_triples):
            path = await self.repo.get_reasoning_path(
                db=self.mock_db,
                conclusion_entity_id="RST-002",
                max_depth=3,
            )

        assert len(path) >= 1

    # ----- 통계 테스트 -----

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """온톨로지 통계 조회"""
        # Entity 통계 mock row
        entity_row = MagicMock()
        entity_row.entity_type = EntityType.SIGNAL
        entity_row.count = 10

        # Triple 통계 mock row
        triple_row = MagicMock()
        triple_row.predicate = PredicateType.HAS_PAIN
        triple_row.count = 20

        # execute 결과 mock
        entity_result = MagicMock()
        entity_result.all.return_value = [entity_row]

        triple_result = MagicMock()
        triple_result.all.return_value = [triple_row]

        # execute 호출 순서에 따른 반환값 설정
        self.mock_db.execute = AsyncMock(side_effect=[entity_result, triple_result])

        # scalar (평균 신뢰도)
        self.mock_db.scalar = AsyncMock(return_value=0.85)

        stats = await self.repo.get_stats(self.mock_db)

        assert stats["entity_count"] == 10
        assert stats["triple_count"] == 20
        assert stats["avg_confidence"] == 0.85
        assert "entity_by_type" in stats
        assert "triple_by_predicate" in stats
        # EntityType.SIGNAL.value = "Signal", PredicateType.HAS_PAIN.value = "has_pain"
        assert stats["entity_by_type"]["Signal"] == 10
        assert stats["triple_by_predicate"]["has_pain"] == 20


class TestOntologyRepositorySingleton:
    """싱글톤 인스턴스 테스트"""

    def test_ontology_repo_singleton(self):
        """ontology_repo 싱글톤 확인"""
        from backend.database.repositories.ontology import ontology_repo

        assert isinstance(ontology_repo, OntologyRepository)
