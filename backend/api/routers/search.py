"""
Search Router

Vector RAG 기반 의미 검색 API
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.database.models.entity import EntityType
from backend.services.rag_service import rag_service

router = APIRouter()


# ==================== Request/Response Models ====================


class SemanticSearchRequest(BaseModel):
    """의미 검색 요청"""

    query: str = Field(..., min_length=1, max_length=2000, description="검색 쿼리")
    entity_types: list[str] | None = Field(
        default=None,
        description="검색할 Entity 타입 (Signal, Topic, Customer 등)",
    )
    top_k: int = Field(default=10, ge=1, le=50, description="반환할 최대 결과 수")
    min_score: float = Field(default=0.7, ge=0.0, le=1.0, description="최소 유사도 점수")


class SearchResultItem(BaseModel):
    """검색 결과 항목"""

    entity_id: str
    score: float
    entity_type: str | None = None
    name: str | None = None
    confidence: float | None = None
    external_ref_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SemanticSearchResponse(BaseModel):
    """의미 검색 응답"""

    query: str
    items: list[SearchResultItem]
    total: int


class DuplicateCheckRequest(BaseModel):
    """중복 검사 요청"""

    title: str = Field(..., min_length=1, max_length=500)
    pain: str = Field(..., min_length=1, max_length=2000)
    proposed_value: str | None = Field(default=None, max_length=2000)
    customer_segment: str | None = Field(default=None, max_length=200)
    threshold: float = Field(default=0.85, ge=0.5, le=1.0, description="중복 판정 임계값")
    exclude_signal_id: str | None = Field(default=None, description="제외할 Signal ID (자기 자신)")


class DuplicateCheckResponse(BaseModel):
    """중복 검사 응답"""

    is_duplicate: bool
    highest_score: float
    threshold: float
    similar_signals: list[SearchResultItem]


class ContextGenerateRequest(BaseModel):
    """Context 생성 요청"""

    query: str = Field(..., min_length=1, max_length=2000)
    entity_types: list[str] | None = None
    max_tokens: int = Field(default=4000, ge=500, le=8000)


class ContextGenerateResponse(BaseModel):
    """Context 생성 응답"""

    context: str
    query: str
    estimated_tokens: int


class HealthCheckResponse(BaseModel):
    """헬스체크 응답"""

    embedding: bool
    vectorize: bool
    overall: bool


# ==================== API Endpoints ====================


@router.get("/health", response_model=HealthCheckResponse)
async def search_health_check():
    """
    검색 서비스 헬스체크

    임베딩 서비스와 Vectorize 연결 상태를 확인합니다.
    """
    status = await rag_service.health_check()
    return HealthCheckResponse(**status)


@router.get("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    query: Annotated[str, Query(min_length=1, max_length=2000, description="검색 쿼리")],
    entity_types: Annotated[
        list[str] | None,
        Query(description="Entity 타입 필터 (Signal, Topic, Customer 등)"),
    ] = None,
    top_k: Annotated[int, Query(ge=1, le=50, description="반환할 최대 결과 수")] = 10,
    min_score: Annotated[float, Query(ge=0.0, le=1.0, description="최소 유사도 점수")] = 0.7,
):
    """
    의미 기반 검색 (Vector RAG)

    쿼리 텍스트와 유사한 Entity를 벡터 유사도로 검색합니다.

    - **query**: 검색할 텍스트
    - **entity_types**: 검색 대상 Entity 타입 (복수 선택 가능)
    - **top_k**: 반환할 최대 결과 수 (기본: 10)
    - **min_score**: 최소 유사도 점수 (기본: 0.7)
    """
    if not rag_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="검색 서비스가 설정되지 않았습니다. OPENAI_API_KEY와 Vectorize 설정을 확인하세요.",
        )

    # Entity 타입 변환
    types = None
    if entity_types:
        try:
            types = [EntityType(t) for t in entity_types]
        except ValueError as e:
            valid_types = [t.value for t in EntityType]
            raise HTTPException(
                status_code=400,
                detail=f"유효하지 않은 Entity 타입: {e}. 유효한 타입: {valid_types}",
            ) from e

    try:
        results = await rag_service.search_similar(
            query=query,
            entity_types=types,
            top_k=top_k,
            min_score=min_score,
        )

        items = []
        for r in results:
            metadata = r.get("metadata", {}) or {}
            items.append(
                SearchResultItem(
                    entity_id=r["entity_id"],
                    score=r["score"],
                    entity_type=metadata.get("entity_type"),
                    name=metadata.get("name"),
                    confidence=metadata.get("confidence"),
                    external_ref_id=metadata.get("external_ref_id"),
                )
            )

        return SemanticSearchResponse(
            query=query,
            items=items,
            total=len(items),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}") from e


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search_post(request: SemanticSearchRequest):
    """
    의미 기반 검색 (POST)

    GET과 동일하지만 복잡한 쿼리나 긴 텍스트에 적합합니다.
    """
    return await semantic_search(
        query=request.query,
        entity_types=request.entity_types,
        top_k=request.top_k,
        min_score=request.min_score,
    )


@router.post("/duplicates", response_model=DuplicateCheckResponse)
async def check_duplicates(request: DuplicateCheckRequest):
    """
    Signal 중복 검사

    새 Signal 생성 전 기존 Signal과의 중복 여부를 검사합니다.

    - **title**: Signal 제목
    - **pain**: Pain point
    - **threshold**: 중복 판정 임계값 (기본: 0.85)
    """
    if not rag_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="검색 서비스가 설정되지 않았습니다.",
        )

    try:
        result = await rag_service.check_signal_duplicate(
            title=request.title,
            pain=request.pain,
            proposed_value=request.proposed_value,
            customer_segment=request.customer_segment,
            threshold=request.threshold,
            exclude_signal_id=request.exclude_signal_id,
        )

        similar_signals = []
        for s in result["similar_signals"]:
            metadata = s.get("metadata", {}) or {}
            similar_signals.append(
                SearchResultItem(
                    entity_id=s["entity_id"],
                    score=s["score"],
                    entity_type=metadata.get("entity_type"),
                    name=metadata.get("name"),
                    confidence=metadata.get("confidence"),
                    external_ref_id=metadata.get("external_ref_id"),
                )
            )

        return DuplicateCheckResponse(
            is_duplicate=result["is_duplicate"],
            highest_score=result["highest_score"],
            threshold=result["threshold"],
            similar_signals=similar_signals,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"중복 검사 실패: {str(e)}") from e


@router.post("/context", response_model=ContextGenerateResponse)
async def generate_context(request: ContextGenerateRequest):
    """
    RAG Context 생성

    쿼리와 관련된 Entity들을 검색하여 LLM 입력용 컨텍스트를 생성합니다.

    - **query**: 검색 쿼리
    - **entity_types**: 검색 대상 Entity 타입
    - **max_tokens**: 최대 토큰 수 (기본: 4000)
    """
    if not rag_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="검색 서비스가 설정되지 않았습니다.",
        )

    # Entity 타입 변환
    types = None
    if request.entity_types:
        try:
            types = [EntityType(t) for t in request.entity_types]
        except ValueError as e:
            valid_types = [t.value for t in EntityType]
            raise HTTPException(
                status_code=400,
                detail=f"유효하지 않은 Entity 타입: {e}. 유효한 타입: {valid_types}",
            ) from e

    try:
        context = await rag_service.generate_context(
            query=request.query,
            entity_types=types,
            max_tokens=request.max_tokens,
        )

        # 토큰 수 추정
        estimated_tokens = rag_service.embedding.estimate_tokens(context)

        return ContextGenerateResponse(
            context=context,
            query=request.query,
            estimated_tokens=estimated_tokens,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context 생성 실패: {str(e)}") from e


@router.get("/entity-types")
async def list_entity_types():
    """
    검색 가능한 Entity 타입 목록

    벡터 검색에서 필터로 사용할 수 있는 Entity 타입을 반환합니다.
    """
    return {"entity_types": [{"value": t.value, "name": t.name} for t in EntityType]}
