"""
Scorecard Router

Scorecard 평가 API (D1 HTTP API 사용)
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from backend.integrations.cloudflare_d1.repositories import scorecard_d1_repo, signal_d1_repo

router = APIRouter()


class DimensionScore(BaseModel):
    """차원별 점수"""

    score: int
    weight: int


class Recommendation(BaseModel):
    """추천 결과"""

    decision: str  # GO, PIVOT, HOLD, NO_GO
    rationale: str


class ScorecardResponse(BaseModel):
    """Scorecard 응답"""

    scorecard_id: str
    signal_id: str
    signal_title: str | None = None
    total_score: float
    dimensions: dict
    recommendation: Recommendation
    created_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ScorecardListResponse(BaseModel):
    """Scorecard 목록 응답"""

    items: list[ScorecardResponse]
    total: int
    page: int
    page_size: int


class ScorecardCreate(BaseModel):
    """Scorecard 생성 요청"""

    signal_id: str
    total_score: int = 0
    market_fit: int = 0
    kt_synergy: int = 0
    technical_feasibility: int = 0
    urgency: int = 0
    revenue_potential: int = 0
    recommendation: str = "HOLD"
    evaluator_notes: str | None = None


@router.get("", response_model=ScorecardListResponse)
async def list_scorecards(
    decision: Annotated[str | None, Query(description="판정 필터 (GO, PIVOT, HOLD, NO_GO)")] = None,
    min_score: Annotated[int | None, Query(description="최소 점수 필터")] = None,
    max_score: Annotated[int | None, Query(description="최대 점수 필터")] = None,
    page: int = 1,
    page_size: int = 20,
):
    """Scorecard 목록 조회"""
    items, total = await scorecard_d1_repo.get_all(
        page=page,
        page_size=page_size,
        decision=decision,
        min_score=min_score,
        max_score=max_score,
    )

    return ScorecardListResponse(
        items=[
            ScorecardResponse(
                scorecard_id=item["scorecard_id"],
                signal_id=item["signal_id"],
                signal_title=item.get("signal_title"),
                total_score=item["total_score"],
                dimensions=item["dimensions"],
                recommendation=Recommendation(**item["recommendation"]),
                created_at=item.get("created_at"),
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats/distribution")
async def get_score_distribution():
    """Scorecard 점수 분포 통계"""
    return await scorecard_d1_repo.get_distribution()


@router.get("/{signal_id}", response_model=ScorecardResponse)
async def get_scorecard(signal_id: str):
    """Signal의 Scorecard 조회"""
    scorecard = await scorecard_d1_repo.get_by_signal_id(signal_id)
    if not scorecard:
        raise HTTPException(status_code=404, detail="Scorecard not found")

    return ScorecardResponse(
        scorecard_id=scorecard["scorecard_id"],
        signal_id=scorecard["signal_id"],
        signal_title=scorecard.get("signal_title"),
        total_score=scorecard["total_score"],
        dimensions=scorecard["dimensions"],
        recommendation=Recommendation(**scorecard["recommendation"]),
        created_at=scorecard.get("created_at"),
    )


@router.post("/evaluate/{signal_id}")
async def evaluate_signal(signal_id: str, auto: bool = True):
    """Signal 자동 평가"""
    # Signal 존재 확인
    signal = await signal_d1_repo.get_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # 이미 평가된 Signal인지 확인
    existing = await scorecard_d1_repo.get_by_signal_id(signal_id)
    if existing:
        return {
            "status": "already_scored",
            "signal_id": signal_id,
            "scorecard_id": existing["scorecard_id"],
            "message": "이미 평가된 Signal입니다.",
        }

    if auto:
        return {
            "status": "processing",
            "signal_id": signal_id,
            "message": "AI 평가가 진행 중입니다.",
        }
    else:
        return {
            "status": "manual_required",
            "signal_id": signal_id,
            "form_fields": [
                "market_fit",
                "kt_synergy",
                "technical_feasibility",
                "urgency",
                "revenue_potential",
                "evaluator_notes",
            ],
        }


@router.post("", response_model=ScorecardResponse)
async def create_scorecard(scorecard: ScorecardCreate):
    """Scorecard 수동 생성"""
    # Signal 존재 확인
    signal = await signal_d1_repo.get_by_id(scorecard.signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # 이미 평가된 Signal인지 확인
    existing = await scorecard_d1_repo.get_by_signal_id(scorecard.signal_id)
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Signal already has scorecard: {existing['scorecard_id']}"
        )

    # 총점 계산
    total_score = (
        scorecard.market_fit
        + scorecard.kt_synergy
        + scorecard.technical_feasibility
        + scorecard.urgency
        + scorecard.revenue_potential
    )

    # 추천 결정
    if total_score >= 70:
        decision = "GO"
    elif total_score >= 50:
        decision = "PIVOT"
    elif total_score >= 30:
        decision = "HOLD"
    else:
        decision = "NO_GO"

    scorecard_data = {
        "signal_id": scorecard.signal_id,
        "total_score": total_score,
        "market_fit": scorecard.market_fit,
        "kt_synergy": scorecard.kt_synergy,
        "technical_feasibility": scorecard.technical_feasibility,
        "urgency": scorecard.urgency,
        "revenue_potential": scorecard.revenue_potential,
        "recommendation": decision,
        "evaluator_notes": scorecard.evaluator_notes,
    }

    db_scorecard = await scorecard_d1_repo.create(scorecard_data)

    return ScorecardResponse(
        scorecard_id=db_scorecard["scorecard_id"],
        signal_id=db_scorecard["signal_id"],
        signal_title=db_scorecard.get("signal_title"),
        total_score=db_scorecard["total_score"],
        dimensions=db_scorecard["dimensions"],
        recommendation=Recommendation(**db_scorecard["recommendation"]),
        created_at=db_scorecard.get("created_at"),
    )
