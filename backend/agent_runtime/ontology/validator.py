"""
Triple 검증기 (P0)

Predicate별 도메인/레인지/필수연결 제약을 코드로 강제
SHACL/OWL까지 안 가더라도, 코드 레벨 validator만 있어도 오염이 확 줄어듦

검증 실패 시:
- proposed_triples 큐에 격리
- 검증 통과한 것만 verified 승격
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.database.models.entity import EntityType
from backend.database.models.triple import (
    AssertionType,
    PredicateType,
    TripleStatus,
)


class ValidationErrorCode(Enum):
    """검증 오류 코드"""

    # 도메인/레인지 오류
    INVALID_SUBJECT_TYPE = "INVALID_SUBJECT_TYPE"
    INVALID_OBJECT_TYPE = "INVALID_OBJECT_TYPE"

    # 필수 연결 오류
    MISSING_REQUIRED_EVIDENCE = "MISSING_REQUIRED_EVIDENCE"
    MISSING_REQUIRED_SOURCE = "MISSING_REQUIRED_SOURCE"

    # 신뢰도 오류
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NO_EVIDENCE_FOR_OBSERVED = "NO_EVIDENCE_FOR_OBSERVED"

    # 구조 오류
    SELF_REFERENCE = "SELF_REFERENCE"
    DUPLICATE_TRIPLE = "DUPLICATE_TRIPLE"
    CIRCULAR_REFERENCE = "CIRCULAR_REFERENCE"

    # deprecated 사용
    DEPRECATED_PREDICATE = "DEPRECATED_PREDICATE"


@dataclass
class ValidationError:
    """검증 오류"""

    code: ValidationErrorCode
    message: str
    field: str | None = None
    context: dict[str, Any] | None = None


@dataclass
class ValidationResult:
    """검증 결과"""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    suggested_status: TripleStatus = TripleStatus.PROPOSED

    def add_error(self, code: ValidationErrorCode, message: str, **kwargs):
        self.errors.append(ValidationError(code=code, message=message, **kwargs))
        self.is_valid = False

    def add_warning(self, code: ValidationErrorCode, message: str, **kwargs):
        self.warnings.append(ValidationError(code=code, message=message, **kwargs))


@dataclass
class PredicateConstraint:
    """Predicate 제약 정의"""

    # 허용되는 Subject 타입
    subject_types: set[EntityType]

    # 허용되는 Object 타입
    object_types: set[EntityType]

    # 필수 연결 (최소 1개 필요)
    requires_evidence: bool = False
    requires_source: bool = False

    # 최소 신뢰도
    min_confidence: float = 0.0

    # deprecated 여부
    deprecated: bool = False
    deprecated_message: str | None = None

    # 경로 탐색에서 제외 권장
    exclude_from_path: bool = False


# v2: Predicate별 도메인/레인지/필수연결 제약 (28종)
PREDICATE_CONSTRAINTS: dict[PredicateType, PredicateConstraint] = {
    # ===== Pipeline Flow Relations (6종) =====
    PredicateType.GENERATES: PredicateConstraint(
        subject_types={EntityType.ACTIVITY},
        object_types={EntityType.SIGNAL},
        requires_evidence=True,
        min_confidence=0.7,
    ),
    PredicateType.EVALUATES_TO: PredicateConstraint(
        subject_types={EntityType.SIGNAL},
        object_types={EntityType.SCORECARD},
    ),
    PredicateType.SUMMARIZED_IN: PredicateConstraint(
        subject_types={EntityType.SIGNAL},
        object_types={EntityType.BRIEF},
    ),
    PredicateType.VALIDATED_BY: PredicateConstraint(
        subject_types={EntityType.BRIEF},
        object_types={EntityType.VALIDATION},
    ),
    PredicateType.PILOTS_AS: PredicateConstraint(
        subject_types={EntityType.VALIDATION},
        object_types={EntityType.PILOT},
    ),
    PredicateType.PROGRESSES_TO: PredicateConstraint(
        subject_types={
            EntityType.ACTIVITY,
            EntityType.SIGNAL,
            EntityType.SCORECARD,
            EntityType.BRIEF,
            EntityType.VALIDATION,
            EntityType.PILOT,
        },
        object_types={
            EntityType.ACTIVITY,
            EntityType.SIGNAL,
            EntityType.SCORECARD,
            EntityType.BRIEF,
            EntityType.VALIDATION,
            EntityType.PILOT,
        },
    ),
    # ===== Topic Relations (4종) =====
    PredicateType.HAS_PAIN: PredicateConstraint(
        subject_types={EntityType.SIGNAL},
        object_types={EntityType.TOPIC},
    ),
    PredicateType.SIMILAR_TO: PredicateConstraint(
        subject_types={EntityType.TOPIC, EntityType.SIGNAL, EntityType.TREND},
        object_types={EntityType.TOPIC, EntityType.SIGNAL, EntityType.TREND},
    ),
    PredicateType.PARENT_OF: PredicateConstraint(
        subject_types={EntityType.TOPIC, EntityType.INDUSTRY},
        object_types={EntityType.TOPIC, EntityType.INDUSTRY},
    ),
    PredicateType.ADDRESSES: PredicateConstraint(
        subject_types={EntityType.TECHNOLOGY},
        object_types={EntityType.TOPIC, EntityType.TREND},
    ),
    # ===== Organization Relations (6종) =====
    PredicateType.TARGETS: PredicateConstraint(
        subject_types={EntityType.SIGNAL, EntityType.BRIEF, EntityType.ACTIVITY},
        object_types={EntityType.ORGANIZATION, EntityType.CUSTOMER},
    ),
    PredicateType.EMPLOYS: PredicateConstraint(
        subject_types={EntityType.ORGANIZATION, EntityType.TEAM},
        object_types={EntityType.PERSON},
    ),
    PredicateType.PARTNERS_WITH: PredicateConstraint(
        subject_types={EntityType.ORGANIZATION},
        object_types={EntityType.ORGANIZATION},
    ),
    PredicateType.COMPETES_WITH: PredicateConstraint(
        subject_types={EntityType.ORGANIZATION},
        object_types={EntityType.ORGANIZATION, EntityType.COMPETITOR},
    ),
    PredicateType.SUBSIDIARY_OF: PredicateConstraint(
        subject_types={EntityType.ORGANIZATION},
        object_types={EntityType.ORGANIZATION},
    ),
    PredicateType.IN_INDUSTRY: PredicateConstraint(
        subject_types={EntityType.ORGANIZATION, EntityType.SIGNAL, EntityType.CUSTOMER},
        object_types={EntityType.INDUSTRY, EntityType.MARKET_SEGMENT},
    ),
    # ===== Person Relations (4종) =====
    PredicateType.OWNS: PredicateConstraint(
        subject_types={EntityType.PERSON},
        object_types={EntityType.SIGNAL, EntityType.BRIEF, EntityType.TASK},
    ),
    PredicateType.DECIDES: PredicateConstraint(
        subject_types={EntityType.PERSON},
        object_types={EntityType.DECISION},
    ),
    PredicateType.ATTENDED: PredicateConstraint(
        subject_types={EntityType.PERSON},
        object_types={EntityType.MEETING, EntityType.ACTIVITY},
    ),
    PredicateType.REPORTS_TO: PredicateConstraint(
        subject_types={EntityType.PERSON},
        object_types={EntityType.PERSON},
    ),
    # ===== Evidence Relations (4종) =====
    PredicateType.SUPPORTED_BY: PredicateConstraint(
        subject_types=set(EntityType),  # 모든 타입
        object_types={EntityType.EVIDENCE},
    ),
    PredicateType.SOURCED_FROM: PredicateConstraint(
        subject_types={EntityType.EVIDENCE},
        object_types={EntityType.SOURCE},
    ),
    PredicateType.INFERRED_FROM: PredicateConstraint(
        subject_types={EntityType.BRIEF, EntityType.SCORECARD, EntityType.DECISION},
        object_types={EntityType.REASONING_STEP},
        exclude_from_path=True,
    ),
    PredicateType.CONTRADICTS: PredicateConstraint(
        subject_types={EntityType.EVIDENCE},
        object_types={EntityType.EVIDENCE},
    ),
    # ===== Operational Relations (4종) =====
    PredicateType.BELONGS_TO_PLAY: PredicateConstraint(
        subject_types={EntityType.SIGNAL, EntityType.BRIEF, EntityType.ACTIVITY},
        object_types={EntityType.PLAY},
    ),
    PredicateType.SCHEDULED_FOR: PredicateConstraint(
        subject_types={EntityType.TASK},
        object_types={EntityType.MEETING, EntityType.MILESTONE},
    ),
    PredicateType.ACHIEVES: PredicateConstraint(
        subject_types={EntityType.TASK, EntityType.PILOT},
        object_types={EntityType.MILESTONE},
    ),
    PredicateType.SAME_AS: PredicateConstraint(
        subject_types=set(EntityType),
        object_types=set(EntityType),
    ),
    # ===== Deprecated (하위 호환) =====
    PredicateType.HAS_SCORECARD: PredicateConstraint(
        subject_types={EntityType.SIGNAL},
        object_types={EntityType.SCORECARD},
        deprecated=True,
        deprecated_message="Use EVALUATES_TO instead",
    ),
    PredicateType.HAS_BRIEF: PredicateConstraint(
        subject_types={EntityType.SIGNAL},
        object_types={EntityType.BRIEF},
        deprecated=True,
        deprecated_message="Use SUMMARIZED_IN instead",
    ),
    PredicateType.RELATED_TO: PredicateConstraint(
        subject_types={EntityType.TOPIC, EntityType.SIGNAL, EntityType.TECHNOLOGY},
        object_types={EntityType.TOPIC, EntityType.SIGNAL, EntityType.TECHNOLOGY},
        deprecated=True,
        deprecated_message="Use more specific relations (SIMILAR_TO, ADDRESSES, etc.)",
    ),
    PredicateType.USES_TECHNOLOGY: PredicateConstraint(
        subject_types={EntityType.SIGNAL, EntityType.ORGANIZATION},
        object_types={EntityType.TECHNOLOGY},
        deprecated=True,
        deprecated_message="Use ADDRESSES instead",
    ),
    PredicateType.HAS_ROLE: PredicateConstraint(
        subject_types={EntityType.ORGANIZATION},
        object_types={EntityType.PLAY, EntityType.SIGNAL},
        deprecated=True,
        deprecated_message="Use EMPLOYS with role property instead",
    ),
    PredicateType.LEADS_TO: PredicateConstraint(
        subject_types={EntityType.REASONING_STEP},
        object_types={EntityType.REASONING_STEP},
        deprecated=True,
        deprecated_message="Use PROGRESSES_TO instead",
        exclude_from_path=True,
    ),
}


class TripleValidator:
    """
    Triple 검증기

    Predicate별 제약을 검사하고 검증 결과 반환
    검증 실패 시 proposed 상태로 격리
    """

    def __init__(self):
        self.constraints = PREDICATE_CONSTRAINTS

    def validate(
        self,
        subject_type: EntityType,
        predicate: PredicateType,
        object_type: EntityType,
        assertion_type: AssertionType = AssertionType.OBSERVED,
        evidence_ids: list[str] | None = None,
        confidence: float = 1.0,
        properties: dict | None = None,
    ) -> ValidationResult:
        """
        Triple 검증

        Args:
            subject_type: Subject 엔티티 타입
            predicate: Predicate 타입
            object_type: Object 엔티티 타입
            assertion_type: observed/inferred
            evidence_ids: 근거 ID 목록
            confidence: 신뢰도
            properties: 추가 속성

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        # 제약 조회
        constraint = self.constraints.get(predicate)
        if not constraint:
            # 알 수 없는 predicate는 일단 통과 (확장성)
            result.add_warning(
                ValidationErrorCode.DEPRECATED_PREDICATE,
                f"Unknown predicate: {predicate.value}",
            )
            return result

        # 1. Deprecated 체크
        if constraint.deprecated:
            result.add_warning(
                ValidationErrorCode.DEPRECATED_PREDICATE,
                constraint.deprecated_message or f"Predicate {predicate.value} is deprecated",
            )

        # 2. Subject 타입 검증
        if subject_type not in constraint.subject_types:
            result.add_error(
                ValidationErrorCode.INVALID_SUBJECT_TYPE,
                f"Subject type {subject_type.value} not allowed for {predicate.value}. "
                f"Allowed: {[t.value for t in constraint.subject_types]}",
                field="subject_type",
            )

        # 3. Object 타입 검증
        if object_type not in constraint.object_types:
            result.add_error(
                ValidationErrorCode.INVALID_OBJECT_TYPE,
                f"Object type {object_type.value} not allowed for {predicate.value}. "
                f"Allowed: {[t.value for t in constraint.object_types]}",
                field="object_type",
            )

        # 4. 신뢰도 검증
        if confidence < constraint.min_confidence:
            result.add_error(
                ValidationErrorCode.LOW_CONFIDENCE,
                f"Confidence {confidence} below minimum {constraint.min_confidence}",
                field="confidence",
            )

        # 5. observed인데 증거 없음 체크
        if assertion_type == AssertionType.OBSERVED:
            if not evidence_ids or len(evidence_ids) == 0:
                # SUPPORTED_BY, SOURCED_FROM은 자체가 증거 연결이므로 제외
                if predicate not in [PredicateType.SUPPORTED_BY, PredicateType.SOURCED_FROM]:
                    result.add_warning(
                        ValidationErrorCode.NO_EVIDENCE_FOR_OBSERVED,
                        "OBSERVED assertion should have at least one evidence",
                        field="evidence_ids",
                    )

        # 6. HAS_ROLE의 경우 role 속성 필수
        if predicate == PredicateType.HAS_ROLE:
            if not properties or "role" not in properties:
                result.add_error(
                    ValidationErrorCode.MISSING_REQUIRED_EVIDENCE,
                    "HAS_ROLE requires 'role' property (customer|competitor|partner)",
                    field="properties.role",
                )
            elif properties["role"] not in ["customer", "competitor", "partner"]:
                result.add_warning(
                    ValidationErrorCode.INVALID_OBJECT_TYPE,
                    f"Unknown role: {properties['role']}. Expected: customer|competitor|partner",
                    field="properties.role",
                )

        # 검증 결과에 따라 상태 제안
        if result.is_valid:
            # 경고만 있으면 verified, 에러 있으면 proposed
            if len(result.warnings) == 0 and confidence >= 0.7:
                result.suggested_status = TripleStatus.VERIFIED
            else:
                result.suggested_status = TripleStatus.PROPOSED
        else:
            result.suggested_status = TripleStatus.REJECTED

        return result

    def get_allowed_predicates(
        self,
        subject_type: EntityType,
        object_type: EntityType,
    ) -> list[PredicateType]:
        """
        주어진 subject/object 타입에 허용되는 predicate 목록 반환
        """
        allowed = []
        for predicate, constraint in self.constraints.items():
            if constraint.deprecated:
                continue
            if subject_type in constraint.subject_types and object_type in constraint.object_types:
                allowed.append(predicate)
        return allowed

    def get_path_safe_predicates(self) -> list[PredicateType]:
        """
        경로 탐색에서 안전하게 사용할 수 있는 predicate 목록
        (INFERRED_FROM, LEADS_TO 등 제외)
        """
        return [
            predicate
            for predicate, constraint in self.constraints.items()
            if not constraint.exclude_from_path and not constraint.deprecated
        ]
