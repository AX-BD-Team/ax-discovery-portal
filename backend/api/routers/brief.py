"""
Brief Router

1-Page Opportunity Brief API (D1 HTTP API 사용)
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from backend.integrations.cloudflare_d1.repositories import brief_d1_repo, signal_d1_repo

router = APIRouter()


class Customer(BaseModel):
    """고객 정보"""

    segment: str
    buyer_role: str | None = None
    account: str | None = None


class Problem(BaseModel):
    """문제 정의"""

    pain: str
    why_now: str | None = None


class SolutionHypothesis(BaseModel):
    """솔루션 가설"""

    approach: str


class ValidationPlan(BaseModel):
    """검증 계획"""

    method: str = "5DAY_SPRINT"
    timebox_days: int = 5
    questions: list[str] = []


class BriefCreate(BaseModel):
    """Brief 생성 요청"""

    signal_id: str
    title: str
    customer: Customer
    problem: Problem
    solution_hypothesis: SolutionHypothesis
    kpis: list[str] = []
    validation_plan: ValidationPlan
    risks: list[str] = []
    owner: str = ""


class BriefResponse(BaseModel):
    """Brief 응답"""

    brief_id: str
    signal_id: str
    title: str
    customer: Customer
    problem: Problem
    solution_hypothesis: SolutionHypothesis
    kpis: list[str]
    validation_plan: ValidationPlan
    risks: list[str]
    status: str
    owner: str
    confluence_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BriefListResponse(BaseModel):
    """Brief 목록 응답"""

    items: list[BriefResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=list[BriefResponse])
async def list_briefs(
    status: Annotated[str | None, Query(description="상태 필터")] = None,
    page: int = 1,
    page_size: int = 20,
):
    """Brief 목록 조회"""
    items, total = await brief_d1_repo.get_all(
        page=page,
        page_size=page_size,
        status=status,
    )

    return [
        BriefResponse(
            brief_id=item["brief_id"],
            signal_id=item["signal_id"],
            title=item["title"],
            customer=Customer(**item["customer"]),
            problem=Problem(**item["problem"]),
            solution_hypothesis=SolutionHypothesis(**item["solution_hypothesis"]),
            kpis=item.get("kpis", []),
            validation_plan=ValidationPlan(**item["validation_plan"]),
            risks=item.get("risks", []),
            status=item["status"],
            owner=item.get("owner", ""),
            confluence_url=item.get("confluence_url"),
            created_at=item.get("created_at"),
            updated_at=item.get("updated_at"),
        )
        for item in items
    ]


@router.get("/{brief_id}", response_model=BriefResponse)
async def get_brief(brief_id: str):
    """Brief 상세 조회"""
    brief = await brief_d1_repo.get_by_id(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    return BriefResponse(
        brief_id=brief["brief_id"],
        signal_id=brief["signal_id"],
        title=brief["title"],
        customer=Customer(**brief["customer"]),
        problem=Problem(**brief["problem"]),
        solution_hypothesis=SolutionHypothesis(**brief["solution_hypothesis"]),
        kpis=brief.get("kpis", []),
        validation_plan=ValidationPlan(**brief["validation_plan"]),
        risks=brief.get("risks", []),
        status=brief["status"],
        owner=brief.get("owner", ""),
        confluence_url=brief.get("confluence_url"),
        created_at=brief.get("created_at"),
        updated_at=brief.get("updated_at"),
    )


@router.post("/generate/{signal_id}")
async def generate_brief(signal_id: str):
    """Signal에서 Brief 자동 생성"""
    # Signal 존재 확인
    signal = await signal_d1_repo.get_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    return {
        "status": "processing",
        "signal_id": signal_id,
        "message": "Brief 생성이 진행 중입니다.",
    }


@router.post("", response_model=BriefResponse)
async def create_brief(brief: BriefCreate):
    """Brief 수동 생성"""
    brief_data = {
        "signal_id": brief.signal_id,
        "title": brief.title,
        "executive_summary": "",
        "problem_statement": brief.problem.pain,
        "proposed_solution": brief.solution_hypothesis.approach,
        "target_customer": brief.customer.segment,
        "business_model": "",
        "competitive_advantage": "",
        "next_steps": "",
    }

    db_brief = await brief_d1_repo.create(brief_data)

    return BriefResponse(
        brief_id=db_brief["brief_id"],
        signal_id=db_brief["signal_id"],
        title=db_brief["title"],
        customer=Customer(**db_brief["customer"]),
        problem=Problem(**db_brief["problem"]),
        solution_hypothesis=SolutionHypothesis(**db_brief["solution_hypothesis"]),
        kpis=db_brief.get("kpis", []),
        validation_plan=ValidationPlan(**db_brief["validation_plan"]),
        risks=db_brief.get("risks", []),
        status=db_brief["status"],
        owner=db_brief.get("owner", ""),
        confluence_url=db_brief.get("confluence_url"),
        created_at=db_brief.get("created_at"),
        updated_at=db_brief.get("updated_at"),
    )


@router.post("/{brief_id}/approve")
async def approve_brief(brief_id: str):
    """Brief 승인"""
    brief = await brief_d1_repo.get_by_id(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    await brief_d1_repo.update_status(brief_id, "APPROVED")

    return {"status": "approved", "brief_id": brief_id, "message": "Brief가 승인되었습니다."}


@router.post("/{brief_id}/start-validation")
async def start_validation(brief_id: str):
    """Validation 시작"""
    brief = await brief_d1_repo.get_by_id(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    await brief_d1_repo.update_status(brief_id, "VALIDATED")

    return {
        "status": "validation_started",
        "brief_id": brief_id,
        "message": "Validation이 시작되었습니다.",
    }
