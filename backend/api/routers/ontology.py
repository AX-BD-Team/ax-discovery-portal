"""
Ontology API Router

온톨로지 Entity/Triple CRUD 및 그래프 탐색 API
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.database.models.entity import EntityType
from backend.database.models.triple import PredicateType
from backend.database.repositories.ontology import ontology_repo
from backend.services.ontology_service import ontology_service

router = APIRouter(prefix="/ontology", tags=["Ontology"])


# ==================== Pydantic Schemas ====================


class EntityCreate(BaseModel):
    """엔티티 생성 요청"""

    entity_type: str = Field(..., description="엔티티 유형")
    name: str = Field(..., max_length=500, description="엔티티 이름")
    description: str | None = Field(None, description="설명")
    properties: dict = Field(default_factory=dict, description="추가 메타데이터")
    external_ref_id: str | None = Field(None, description="외부 참조 ID")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="신뢰도")


class EntityResponse(BaseModel):
    """엔티티 응답"""

    entity_id: str
    entity_type: str
    name: str
    description: str | None
    confidence: float
    properties: dict
    external_ref_id: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)


class EntityListResponse(BaseModel):
    """엔티티 목록 응답"""

    items: list[EntityResponse]
    total: int
    page: int
    page_size: int


class TripleCreate(BaseModel):
    """관계 생성 요청"""

    subject_id: str = Field(..., description="Subject 엔티티 ID")
    predicate: str = Field(..., description="관계 유형")
    object_id: str = Field(..., description="Object 엔티티 ID")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="관계 강도")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="신뢰도")
    evidence_ids: list[str] = Field(default_factory=list, description="근거 Evidence ID 목록")
    reasoning_path_id: str | None = Field(None, description="추론 경로 ID")
    properties: dict = Field(default_factory=dict, description="추가 메타데이터")


class TripleResponse(BaseModel):
    """관계 응답"""

    triple_id: str
    subject_id: str
    predicate: str
    object_id: str
    weight: float
    confidence: float
    evidence_ids: list[str]
    reasoning_path_id: str | None
    properties: dict
    created_at: datetime
    created_by: str | None
    subject: EntityResponse | None = None
    object: EntityResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class TripleListResponse(BaseModel):
    """관계 목록 응답"""

    items: list[TripleResponse]
    total: int


class GraphNode(BaseModel):
    """그래프 노드"""

    id: str
    type: str
    name: str
    confidence: float


class GraphEdge(BaseModel):
    """그래프 엣지"""

    source: str
    target: str
    predicate: str
    weight: float
    confidence: float


class GraphResponse(BaseModel):
    """그래프 응답"""

    center_node_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class PathResponse(BaseModel):
    """경로 응답"""

    source_id: str
    target_id: str
    path: list[TripleResponse]
    hops: int


class SimilarEntityResponse(BaseModel):
    """유사 엔티티 응답"""

    entity: EntityResponse
    similarity: float


class StatsResponse(BaseModel):
    """통계 응답"""

    entity_count: int
    entity_by_type: dict[str, int]
    triple_count: int
    triple_by_predicate: dict[str, int]
    avg_confidence: float


# ==================== Entity Endpoints ====================


@router.post("/entities", response_model=EntityResponse)
async def create_entity(
    entity: EntityCreate,
    auto_index: bool = Query(True, description="자동 벡터 인덱싱 여부"),
    db: AsyncSession = Depends(get_db),
):
    """
    엔티티 생성

    Entity를 생성하고 자동으로 벡터 인덱스에 추가합니다.
    auto_index=false로 설정하면 인덱싱을 건너뜁니다.
    """
    try:
        entity_type = EntityType(entity.entity_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type: {entity.entity_type}. "
            f"Valid types: {[e.value for e in EntityType]}",
        ) from None

    # OntologyService를 사용하여 생성 + 자동 인덱싱
    db_entity = await ontology_service.create_entity(
        db,
        entity_type=entity_type,
        name=entity.name,
        description=entity.description,
        properties=entity.properties,
        external_ref_id=entity.external_ref_id,
        confidence=entity.confidence,
        auto_index=auto_index,
    )
    await db.commit()

    return EntityResponse(
        entity_id=db_entity.entity_id,
        entity_type=db_entity.entity_type.value,
        name=db_entity.name,
        description=db_entity.description,
        confidence=db_entity.confidence,
        properties=db_entity.properties or {},
        external_ref_id=db_entity.external_ref_id,
        created_at=db_entity.created_at,
        updated_at=db_entity.updated_at,
        created_by=db_entity.created_by,
    )


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """엔티티 조회"""
    entity = await ontology_repo.get_entity(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return EntityResponse(
        entity_id=entity.entity_id,
        entity_type=entity.entity_type.value,
        name=entity.name,
        description=entity.description,
        confidence=entity.confidence,
        properties=entity.properties or {},
        external_ref_id=entity.external_ref_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=entity.created_by,
    )


@router.get("/entities", response_model=EntityListResponse)
async def list_entities(
    entity_type: str | None = Query(None, description="엔티티 유형 필터"),
    search: str | None = Query(None, description="이름/설명 검색"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db),
):
    """엔티티 목록 조회"""
    # entity_type 변환
    type_filter = None
    if entity_type:
        try:
            type_filter = EntityType(entity_type)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid entity_type: {entity_type}"
            ) from None

    skip = (page - 1) * page_size
    entities, total = await ontology_repo.list_entities(
        db,
        entity_type=type_filter,
        search=search,
        skip=skip,
        limit=page_size,
    )

    return EntityListResponse(
        items=[
            EntityResponse(
                entity_id=e.entity_id,
                entity_type=e.entity_type.value,
                name=e.name,
                description=e.description,
                confidence=e.confidence,
                properties=e.properties or {},
                external_ref_id=e.external_ref_id,
                created_at=e.created_at,
                updated_at=e.updated_at,
                created_by=e.created_by,
            )
            for e in entities
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/entities/{entity_id}")
async def delete_entity(
    entity_id: str,
    remove_from_index: bool = Query(True, description="벡터 인덱스에서도 제거 여부"),
    db: AsyncSession = Depends(get_db),
):
    """
    엔티티 삭제

    Entity를 삭제하고 벡터 인덱스에서도 제거합니다.
    remove_from_index=false로 설정하면 인덱스 제거를 건너뜁니다.
    """
    # OntologyService를 사용하여 삭제 + 인덱스 제거
    deleted = await ontology_service.delete_entity(
        db, entity_id, remove_from_index=remove_from_index
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Entity not found")

    await db.commit()
    return {"message": "Entity deleted", "entity_id": entity_id}


# ==================== Triple Endpoints ====================


@router.post("/triples", response_model=TripleResponse)
async def create_triple(
    triple: TripleCreate,
    db: AsyncSession = Depends(get_db),
):
    """관계(Triple) 생성"""
    try:
        predicate = PredicateType(triple.predicate)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid predicate: {triple.predicate}. "
            f"Valid predicates: {[p.value for p in PredicateType]}",
        ) from None

    # Subject/Object 존재 확인
    subject = await ontology_repo.get_entity(db, triple.subject_id)
    if not subject:
        raise HTTPException(
            status_code=404, detail=f"Subject entity not found: {triple.subject_id}"
        )

    obj = await ontology_repo.get_entity(db, triple.object_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Object entity not found: {triple.object_id}")

    # OntologyService를 사용하여 Triple 생성
    db_triple = await ontology_service.create_triple(
        db,
        subject_id=triple.subject_id,
        predicate=predicate,
        object_id=triple.object_id,
        weight=triple.weight,
        confidence=triple.confidence,
        evidence_ids=triple.evidence_ids,
        reasoning_path_id=triple.reasoning_path_id,
        properties=triple.properties,
    )
    await db.commit()

    return TripleResponse(
        triple_id=db_triple.triple_id,
        subject_id=db_triple.subject_id,
        predicate=db_triple.predicate.value,
        object_id=db_triple.object_id,
        weight=db_triple.weight,
        confidence=db_triple.confidence,
        evidence_ids=db_triple.evidence_ids or [],
        reasoning_path_id=db_triple.reasoning_path_id,
        properties=db_triple.properties or {},
        created_at=db_triple.created_at,
        created_by=db_triple.created_by,
    )


@router.get("/triples", response_model=TripleListResponse)
async def query_triples(
    subject_id: str | None = Query(None, description="Subject ID 필터"),
    predicate: str | None = Query(None, description="Predicate 필터"),
    object_id: str | None = Query(None, description="Object ID 필터"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="최소 신뢰도"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(100, ge=1, le=500, description="조회 개수"),
    db: AsyncSession = Depends(get_db),
):
    """관계 쿼리 (SPO 패턴)"""
    predicate_filter = None
    if predicate:
        try:
            predicate_filter = PredicateType(predicate)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid predicate: {predicate}") from None

    triples, total = await ontology_repo.query_triples(
        db,
        subject_id=subject_id,
        predicate=predicate_filter,
        object_id=object_id,
        min_confidence=min_confidence,
        skip=skip,
        limit=limit,
    )

    return TripleListResponse(
        items=[
            TripleResponse(
                triple_id=t.triple_id,
                subject_id=t.subject_id,
                predicate=t.predicate.value,
                object_id=t.object_id,
                weight=t.weight,
                confidence=t.confidence,
                evidence_ids=t.evidence_ids or [],
                reasoning_path_id=t.reasoning_path_id,
                properties=t.properties or {},
                created_at=t.created_at,
                created_by=t.created_by,
                subject=EntityResponse(
                    entity_id=t.subject.entity_id,
                    entity_type=t.subject.entity_type.value,
                    name=t.subject.name,
                    description=t.subject.description,
                    confidence=t.subject.confidence,
                    properties=t.subject.properties or {},
                    external_ref_id=t.subject.external_ref_id,
                    created_at=t.subject.created_at,
                    updated_at=t.subject.updated_at,
                    created_by=t.subject.created_by,
                )
                if t.subject
                else None,
                object=EntityResponse(
                    entity_id=t.object.entity_id,
                    entity_type=t.object.entity_type.value,
                    name=t.object.name,
                    description=t.object.description,
                    confidence=t.object.confidence,
                    properties=t.object.properties or {},
                    external_ref_id=t.object.external_ref_id,
                    created_at=t.object.created_at,
                    updated_at=t.object.updated_at,
                    created_by=t.object.created_by,
                )
                if t.object
                else None,
            )
            for t in triples
        ],
        total=total,
    )


@router.delete("/triples/{triple_id}")
async def delete_triple(
    triple_id: str,
    db: AsyncSession = Depends(get_db),
):
    """관계 삭제"""
    # OntologyService를 사용하여 Triple 삭제
    deleted = await ontology_service.delete_triple(db, triple_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Triple not found")

    await db.commit()
    return {"message": "Triple deleted", "triple_id": triple_id}


# ==================== Graph Query Endpoints ====================


@router.get("/graph/{entity_id}", response_model=GraphResponse)
async def get_entity_graph(
    entity_id: str,
    depth: int = Query(1, ge=1, le=5, description="탐색 깊이"),
    predicates: str | None = Query(None, description="관계 유형 필터 (쉼표 구분)"),
    db: AsyncSession = Depends(get_db),
):
    """엔티티 중심 그래프 조회"""
    # predicate 필터 파싱
    predicate_filter = None
    if predicates:
        predicate_filter = []
        for p in predicates.split(","):
            try:
                predicate_filter.append(PredicateType(p.strip()))
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid predicate: {p.strip()}"
                ) from None

    graph = await ontology_repo.get_entity_graph(
        db,
        entity_id=entity_id,
        depth=depth,
        predicates=predicate_filter,
    )

    if not graph["center"]:
        raise HTTPException(status_code=404, detail="Entity not found")

    return GraphResponse(
        center_node_id=entity_id,
        nodes=[
            GraphNode(
                id=n.entity_id,
                type=n.entity_type.value,
                name=n.name,
                confidence=n.confidence,
            )
            for n in graph["nodes"]
        ],
        edges=[
            GraphEdge(
                source=e.subject_id,
                target=e.object_id,
                predicate=e.predicate.value,
                weight=e.weight,
                confidence=e.confidence,
            )
            for e in graph["edges"]
        ],
    )


@router.get("/path/{source_id}/{target_id}", response_model=PathResponse)
async def find_path(
    source_id: str,
    target_id: str,
    max_depth: int = Query(5, ge=1, le=10, description="최대 탐색 깊이"),
    db: AsyncSession = Depends(get_db),
):
    """두 엔티티 간 경로 탐색"""
    # 엔티티 존재 확인
    source = await ontology_repo.get_entity(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source entity not found: {source_id}")

    target = await ontology_repo.get_entity(db, target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target entity not found: {target_id}")

    path = await ontology_repo.find_path(
        db,
        source_id=source_id,
        target_id=target_id,
        max_depth=max_depth,
    )

    return PathResponse(
        source_id=source_id,
        target_id=target_id,
        path=[
            TripleResponse(
                triple_id=t.triple_id,
                subject_id=t.subject_id,
                predicate=t.predicate.value,
                object_id=t.object_id,
                weight=t.weight,
                confidence=t.confidence,
                evidence_ids=t.evidence_ids or [],
                reasoning_path_id=t.reasoning_path_id,
                properties=t.properties or {},
                created_at=t.created_at,
                created_by=t.created_by,
            )
            for t in path
        ],
        hops=len(path),
    )


@router.get("/similar/{entity_id}", response_model=list[SimilarEntityResponse])
async def find_similar_entities(
    entity_id: str,
    limit: int = Query(10, ge=1, le=50, description="조회 개수"),
    db: AsyncSession = Depends(get_db),
):
    """유사 엔티티 검색"""
    entity = await ontology_repo.get_entity(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    similar = await ontology_repo.get_similar_entities(
        db,
        entity_id=entity_id,
        limit=limit,
    )

    return [
        SimilarEntityResponse(
            entity=EntityResponse(
                entity_id=e.entity_id,
                entity_type=e.entity_type.value,
                name=e.name,
                description=e.description,
                confidence=e.confidence,
                properties=e.properties or {},
                external_ref_id=e.external_ref_id,
                created_at=e.created_at,
                updated_at=e.updated_at,
                created_by=e.created_by,
            ),
            similarity=score,
        )
        for e, score in similar
    ]


# ==================== Statistics Endpoint ====================


@router.get("/stats", response_model=StatsResponse)
async def get_ontology_stats(
    db: AsyncSession = Depends(get_db),
):
    """온톨로지 통계"""
    stats = await ontology_repo.get_stats(db)
    return StatsResponse(**stats)
