"""
Scorecard Router

Scorecard 평가 API
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


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
    total_score: int
    dimension_scores: DimensionScores
    red_flags: list[str]
    recommendation: Recommendation
    scored_by: str
    scored_at: datetime


@router.get("/{signal_id}")
async def get_scorecard(signal_id: str):
    """Signal의 Scorecard 조회"""
    # TODO: DB 조회
    raise HTTPException(status_code=404, detail="Scorecard not found")


@router.post("/evaluate/{signal_id}")
async def evaluate_signal(signal_id: str, auto: bool = True):
    """
    Signal 자동 평가
    
    Args:
        signal_id: 평가할 Signal ID
        auto: True면 AI 자동 평가, False면 수동 평가 폼 반환
    """
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


@router.post("")
async def create_scorecard(scorecard: ScorecardCreate):
    """Scorecard 수동 생성"""
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
    
    # TODO: DB 저장
    scorecard_id = f"SCR-{datetime.now().year}-001"
    
    return ScorecardResponse(
        scorecard_id=scorecard_id,
        signal_id=scorecard.signal_id,
        total_score=total_score,
        dimension_scores=scorecard.dimension_scores,
        red_flags=red_flags,
        recommendation=Recommendation(
            decision=decision,
            next_step=next_step,
            rationale=scorecard.rationale or ""
        ),
        scored_by="manual",
        scored_at=datetime.utcnow()
    )


@router.get("/stats/distribution")
async def get_score_distribution():
    """Scorecard 점수 분포 통계"""
    return {
        "total_scored": 0,
        "go_count": 0,
        "pivot_count": 0,
        "hold_count": 0,
        "no_go_count": 0,
        "average_score": 0,
        "red_flag_rate": 0
    }
