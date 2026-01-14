"""
Scorecard Router

Scorecard 평가 API - DB 연동
"""

from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.database.repositories.scorecard import scorecard_repo
from backend.database.repositories.signal import signal_repo


router = APIRouter()


class DimensionScores(BaseModel):
    """차원별 점수"""
    problem_severity: int  # 0-20
    willingness_to_pay: int  # 0-20
    data_availability: int  # 0-20
    feasibility: int  # 0-20
    strategic_fit: int  # 0-20


class Recommendation(BaseModel):
    """추천 결과"""
    decision: str  # GO, PIVOT, HOLD, NO_GO
    next_step: str  # BRIEF, VALIDATION, PILOT_READY, DROP, NEED_MORE_EVIDENCE
    rationale: str


class ScorecardCreate(BaseModel):
    """Scorecard 생성 요청 (수동 평가)"""
    signal_id: str
    dimension_scores: DimensionScores
    red_flags: list[str] | None = None
    rationale: str | None = None


class ScorecardResponse(BaseModel):
    """Scorecard 응답"""
    scorecard_id: str
    signal_id: str
    total_score: float
    dimension_scores: dict
    red_flags: list[str]
    recommendation: dict
    scored_by: str | None
    scored_at: datetime

    class Config:
        from_attributes = True


class ScorecardListResponse(BaseModel):
    """Scorecard 목록 응답"""
    items: list[ScorecardResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=ScorecardListResponse)
async def list_scorecards(
    db: AsyncSession = Depends(get_db),
    decision: Annotated[str | None, Query(description="판정 필터 (GO, PIVOT, HOLD, NO_GO)")] = None,
    min_score: Annotated[float | None, Query(description="최소 점수 필터")] = None,
    max_score: Annotated[float | None, Query(description="최대 점수 필터")] = None,
    page: int = 1,
    page_size: int = 20,
):
    """Scorecard 목록 조회"""
    skip = (page - 1) * page_size
    items, total = await scorecard_repo.get_multi_filtered(
        db, decision, min_score, max_score, skip, page_size
    )

    return ScorecardListResponse(
        items=[
            ScorecardResponse(
                scorecard_id=item.scorecard_id,
                signal_id=item.signal_id,
                total_score=item.total_score,
                dimension_scores=item.dimension_scores,
                red_flags=item.red_flags or [],
                recommendation=item.recommendation,
                scored_by=item.scored_by,
                scored_at=item.scored_at
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/stats/distribution")
async def get_score_distribution(db: AsyncSession = Depends(get_db)):
    """Scorecard 점수 분포 통계"""
    return await scorecard_repo.get_distribution_stats(db)


@router.get("/{signal_id}", response_model=ScorecardResponse)
async def get_scorecard(signal_id: str, db: AsyncSession = Depends(get_db)):
    """Signal의 Scorecard 조회"""
    scorecard = await scorecard_repo.get_by_signal_id(db, signal_id)
    if not scorecard:
        raise HTTPException(status_code=404, detail="Scorecard not found")

    return ScorecardResponse(
        scorecard_id=scorecard.scorecard_id,
        signal_id=scorecard.signal_id,
        total_score=scorecard.total_score,
        dimension_scores=scorecard.dimension_scores,
        red_flags=scorecard.red_flags or [],
        recommendation=scorecard.recommendation,
        scored_by=scorecard.scored_by,
        scored_at=scorecard.scored_at
    )


@router.post("/evaluate/{signal_id}")
async def evaluate_signal(
    signal_id: str,
    db: AsyncSession = Depends(get_db),
    auto: bool = True
):
    """
    Signal 자동 평가

    Args:
        signal_id: 평가할 Signal ID
        auto: True면 AI 자동 평가, False면 수동 평가 폼 반환
    """
    # Signal 존재 확인
    signal = await signal_repo.get_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # 이미 평가된 Signal인지 확인
    existing = await scorecard_repo.get_by_signal_id(db, signal_id)
    if existing:
        return {
            "status": "already_scored",
            "signal_id": signal_id,
            "scorecard_id": existing.scorecard_id,
            "message": "이미 평가된 Signal입니다."
        }

    if auto:
        # TODO: ScorecardEvaluator Agent 호출
        return {
            "status": "processing",
            "signal_id": signal_id,
            "message": "AI 평가가 진행 중입니다."
        }
    else:
        return {
            "status": "manual_required",
            "signal_id": signal_id,
            "form_fields": [
                "problem_severity",
                "willingness_to_pay",
                "data_availability",
                "feasibility",
                "strategic_fit",
                "red_flags",
                "rationale"
            ]
        }


@router.post("", response_model=ScorecardResponse)
async def create_scorecard(
    scorecard: ScorecardCreate,
    db: AsyncSession = Depends(get_db)
):
    """Scorecard 수동 생성"""
    # Signal 존재 확인
    signal = await signal_repo.get_by_id(db, scorecard.signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # 이미 평가된 Signal인지 확인
    existing = await scorecard_repo.get_by_signal_id(db, scorecard.signal_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Signal already has scorecard: {existing.scorecard_id}"
        )

    # 총점 계산
    scores = scorecard.dimension_scores
    total_score = (
        scores.problem_severity +
        scores.willingness_to_pay +
        scores.data_availability +
        scores.feasibility +
        scores.strategic_fit
    )

    # 추천 결정
    red_flags = scorecard.red_flags or []
    if total_score >= 70 and len(red_flags) == 0:
        decision, next_step = "GO", "BRIEF"
    elif total_score >= 50 and len(red_flags) <= 1:
        decision, next_step = "PIVOT", "NEED_MORE_EVIDENCE"
    elif total_score >= 30:
        decision, next_step = "HOLD", "NEED_MORE_EVIDENCE"
    else:
        decision, next_step = "NO_GO", "DROP"

    # Scorecard ID 생성
    scorecard_id = await scorecard_repo.generate_scorecard_id(db)

    # DB 저장
    scorecard_data = {
        "scorecard_id": scorecard_id,
        "signal_id": scorecard.signal_id,
        "total_score": total_score,
        "dimension_scores": scores.model_dump(),
        "red_flags": red_flags,
        "recommendation": {
            "decision": decision,
            "next_step": next_step,
            "rationale": scorecard.rationale or ""
        },
        "scored_by": "manual"
    }

    db_scorecard = await scorecard_repo.create(db, scorecard_data)
    await db.commit()
    await db.refresh(db_scorecard)

    return ScorecardResponse(
        scorecard_id=db_scorecard.scorecard_id,
        signal_id=db_scorecard.signal_id,
        total_score=db_scorecard.total_score,
        dimension_scores=db_scorecard.dimension_scores,
        red_flags=db_scorecard.red_flags or [],
        recommendation=db_scorecard.recommendation,
        scored_by=db_scorecard.scored_by,
        scored_at=db_scorecard.scored_at
    )
