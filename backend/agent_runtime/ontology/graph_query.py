"""
그래프 쿼리 (P0)

BFS/path 탐색에 "기본 안전모드" 적용:
- 기본값은 status=verified 엣지만 사용
- assertion_type=inferred는 가중치 페널티(또는 기본 제외)
- 특정 predicate는 path 구성에서 제외 (예: INFERRED_FROM)

쿼리 옵션:
- as_of: 특정 시점 기준 (Recency 필터)
- min_freshness: 최소 Freshness 점수
- include_proposed: proposed 상태 포함 여부
- include_inferred: inferred 타입 포함 여부
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from backend.database.models.entity import EntityType
from backend.database.models.triple import (
    AssertionType,
    PredicateType,
    TripleStatus,
)

from .validator import TripleValidator

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class PathMode(Enum):
    """경로 탐색 모드"""

    SAFE = "safe"  # verified만, inferred 제외
    NORMAL = "normal"  # verified만, inferred 포함 (페널티)
    FULL = "full"  # proposed 포함


@dataclass
class PathOptions:
    """경로 탐색 옵션"""

    # 안전 모드 (기본: SAFE)
    mode: PathMode = PathMode.SAFE

    # 최대 홉 수
    max_hops: int = 5

    # 최대 결과 수
    max_results: int = 10

    # Recency 필터
    as_of: datetime | None = None
    min_freshness: float = 0.0

    # 상태 필터
    include_proposed: bool = False
    include_deprecated: bool = False

    # 타입 필터
    include_inferred: bool = False
    inferred_weight_penalty: float = 0.5  # inferred 엣지 가중치 감소

    # Predicate 필터
    allowed_predicates: list[PredicateType] | None = None
    excluded_predicates: list[PredicateType] | None = None

    # 신뢰도 필터
    min_confidence: float = 0.5

    def __post_init__(self):
        # 모드에 따른 기본값 설정
        if self.mode == PathMode.SAFE:
            self.include_proposed = False
            self.include_inferred = False
        elif self.mode == PathMode.NORMAL:
            self.include_proposed = False
            self.include_inferred = True
        elif self.mode == PathMode.FULL:
            self.include_proposed = True
            self.include_inferred = True


@dataclass
class PathStep:
    """경로의 한 단계"""

    entity_id: str
    entity_type: EntityType
    entity_name: str
    predicate: PredicateType | None = None  # 이전 노드에서 이 노드로 온 predicate
    triple_id: str | None = None
    confidence: float = 1.0
    is_inferred: bool = False


@dataclass
class PathResult:
    """경로 탐색 결과"""

    # 경로 (시작 -> 끝)
    path: list[PathStep] = field(default_factory=list)

    # 전체 경로 신뢰도 (각 엣지 신뢰도의 곱)
    total_confidence: float = 1.0

    # 경로 길이 (홉 수)
    hop_count: int = 0

    # 경로에 inferred 엣지 포함 여부
    contains_inferred: bool = False

    # 경로에 proposed 엣지 포함 여부
    contains_proposed: bool = False

    # 경로 설명 (XAI용)
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "path": [
                {
                    "entity_id": step.entity_id,
                    "entity_type": step.entity_type.value,
                    "entity_name": step.entity_name,
                    "predicate": step.predicate.value if step.predicate else None,
                    "triple_id": step.triple_id,
                    "confidence": step.confidence,
                    "is_inferred": step.is_inferred,
                }
                for step in self.path
            ],
            "total_confidence": self.total_confidence,
            "hop_count": self.hop_count,
            "contains_inferred": self.contains_inferred,
            "contains_proposed": self.contains_proposed,
            "explanation": self.explanation,
        }


class GraphQuery:
    """
    그래프 쿼리 실행기

    BFS 기반 경로 탐색 + 안전모드 필터링
    """

    def __init__(self):
        self.validator = TripleValidator()
        self._path_safe_predicates = self.validator.get_path_safe_predicates()

    def _build_status_filter(self, options: PathOptions) -> list[TripleStatus]:
        """상태 필터 빌드"""
        statuses = [TripleStatus.VERIFIED]
        if options.include_proposed:
            statuses.append(TripleStatus.PROPOSED)
        if options.include_deprecated:
            statuses.append(TripleStatus.DEPRECATED)
        return statuses

    def _build_predicate_filter(self, options: PathOptions) -> set[PredicateType]:
        """Predicate 필터 빌드"""
        if options.allowed_predicates:
            predicates = set(options.allowed_predicates)
        else:
            # 기본: 경로 안전 predicate만
            predicates = set(self._path_safe_predicates)

        if options.excluded_predicates:
            predicates -= set(options.excluded_predicates)

        return predicates

    def _calculate_edge_weight(
        self,
        confidence: float,
        assertion_type: AssertionType,
        options: PathOptions,
    ) -> float:
        """엣지 가중치 계산 (페널티 적용)"""
        weight = confidence

        # inferred 페널티
        if assertion_type == AssertionType.INFERRED:
            weight *= options.inferred_weight_penalty

        return weight

    async def find_path_bfs(
        self,
        session: "AsyncSession",
        source_id: str,
        target_id: str,
        options: PathOptions | None = None,
    ) -> list[PathResult]:
        """
        BFS 경로 탐색 (P0: 안전모드 적용)

        Args:
            session: DB 세션
            source_id: 시작 엔티티 ID
            target_id: 목표 엔티티 ID
            options: 탐색 옵션

        Returns:
            찾은 경로 목록 (신뢰도 순 정렬)
        """
        from sqlalchemy import and_, select

        from backend.database.models.entity import Entity
        from backend.database.models.triple import Triple

        if options is None:
            options = PathOptions(mode=PathMode.SAFE)

        # 필터 빌드
        allowed_statuses = self._build_status_filter(options)
        allowed_predicates = self._build_predicate_filter(options)

        # BFS 초기화
        queue: deque[tuple[str, list[PathStep], float]] = deque()
        visited: set[str] = set()
        results: list[PathResult] = []

        # 시작 노드 정보 조회
        start_entity = await session.get(Entity, source_id)
        if not start_entity:
            return []

        start_step = PathStep(
            entity_id=source_id,
            entity_type=start_entity.entity_type,
            entity_name=start_entity.name,
        )
        queue.append((source_id, [start_step], 1.0))
        visited.add(source_id)

        while queue and len(results) < options.max_results:
            current_id, path, path_confidence = queue.popleft()

            # 홉 수 제한
            if len(path) > options.max_hops + 1:
                continue

            # 목표 도달
            if current_id == target_id:
                result = PathResult(
                    path=path,
                    total_confidence=path_confidence,
                    hop_count=len(path) - 1,
                    contains_inferred=any(step.is_inferred for step in path),
                    explanation=self._generate_path_explanation(path),
                )
                results.append(result)
                continue

            # 인접 엣지 조회 (outgoing)
            stmt = (
                select(Triple, Entity)
                .join(Entity, Triple.object_id == Entity.entity_id)
                .where(
                    and_(
                        Triple.subject_id == current_id,
                        Triple.status.in_(allowed_statuses),
                        Triple.predicate.in_(allowed_predicates),
                        Triple.confidence >= options.min_confidence,
                    )
                )
            )

            # inferred 필터
            if not options.include_inferred:
                stmt = stmt.where(Triple.assertion_type == AssertionType.OBSERVED)

            edge_result = await session.execute(stmt)
            edges = edge_result.all()

            for triple, next_entity in edges:
                if next_entity.entity_id in visited:
                    continue

                # 엣지 가중치 계산
                edge_weight = self._calculate_edge_weight(
                    triple.confidence,
                    triple.assertion_type,
                    options,
                )

                new_confidence = path_confidence * edge_weight

                # 너무 낮은 신뢰도는 스킵
                if new_confidence < 0.1:
                    continue

                new_step = PathStep(
                    entity_id=next_entity.entity_id,
                    entity_type=next_entity.entity_type,
                    entity_name=next_entity.name,
                    predicate=triple.predicate,
                    triple_id=triple.triple_id,
                    confidence=triple.confidence,
                    is_inferred=triple.assertion_type == AssertionType.INFERRED,
                )

                new_path = path + [new_step]
                visited.add(next_entity.entity_id)
                queue.append((next_entity.entity_id, new_path, new_confidence))

        # 신뢰도 순 정렬
        results.sort(key=lambda r: r.total_confidence, reverse=True)

        return results

    async def get_neighbors(
        self,
        session: "AsyncSession",
        entity_id: str,
        options: PathOptions | None = None,
        direction: str = "both",  # "outgoing", "incoming", "both"
    ) -> list[dict]:
        """
        인접 엔티티 조회

        Args:
            session: DB 세션
            entity_id: 엔티티 ID
            options: 쿼리 옵션
            direction: 방향 (outgoing, incoming, both)

        Returns:
            인접 엔티티 목록
        """
        from sqlalchemy import and_, select

        from backend.database.models.entity import Entity
        from backend.database.models.triple import Triple

        if options is None:
            options = PathOptions(mode=PathMode.SAFE)

        allowed_statuses = self._build_status_filter(options)
        allowed_predicates = self._build_predicate_filter(options)

        neighbors = []

        # Outgoing edges
        if direction in ("outgoing", "both"):
            stmt = (
                select(Triple, Entity)
                .join(Entity, Triple.object_id == Entity.entity_id)
                .where(
                    and_(
                        Triple.subject_id == entity_id,
                        Triple.status.in_(allowed_statuses),
                        Triple.predicate.in_(allowed_predicates),
                        Triple.confidence >= options.min_confidence,
                    )
                )
            )
            if not options.include_inferred:
                stmt = stmt.where(Triple.assertion_type == AssertionType.OBSERVED)

            result = await session.execute(stmt)
            for triple, entity in result.all():
                neighbors.append(
                    {
                        "direction": "outgoing",
                        "entity": entity.to_dict(),
                        "triple": triple.to_dict(),
                    }
                )

        # Incoming edges
        if direction in ("incoming", "both"):
            stmt = (
                select(Triple, Entity)
                .join(Entity, Triple.subject_id == Entity.entity_id)
                .where(
                    and_(
                        Triple.object_id == entity_id,
                        Triple.status.in_(allowed_statuses),
                        Triple.predicate.in_(allowed_predicates),
                        Triple.confidence >= options.min_confidence,
                    )
                )
            )
            if not options.include_inferred:
                stmt = stmt.where(Triple.assertion_type == AssertionType.OBSERVED)

            result = await session.execute(stmt)
            for triple, entity in result.all():
                neighbors.append(
                    {
                        "direction": "incoming",
                        "entity": entity.to_dict(),
                        "triple": triple.to_dict(),
                    }
                )

        return neighbors

    def _generate_path_explanation(self, path: list[PathStep]) -> str:
        """경로 설명 생성 (XAI용)"""
        if len(path) < 2:
            return ""

        parts = []
        for i, step in enumerate(path):
            if i == 0:
                parts.append(f"'{step.entity_name}'")
            else:
                predicate_name = step.predicate.value if step.predicate else "?"
                confidence_note = ""
                if step.is_inferred:
                    confidence_note = " (추론)"
                elif step.confidence < 0.7:
                    confidence_note = f" (신뢰도: {step.confidence:.0%})"

                parts.append(f"--[{predicate_name}]{confidence_note}--> '{step.entity_name}'")

        return " ".join(parts)


# 쿼리 헬퍼 함수들
async def find_evidence_chain(
    session: "AsyncSession",
    entity_id: str,
    max_depth: int = 3,
) -> list[dict]:
    """
    엔티티의 근거 체인 조회 (XAI용)

    Signal/Brief → Evidence → Source 경로 추적
    """
    from sqlalchemy import and_, select

    from backend.database.models.entity import Entity
    from backend.database.models.triple import PredicateType, Triple, TripleStatus

    chain = []
    current_ids = [entity_id]

    for depth in range(max_depth):
        if not current_ids:
            break

        # SUPPORTED_BY, SOURCED_FROM 관계 탐색
        stmt = (
            select(Triple, Entity)
            .join(Entity, Triple.object_id == Entity.entity_id)
            .where(
                and_(
                    Triple.subject_id.in_(current_ids),
                    Triple.predicate.in_(
                        [
                            PredicateType.SUPPORTED_BY,
                            PredicateType.SOURCED_FROM,
                        ]
                    ),
                    Triple.status == TripleStatus.VERIFIED,
                )
            )
        )

        result = await session.execute(stmt)
        next_ids = []

        for triple, entity in result.all():
            chain.append(
                {
                    "depth": depth,
                    "from_id": triple.subject_id,
                    "to_id": triple.object_id,
                    "predicate": triple.predicate.value,
                    "entity": entity.to_dict(),
                    "evidence_span": triple.evidence_span,
                }
            )
            next_ids.append(entity.entity_id)

        current_ids = next_ids

    return chain
