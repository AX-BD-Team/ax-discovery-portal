"""
온톨로지 관리 모듈

Triple Lifecycle 관리, Predicate 제약 검증, 경로 탐색 등
"""

from .graph_query import GraphQuery, PathOptions, PathResult
from .validator import (
    PredicateConstraint,
    TripleValidator,
    ValidationError,
    ValidationResult,
)

__all__ = [
    # Validator
    "TripleValidator",
    "PredicateConstraint",
    "ValidationResult",
    "ValidationError",
    # Graph Query
    "GraphQuery",
    "PathOptions",
    "PathResult",
]
