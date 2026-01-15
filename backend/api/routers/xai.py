"""
XAI (Explainable AI) API Router

설명가능한 AI를 위한 API - Evidence Chain, Reasoning Path, Confidence 분석
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.database.models.triple import PredicateType
from backend.database.repositories.ontology import ontology_repo

router = APIRouter(prefix="/xai", tags=["XAI"])


# ==================== Pydantic Schemas ====================


class EvidenceItem(BaseModel):
    """증거 항목"""

    evidence_id: str
    evidence_type: str
    title: str
    source: str | None
    credibility: float
    summary: str | None


class ReasoningStepResponse(BaseModel):
    """추론 단계"""

    step_number: int
    premise: str
    inference: str
    conclusion: str
    evidence_ids: list[str]
    confidence: float
    reasoning_type: str


class ReasoningPathResponse(BaseModel):
    """추론 경로"""

    path_id: str | None
    final_conclusion: str
    steps: list[ReasoningStepResponse]
    total_confidence: float


class DimensionExplanation(BaseModel):
    """차원별 설명"""

    dimension: str
    score: float
    max_score: float
    evidence: list[EvidenceItem]
    reasoning: str


class ScorecardExplanationResponse(BaseModel):
    """Scorecard 평가 설명"""

    scorecard_id: str
    signal_id: str
    total_score: float
    decision: str
    dimension_explanations: list[DimensionExplanation]
    reasoning_path: ReasoningPathResponse | None
    overall_confidence: float


class TraceItem(BaseModel):
    """추적 항목"""

    hop: int
    entity_id: str
    entity_type: str
    entity_name: str
    relation: str
    confidence: float


class TraceResponse(BaseModel):
    """Signal 추적 응답"""

    signal_id: str
    traces: list[TraceItem]
    total_hops: int


class ConfidenceFactor(BaseModel):
    """신뢰도 요인"""

    factor_name: str
    factor_type: str  # positive, negative, neutral
    impact: float
    description: str


class ConfidenceResponse(BaseModel):
    """신뢰도 분석 응답"""

    entity_id: str
    overall_confidence: float
    factors: list[ConfidenceFactor]
    recommendations: list[str]


class EvidenceChainResponse(BaseModel):
    """Evidence Chain 응답"""

    target_id: str
    target_type: str
    evidence_chain: list[EvidenceItem]
    total_credibility: float


# ==================== XAI Endpoints ====================


@router.get("/explain/scorecard/{scorecard_id}", response_model=ScorecardExplanationResponse)
async def explain_scorecard(
    scorecard_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Scorecard 평가 근거 설명

    각 차원별 점수의 근거와 추론 경로를 제공
    """
    # Scorecard 엔티티 조회 (외부 참조로)
    scorecard_entity = await ontology_repo.get_entity_by_external_ref(db, scorecard_id)

    if not scorecard_entity:
        # 엔티티가 없으면 기본 응답 반환
        return ScorecardExplanationResponse(
            scorecard_id=scorecard_id,
            signal_id="",
            total_score=0,
            decision="UNKNOWN",
            dimension_explanations=[],
            reasoning_path=None,
            overall_confidence=0.0,
        )

    # Signal과의 관계 조회
    signal_triples, _ = await ontology_repo.query_triples(
        db,
        object_id=scorecard_entity.entity_id,
        predicate=PredicateType.HAS_SCORECARD,
        limit=1,
    )

    signal_id = signal_triples[0].subject_id if signal_triples else ""

    # Evidence 관계 조회
    evidence_triples, _ = await ontology_repo.query_triples(
        db,
        subject_id=scorecard_entity.entity_id,
        predicate=PredicateType.SUPPORTED_BY,
        limit=100,
    )

    # Evidence 엔티티 수집
    evidence_items = []
    for triple in evidence_triples:
        evidence_entity = await ontology_repo.get_entity(db, triple.object_id)
        if evidence_entity:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=evidence_entity.entity_id,
                    evidence_type=evidence_entity.properties.get("type", "UNKNOWN")
                    if evidence_entity.properties
                    else "UNKNOWN",
                    title=evidence_entity.name,
                    source=evidence_entity.properties.get("source")
                    if evidence_entity.properties
                    else None,
                    credibility=evidence_entity.confidence,
                    summary=evidence_entity.description,
                )
            )

    # 추론 경로 조회
    reasoning_path = await ontology_repo.get_reasoning_path(
        db,
        scorecard_entity.entity_id,
    )

    reasoning_response = None
    if reasoning_path:
        steps = []
        for i, triple in enumerate(reasoning_path):
            step_entity = await ontology_repo.get_entity(db, triple.subject_id)
            if step_entity:
                steps.append(
                    ReasoningStepResponse(
                        step_number=i + 1,
                        premise=step_entity.properties.get("premise", "")
                        if step_entity.properties
                        else "",
                        inference=step_entity.properties.get("inference", "")
                        if step_entity.properties
                        else "",
                        conclusion=step_entity.properties.get("conclusion", "")
                        if step_entity.properties
                        else "",
                        evidence_ids=triple.evidence_ids or [],
                        confidence=triple.confidence,
                        reasoning_type=step_entity.properties.get("type", "DEDUCTIVE")
                        if step_entity.properties
                        else "DEDUCTIVE",
                    )
                )

        reasoning_response = ReasoningPathResponse(
            path_id=reasoning_path[0].reasoning_path_id if reasoning_path else None,
            final_conclusion=scorecard_entity.description or "",
            steps=steps,
            total_confidence=sum(t.confidence for t in reasoning_path) / len(reasoning_path)
            if reasoning_path
            else 0,
        )

    # 차원별 설명 (메타데이터에서 추출)
    dimension_explanations = []
    dimensions = [
        "problem_severity",
        "willingness_to_pay",
        "data_availability",
        "feasibility",
        "strategic_fit",
    ]

    for dim in dimensions:
        dim_score = (
            scorecard_entity.properties.get(f"{dim}_score", 0) if scorecard_entity.properties else 0
        )
        dim_reasoning = (
            scorecard_entity.properties.get(f"{dim}_reasoning", "")
            if scorecard_entity.properties
            else ""
        )

        dimension_explanations.append(
            DimensionExplanation(
                dimension=dim,
                score=dim_score,
                max_score=20,
                evidence=[e for e in evidence_items if dim in (e.evidence_type or "").lower()],
                reasoning=dim_reasoning,
            )
        )

    return ScorecardExplanationResponse(
        scorecard_id=scorecard_id,
        signal_id=signal_id,
        total_score=scorecard_entity.properties.get("total_score", 0)
        if scorecard_entity.properties
        else 0,
        decision=scorecard_entity.properties.get("decision", "UNKNOWN")
        if scorecard_entity.properties
        else "UNKNOWN",
        dimension_explanations=dimension_explanations,
        reasoning_path=reasoning_response,
        overall_confidence=scorecard_entity.confidence,
    )


@router.get("/trace/signal/{signal_id}", response_model=TraceResponse)
async def trace_signal_origin(
    signal_id: str,
    max_depth: int = Query(5, ge=1, le=10, description="최대 추적 깊이"),
    db: AsyncSession = Depends(get_db),
):
    """
    Signal 출처 추적

    Signal에서 시작하여 Evidence → Source 순으로 역추적
    """
    # Signal 엔티티 조회
    signal_entity = await ontology_repo.get_entity_by_external_ref(db, signal_id)

    if not signal_entity:
        signal_entity = await ontology_repo.get_entity(db, signal_id)

    if not signal_entity:
        raise HTTPException(status_code=404, detail=f"Signal not found: {signal_id}")

    traces: list[TraceItem] = []
    visited: set[str] = set()
    current_entities = [(signal_entity, 0)]

    while current_entities:
        entity, hop = current_entities.pop(0)

        if hop >= max_depth or entity.entity_id in visited:
            continue

        visited.add(entity.entity_id)

        # SUPPORTED_BY 또는 SOURCED_FROM 관계 추적
        for predicate in [PredicateType.SUPPORTED_BY, PredicateType.SOURCED_FROM]:
            triples, _ = await ontology_repo.query_triples(
                db,
                subject_id=entity.entity_id,
                predicate=predicate,
                limit=20,
            )

            for triple in triples:
                target_entity = await ontology_repo.get_entity(db, triple.object_id)
                if target_entity and target_entity.entity_id not in visited:
                    traces.append(
                        TraceItem(
                            hop=hop + 1,
                            entity_id=target_entity.entity_id,
                            entity_type=target_entity.entity_type.value,
                            entity_name=target_entity.name,
                            relation=predicate.value,
                            confidence=triple.confidence,
                        )
                    )
                    current_entities.append((target_entity, hop + 1))

    return TraceResponse(
        signal_id=signal_id,
        traces=traces,
        total_hops=max(t.hop for t in traces) if traces else 0,
    )


@router.get("/confidence/{entity_id}", response_model=ConfidenceResponse)
async def calculate_confidence(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    신뢰도 계산 및 분석

    엔티티의 신뢰도에 영향을 미치는 요인 분석
    """
    entity = await ontology_repo.get_entity(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    factors: list[ConfidenceFactor] = []
    recommendations: list[str] = []

    # 증거 기반 신뢰도
    evidence_triples, _ = await ontology_repo.query_triples(
        db,
        subject_id=entity_id,
        predicate=PredicateType.SUPPORTED_BY,
        limit=100,
    )

    evidence_count = len(evidence_triples)
    if evidence_count > 0:
        avg_evidence_confidence = sum(t.confidence for t in evidence_triples) / evidence_count
        factors.append(
            ConfidenceFactor(
                factor_name="Evidence Support",
                factor_type="positive" if avg_evidence_confidence > 0.7 else "neutral",
                impact=avg_evidence_confidence * 0.4,
                description=f"{evidence_count}개의 증거 자료 (평균 신뢰도: {avg_evidence_confidence:.2f})",
            )
        )
    else:
        factors.append(
            ConfidenceFactor(
                factor_name="Evidence Support",
                factor_type="negative",
                impact=-0.2,
                description="증거 자료 없음",
            )
        )
        recommendations.append("증거 자료(Evidence)를 추가하여 신뢰도를 높이세요")

    # 관계 기반 신뢰도
    all_triples, _ = await ontology_repo.query_triples(
        db,
        subject_id=entity_id,
        limit=100,
    )
    incoming_triples, _ = await ontology_repo.query_triples(
        db,
        object_id=entity_id,
        limit=100,
    )

    total_relations = len(all_triples) + len(incoming_triples)
    if total_relations > 0:
        avg_relation_confidence = (
            sum(t.confidence for t in all_triples) + sum(t.confidence for t in incoming_triples)
        ) / total_relations

        factors.append(
            ConfidenceFactor(
                factor_name="Relationship Network",
                factor_type="positive" if total_relations > 3 else "neutral",
                impact=min(total_relations * 0.05, 0.3),
                description=f"{total_relations}개의 관계 연결 (평균 신뢰도: {avg_relation_confidence:.2f})",
            )
        )
    else:
        factors.append(
            ConfidenceFactor(
                factor_name="Relationship Network",
                factor_type="negative",
                impact=-0.1,
                description="관계 연결 없음 (고립된 엔티티)",
            )
        )
        recommendations.append("다른 엔티티와의 관계를 추가하여 컨텍스트를 강화하세요")

    # 메타데이터 완성도
    properties_fields = entity.properties or {}
    if len(properties_fields) > 5:
        factors.append(
            ConfidenceFactor(
                factor_name="Metadata Completeness",
                factor_type="positive",
                impact=0.1,
                description=f"{len(properties_fields)}개의 메타데이터 필드",
            )
        )
    elif len(properties_fields) > 0:
        factors.append(
            ConfidenceFactor(
                factor_name="Metadata Completeness",
                factor_type="neutral",
                impact=0.05,
                description=f"{len(properties_fields)}개의 메타데이터 필드 (보통)",
            )
        )
    else:
        factors.append(
            ConfidenceFactor(
                factor_name="Metadata Completeness",
                factor_type="negative",
                impact=-0.05,
                description="메타데이터 없음",
            )
        )
        recommendations.append("메타데이터를 추가하여 엔티티 정보를 풍부하게 하세요")

    # 전체 신뢰도 계산
    base_confidence = entity.confidence
    total_impact = sum(f.impact for f in factors)
    overall_confidence = max(0.0, min(1.0, base_confidence + total_impact))

    return ConfidenceResponse(
        entity_id=entity_id,
        overall_confidence=round(overall_confidence, 3),
        factors=factors,
        recommendations=recommendations,
    )


@router.get("/evidence-chain/{entity_id}", response_model=EvidenceChainResponse)
async def get_evidence_chain(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    엔티티의 Evidence Chain 조회

    엔티티를 뒷받침하는 모든 증거 자료 수집
    """
    entity = await ontology_repo.get_entity(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # SUPPORTED_BY 관계로 연결된 Evidence 조회
    evidence_triples, _ = await ontology_repo.query_triples(
        db,
        subject_id=entity_id,
        predicate=PredicateType.SUPPORTED_BY,
        limit=100,
    )

    evidence_chain: list[EvidenceItem] = []
    total_credibility = 0.0

    for triple in evidence_triples:
        evidence_entity = await ontology_repo.get_entity(db, triple.object_id)
        if evidence_entity:
            evidence_chain.append(
                EvidenceItem(
                    evidence_id=evidence_entity.entity_id,
                    evidence_type=evidence_entity.properties.get("type", "UNKNOWN")
                    if evidence_entity.properties
                    else "UNKNOWN",
                    title=evidence_entity.name,
                    source=evidence_entity.properties.get("source")
                    if evidence_entity.properties
                    else None,
                    credibility=evidence_entity.confidence,
                    summary=evidence_entity.description,
                )
            )
            total_credibility += evidence_entity.confidence

    # 평균 신뢰도 계산
    avg_credibility = total_credibility / len(evidence_chain) if evidence_chain else 0.0

    return EvidenceChainResponse(
        target_id=entity_id,
        target_type=entity.entity_type.value,
        evidence_chain=evidence_chain,
        total_credibility=round(avg_credibility, 3),
    )


@router.get("/reasoning-path/{entity_id}", response_model=ReasoningPathResponse)
async def get_reasoning_path(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    추론 경로 조회

    결론에 도달하기까지의 추론 단계를 역추적
    """
    entity = await ontology_repo.get_entity(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # 추론 경로 역추적
    path_triples = await ontology_repo.get_reasoning_path(db, entity_id)

    steps = []
    total_confidence = 0.0

    for i, triple in enumerate(path_triples):
        step_entity = await ontology_repo.get_entity(db, triple.subject_id)
        if step_entity:
            steps.append(
                ReasoningStepResponse(
                    step_number=i + 1,
                    premise=step_entity.properties.get("premise", "")
                    if step_entity.properties
                    else "",
                    inference=step_entity.properties.get("inference", "")
                    if step_entity.properties
                    else "",
                    conclusion=step_entity.properties.get("conclusion", "")
                    if step_entity.properties
                    else "",
                    evidence_ids=triple.evidence_ids or [],
                    confidence=triple.confidence,
                    reasoning_type=step_entity.properties.get("type", "DEDUCTIVE")
                    if step_entity.properties
                    else "DEDUCTIVE",
                )
            )
            total_confidence += triple.confidence

    avg_confidence = total_confidence / len(steps) if steps else 0.0

    return ReasoningPathResponse(
        path_id=path_triples[0].reasoning_path_id if path_triples else None,
        final_conclusion=entity.description or entity.name,
        steps=steps,
        total_confidence=round(avg_confidence, 3),
    )
