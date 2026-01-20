"""
Triple 검증기 템플릿

Predicate별 도메인/레인지/필수연결 제약을 코드로 강제
프로젝트 도메인에 맞게 PREDICATE_CONSTRAINTS를 정의하세요.
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

    INVALID_SUBJECT_TYPE = "INVALID_SUBJECT_TYPE"
    INVALID_OBJECT_TYPE = "INVALID_OBJECT_TYPE"
    MISSING_REQUIRED_EVIDENCE = "MISSING_REQUIRED_EVIDENCE"
    MISSING_REQUIRED_SOURCE = "MISSING_REQUIRED_SOURCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NO_EVIDENCE_FOR_OBSERVED = "NO_EVIDENCE_FOR_OBSERVED"
    SELF_REFERENCE = "SELF_REFERENCE"
    DUPLICATE_TRIPLE = "DUPLICATE_TRIPLE"
    CIRCULAR_REFERENCE = "CIRCULAR_REFERENCE"
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

    subject_types: set[EntityType]
    object_types: set[EntityType]
    requires_evidence: bool = False
    requires_source: bool = False
    min_confidence: float = 0.0
    deprecated: bool = False
    deprecated_message: str | None = None
    exclude_from_path: bool = False


# 프로젝트 도메인에 맞게 Predicate별 제약 정의
PREDICATE_CONSTRAINTS: dict[PredicateType, PredicateConstraint] = {
    # ===== Topic Relations =====
    PredicateType.SIMILAR_TO: PredicateConstraint(
        subject_types={EntityType.TECHNOLOGY},  # 프로젝트에 맞게 수정
        object_types={EntityType.TECHNOLOGY},
    ),
    PredicateType.PARENT_OF: PredicateConstraint(
        subject_types={EntityType.INDUSTRY},
        object_types={EntityType.INDUSTRY},
    ),
    PredicateType.ADDRESSES: PredicateConstraint(
        subject_types={EntityType.TECHNOLOGY},
        object_types={EntityType.INDUSTRY},
    ),
    # ===== Organization Relations =====
    PredicateType.TARGETS: PredicateConstraint(
        subject_types={EntityType.ORGANIZATION},
        object_types={EntityType.ORGANIZATION},
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
        object_types={EntityType.ORGANIZATION},
    ),
    # ===== Evidence Relations =====
    PredicateType.SUPPORTED_BY: PredicateConstraint(
        subject_types=set(EntityType),
        object_types={EntityType.EVIDENCE},
    ),
    PredicateType.SOURCED_FROM: PredicateConstraint(
        subject_types={EntityType.EVIDENCE},
        object_types={EntityType.SOURCE},
    ),
    PredicateType.INFERRED_FROM: PredicateConstraint(
        subject_types=set(EntityType),
        object_types={EntityType.REASONING_STEP},
        exclude_from_path=True,
    ),
    PredicateType.CONTRADICTS: PredicateConstraint(
        subject_types={EntityType.EVIDENCE},
        object_types={EntityType.EVIDENCE},
    ),
    # ===== Operational Relations =====
    PredicateType.SAME_AS: PredicateConstraint(
        subject_types=set(EntityType),
        object_types=set(EntityType),
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

        constraint = self.constraints.get(predicate)
        if not constraint:
            result.add_warning(
                ValidationErrorCode.DEPRECATED_PREDICATE,
                f"Unknown predicate: {predicate.value}",
            )
            return result

        # Deprecated 체크
        if constraint.deprecated:
            result.add_warning(
                ValidationErrorCode.DEPRECATED_PREDICATE,
                constraint.deprecated_message or f"Predicate {predicate.value} is deprecated",
            )

        # Subject 타입 검증
        if subject_type not in constraint.subject_types:
            result.add_error(
                ValidationErrorCode.INVALID_SUBJECT_TYPE,
                f"Subject type {subject_type.value} not allowed for {predicate.value}. "
                f"Allowed: {[t.value for t in constraint.subject_types]}",
                field="subject_type",
            )

        # Object 타입 검증
        if object_type not in constraint.object_types:
            result.add_error(
                ValidationErrorCode.INVALID_OBJECT_TYPE,
                f"Object type {object_type.value} not allowed for {predicate.value}. "
                f"Allowed: {[t.value for t in constraint.object_types]}",
                field="object_type",
            )

        # 신뢰도 검증
        if confidence < constraint.min_confidence:
            result.add_error(
                ValidationErrorCode.LOW_CONFIDENCE,
                f"Confidence {confidence} below minimum {constraint.min_confidence}",
                field="confidence",
            )

        # observed인데 증거 없음 체크
        if assertion_type == AssertionType.OBSERVED:
            if not evidence_ids or len(evidence_ids) == 0:
                if predicate not in [PredicateType.SUPPORTED_BY, PredicateType.SOURCED_FROM]:
                    result.add_warning(
                        ValidationErrorCode.NO_EVIDENCE_FOR_OBSERVED,
                        "OBSERVED assertion should have at least one evidence",
                        field="evidence_ids",
                    )

        # 검증 결과에 따라 상태 제안
        if result.is_valid:
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
        """주어진 subject/object 타입에 허용되는 predicate 목록 반환"""
        allowed = []
        for predicate, constraint in self.constraints.items():
            if constraint.deprecated:
                continue
            if subject_type in constraint.subject_types and object_type in constraint.object_types:
                allowed.append(predicate)
        return allowed

    def get_path_safe_predicates(self) -> list[PredicateType]:
        """경로 탐색에서 안전하게 사용할 수 있는 predicate 목록"""
        return [
            predicate
            for predicate, constraint in self.constraints.items()
            if not constraint.exclude_from_path and not constraint.deprecated
        ]
