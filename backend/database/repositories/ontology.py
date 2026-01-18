"""
Ontology Repository

Entity와 Triple에 대한 CRUD 작업 및 그래프 탐색 기능
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database.models.entity import Entity, EntityType
from backend.database.models.triple import PredicateType, Triple


class OntologyRepository:
    """
    온톨로지 저장소

    Entity와 Triple에 대한 CRUD 및 그래프 쿼리 기능 제공
    """

    # ==================== Entity CRUD ====================

    async def create_entity(
        self,
        db: AsyncSession,
        entity_type: EntityType,
        name: str,
        description: str | None = None,
        properties: dict | None = None,
        external_ref_id: str | None = None,
        confidence: float = 1.0,
        created_by: str | None = None,
    ) -> Entity:
        """엔티티 생성"""
        entity_id = self._generate_entity_id(entity_type)

        entity = Entity(
            entity_id=entity_id,
            entity_type=entity_type,
            name=name,
            description=description,
            properties=properties or {},
            external_ref_id=external_ref_id,
            confidence=confidence,
            created_by=created_by,
        )

        db.add(entity)
        await db.flush()
        return entity

    async def get_entity(self, db: AsyncSession, entity_id: str) -> Entity | None:
        """엔티티 조회"""
        result = await db.execute(select(Entity).where(Entity.entity_id == entity_id))
        return result.scalar_one_or_none()

    async def get_entity_by_external_ref(
        self, db: AsyncSession, external_ref_id: str
    ) -> Entity | None:
        """외부 참조 ID로 엔티티 조회"""
        result = await db.execute(select(Entity).where(Entity.external_ref_id == external_ref_id))
        return result.scalar_one_or_none()

    async def list_entities(
        self,
        db: AsyncSession,
        entity_type: EntityType | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Entity], int]:
        """엔티티 목록 조회"""
        query = select(Entity)

        # 필터 적용
        conditions = []
        if entity_type:
            conditions.append(Entity.entity_type == entity_type)
        if search:
            conditions.append(
                or_(Entity.name.ilike(f"%{search}%"), Entity.description.ilike(f"%{search}%"))
            )

        if conditions:
            query = query.where(and_(*conditions))

        # 총 개수
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        # 페이지네이션
        query = query.order_by(Entity.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)

        return list(result.scalars().all()), total

    async def update_entity(self, db: AsyncSession, entity_id: str, **kwargs) -> Entity | None:
        """엔티티 업데이트"""
        entity = await self.get_entity(db, entity_id)
        if not entity:
            return None

        for key, value in kwargs.items():
            if hasattr(entity, key) and value is not None:
                setattr(entity, key, value)

        entity.updated_at = datetime.now(UTC)
        await db.flush()
        return entity

    async def delete_entity(self, db: AsyncSession, entity_id: str) -> bool:
        """엔티티 삭제 (관련 Triple도 CASCADE 삭제)"""
        entity = await self.get_entity(db, entity_id)
        if not entity:
            return False

        await db.delete(entity)
        await db.flush()
        return True

    # ==================== Triple CRUD ====================

    async def create_triple(
        self,
        db: AsyncSession,
        subject_id: str,
        predicate: PredicateType,
        object_id: str,
        weight: float = 1.0,
        confidence: float = 1.0,
        evidence_ids: list[str] | None = None,
        reasoning_path_id: str | None = None,
        properties: dict | None = None,
        created_by: str | None = None,
    ) -> Triple:
        """Triple 생성"""
        triple_id = self._generate_triple_id()

        triple = Triple(
            triple_id=triple_id,
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            weight=weight,
            confidence=confidence,
            evidence_ids=evidence_ids or [],
            reasoning_path_id=reasoning_path_id,
            properties=properties or {},
            created_by=created_by,
        )

        db.add(triple)
        await db.flush()
        return triple

    async def get_triple(self, db: AsyncSession, triple_id: str) -> Triple | None:
        """Triple 조회"""
        result = await db.execute(
            select(Triple)
            .options(selectinload(Triple.subject), selectinload(Triple.object))
            .where(Triple.triple_id == triple_id)
        )
        return result.scalar_one_or_none()

    async def query_triples(
        self,
        db: AsyncSession,
        subject_id: str | None = None,
        predicate: PredicateType | None = None,
        object_id: str | None = None,
        min_confidence: float = 0.0,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Triple], int]:
        """Triple 쿼리 (SPO 패턴)"""
        query = select(Triple).options(selectinload(Triple.subject), selectinload(Triple.object))

        conditions = [Triple.confidence >= min_confidence]

        if subject_id:
            conditions.append(Triple.subject_id == subject_id)
        if predicate:
            conditions.append(Triple.predicate == predicate)
        if object_id:
            conditions.append(Triple.object_id == object_id)

        query = query.where(and_(*conditions))

        # 총 개수
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        # 페이지네이션
        query = query.order_by(Triple.confidence.desc(), Triple.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def delete_triple(self, db: AsyncSession, triple_id: str) -> bool:
        """Triple 삭제"""
        triple = await self.get_triple(db, triple_id)
        if not triple:
            return False

        await db.delete(triple)
        await db.flush()
        return True

    # ==================== Graph Queries ====================

    async def get_entity_graph(
        self,
        db: AsyncSession,
        entity_id: str,
        depth: int = 1,
        predicates: list[PredicateType] | None = None,
    ) -> dict:
        """
        엔티티 중심 그래프 조회

        Returns:
            {
                "center": Entity,
                "nodes": [Entity, ...],
                "edges": [Triple, ...]
            }
        """
        # 중심 엔티티
        center = await self.get_entity(db, entity_id)
        if not center:
            return {"center": None, "nodes": [], "edges": []}

        visited_nodes: set[str] = {entity_id}
        all_edges: list[Triple] = []
        current_frontier: set[str] = {entity_id}

        for _ in range(depth):
            if not current_frontier:
                break

            next_frontier: set[str] = set()

            # 배치 쿼리로 현재 frontier의 모든 관계를 한 번에 조회 (N+1 문제 해결)
            frontier_list = list(current_frontier)

            # 나가는 관계 배치 조회
            outgoing_query = (
                select(Triple)
                .options(selectinload(Triple.subject), selectinload(Triple.object))
                .where(Triple.subject_id.in_(frontier_list))
            )
            if predicates:
                outgoing_query = outgoing_query.where(Triple.predicate.in_(predicates))
            outgoing_result = await db.execute(outgoing_query)
            outgoing_triples = list(outgoing_result.scalars().all())

            for triple in outgoing_triples:
                all_edges.append(triple)
                if triple.object_id not in visited_nodes:
                    next_frontier.add(triple.object_id)

            # 들어오는 관계 배치 조회
            incoming_query = (
                select(Triple)
                .options(selectinload(Triple.subject), selectinload(Triple.object))
                .where(Triple.object_id.in_(frontier_list))
            )
            if predicates:
                incoming_query = incoming_query.where(Triple.predicate.in_(predicates))
            incoming_result = await db.execute(incoming_query)
            incoming_triples = list(incoming_result.scalars().all())

            for triple in incoming_triples:
                all_edges.append(triple)
                if triple.subject_id not in visited_nodes:
                    next_frontier.add(triple.subject_id)

            visited_nodes.update(next_frontier)
            current_frontier = next_frontier

        # 노드 배치 조회 (N+1 문제 해결)
        node_ids_to_fetch = list(visited_nodes)
        if node_ids_to_fetch:
            nodes_result = await db.execute(
                select(Entity).where(Entity.entity_id.in_(node_ids_to_fetch))
            )
            nodes = list(nodes_result.scalars().all())
        else:
            nodes = []

        # 중복 엣지 제거
        unique_edges = {e.triple_id: e for e in all_edges}

        return {
            "center": center,
            "nodes": nodes,
            "edges": list(unique_edges.values()),
        }

    async def find_path(
        self,
        db: AsyncSession,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> list[Triple]:
        """두 엔티티 간 경로 탐색 (BFS)"""
        if source_id == target_id:
            return []

        # BFS로 최단 경로 탐색
        visited: set[str] = {source_id}
        queue: list[tuple[str, list[Triple]]] = [(source_id, [])]

        while queue:
            current_id, path = queue.pop(0)

            if len(path) >= max_depth:
                continue

            # 나가는 관계
            outgoing, _ = await self.query_triples(db, subject_id=current_id, limit=100)

            for triple in outgoing:
                if triple.object_id == target_id:
                    return path + [triple]

                if triple.object_id not in visited:
                    visited.add(triple.object_id)
                    queue.append((triple.object_id, path + [triple]))

        return []  # 경로 없음

    async def get_similar_entities(
        self,
        db: AsyncSession,
        entity_id: str,
        limit: int = 10,
    ) -> list[tuple[Entity, float]]:
        """유사 엔티티 검색 (similar_to 관계 기반)"""
        # 양방향 관계를 단일 쿼리로 조회 (N+1 문제 해결)
        query = (
            select(Triple)
            .options(selectinload(Triple.subject), selectinload(Triple.object))
            .where(
                Triple.predicate == PredicateType.SIMILAR_TO,
                or_(
                    Triple.subject_id == entity_id,
                    Triple.object_id == entity_id,
                ),
            )
            .order_by(Triple.weight.desc())
            .limit(limit * 2)  # 양방향이므로 2배로 가져옴
        )
        result = await db.execute(query)
        triples = list(result.scalars().all())

        # 중복 제거하며 결과 구성
        seen_entity_ids: set[str] = set()
        results: list[tuple[Entity, float]] = []

        for triple in triples:
            if triple.subject_id == entity_id:
                # 나가는 관계: object가 유사 엔티티
                if triple.object_id not in seen_entity_ids and triple.object:
                    seen_entity_ids.add(triple.object_id)
                    results.append((triple.object, triple.weight))
            else:
                # 들어오는 관계: subject가 유사 엔티티
                if triple.subject_id not in seen_entity_ids and triple.subject:
                    seen_entity_ids.add(triple.subject_id)
                    results.append((triple.subject, triple.weight))

        # 점수순 정렬 후 limit 적용
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def get_reasoning_path(
        self,
        db: AsyncSession,
        conclusion_entity_id: str,
        max_depth: int = 10,
    ) -> list[Triple]:
        """
        추론 경로 역추적

        ReasoningStep 엔티티에서 leads_to 관계를 따라 역추적
        """
        path: list[Triple] = []
        visited: set[str] = set()
        current_id = conclusion_entity_id

        for _ in range(max_depth):
            if current_id in visited:
                break
            visited.add(current_id)

            # leads_to 관계의 subject 찾기 (역추적)
            triples, _ = await self.query_triples(
                db, object_id=current_id, predicate=PredicateType.LEADS_TO, limit=1
            )

            if not triples:
                break

            path.insert(0, triples[0])
            current_id = triples[0].subject_id

        return path

    # ==================== Statistics ====================

    async def get_stats(self, db: AsyncSession) -> dict:
        """온톨로지 통계 (최적화: N개 쿼리 -> 3개 쿼리)"""
        # 엔티티 타입별 개수를 단일 GROUP BY 쿼리로 조회
        entity_stats_query = select(
            Entity.entity_type,
            func.count().label("count"),
        ).group_by(Entity.entity_type)
        entity_result = await db.execute(entity_stats_query)
        entity_rows = entity_result.all()

        entity_by_type = {entity_type.value: 0 for entity_type in EntityType}
        entity_count = 0
        for row in entity_rows:
            entity_by_type[row.entity_type.value] = row.count
            entity_count += row.count

        # Triple 통계를 단일 쿼리로 조회 (predicate별 개수 + 평균 신뢰도)
        triple_stats_query = select(
            Triple.predicate,
            func.count().label("count"),
        ).group_by(Triple.predicate)
        triple_result = await db.execute(triple_stats_query)
        triple_rows = triple_result.all()

        triple_by_predicate = {predicate.value: 0 for predicate in PredicateType}
        triple_count = 0
        for row in triple_rows:
            triple_by_predicate[row.predicate.value] = row.count
            triple_count += row.count

        # 평균 신뢰도 (별도 쿼리, 집계 함수)
        avg_confidence = await db.scalar(select(func.avg(Triple.confidence)).select_from(Triple))

        return {
            "entity_count": entity_count,
            "entity_by_type": entity_by_type,
            "triple_count": triple_count,
            "triple_by_predicate": triple_by_predicate,
            "avg_confidence": round(avg_confidence or 0, 3),
        }

    # ==================== Helper Methods ====================

    def _generate_entity_id(self, entity_type: EntityType) -> str:
        """엔티티 ID 생성"""
        # v2: 22종 EntityType ID Prefix 매핑
        prefix_map = {
            # Pipeline Entities (7종)
            EntityType.ACTIVITY: "ACT",
            EntityType.SIGNAL: "SIG",
            EntityType.TOPIC: "TOP",
            EntityType.SCORECARD: "SCR",
            EntityType.BRIEF: "BRF",
            EntityType.VALIDATION: "VAL",
            EntityType.PILOT: "PLT",
            # Organization Entities (3종)
            EntityType.ORGANIZATION: "ORG",
            EntityType.PERSON: "PER",
            EntityType.TEAM: "TEM",
            # Market Context (4종)
            EntityType.TECHNOLOGY: "TEC",
            EntityType.INDUSTRY: "IND",
            EntityType.MARKET_SEGMENT: "MKT",
            EntityType.TREND: "TRD",
            # Evidence & Reasoning (4종)
            EntityType.EVIDENCE: "EVD",
            EntityType.SOURCE: "SRC",
            EntityType.REASONING_STEP: "RST",
            EntityType.DECISION: "DEC",
            # Operational (4종)
            EntityType.PLAY: "PLY",
            EntityType.MEETING: "MTG",
            EntityType.TASK: "TSK",
            EntityType.MILESTONE: "MLS",
            # Deprecated (하위 호환)
            EntityType.CUSTOMER: "CUS",
            EntityType.COMPETITOR: "COM",
        }
        prefix = prefix_map.get(entity_type, "ENT")
        unique_part = str(uuid4())[:8].upper()
        return f"{prefix}-{unique_part}"

    def _generate_triple_id(self) -> str:
        """Triple ID 생성"""
        return f"TRP-{str(uuid4())[:12].upper()}"


# 싱글톤 인스턴스
ontology_repo = OntologyRepository()
