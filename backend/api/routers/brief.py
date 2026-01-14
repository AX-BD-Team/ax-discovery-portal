"""
Brief Router

1-Page Opportunity Brief API
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class Customer(BaseModel):
    segment: str
    buyer_role: str | None = None
    users: str | None = None
    account: str | None = None


class Problem(BaseModel):
    pain: str
    why_now: str | None = None
    current_process: str | None = None


class SolutionHypothesis(BaseModel):
    approach: str
    integration_points: list[str] | None = None
    data_needed: list[str] | None = None


class ValidationPlan(BaseModel):
    questions: list[str]
    method: str  # 5DAY_SPRINT, INTERVIEW, DATA_ANALYSIS, BUYER_REVIEW
    success_criteria: list[str]
    timebox_days: int = 5


class BriefCreate(BaseModel):
    """Brief 생성 요청"""
    signal_id: str
    title: str
    customer: Customer
    problem: Problem
    solution_hypothesis: SolutionHypothesis
    kpis: list[str]
    validation_plan: ValidationPlan
    risks: list[str] | None = None
    owner: str | None = None


class BriefResponse(BaseModel):
    """Brief 응답"""
    brief_id: str
    signal_id: str
    title: str
    status: str
    confluence_url: str | None = None
    created_at: datetime


@router.get("")
async def list_briefs(
    status: str | None = None,
    play_id: str | None = None,
    page: int = 1,
    page_size: int = 20
):
    """Brief 목록 조회"""
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size
    }


@router.get("/{brief_id}")
async def get_brief(brief_id: str):
    """Brief 상세 조회"""
    raise HTTPException(status_code=404, detail="Brief not found")


@router.post("/generate/{signal_id}")
async def generate_brief(signal_id: str, auto_fill: bool = True):
    """
    Signal에서 Brief 자동 생성
    
    Args:
        signal_id: Brief를 생성할 Signal ID
        auto_fill: True면 AI로 자동 채움
    """
    # TODO: BriefWriter Agent 호출
    return {
        "status": "generating",
        "signal_id": signal_id,
        "message": "Brief 초안을 생성 중입니다. 승인 후 Confluence에 게시됩니다."
    }


@router.post("")
async def create_brief(brief: BriefCreate):
    """Brief 수동 생성"""
    brief_id = f"BRF-{datetime.now().year}-001"
    
    # TODO: DB 저장 및 Confluence 연동
    
    return BriefResponse(
        brief_id=brief_id,
        signal_id=brief.signal_id,
        title=brief.title,
        status="DRAFT",
        confluence_url=None,
        created_at=datetime.utcnow()
    )


@router.post("/{brief_id}/approve")
async def approve_brief(brief_id: str, approver: str):
    """Brief 승인 및 Confluence 게시"""
    # TODO: Confluence 페이지 생성
    return {
        "status": "approved",
        "brief_id": brief_id,
        "approver": approver,
        "confluence_url": f"https://confluence.example.com/display/AXBD/{brief_id}"
    }


@router.post("/{brief_id}/start-validation")
async def start_validation(brief_id: str, method: str = "5DAY_SPRINT"):
    """Validation Sprint 시작"""
    # TODO: SprintFacilitator Agent 호출
    return {
        "status": "started",
        "brief_id": brief_id,
        "validation_id": f"VAL-{datetime.now().year}-001",
        "method": method
    }
