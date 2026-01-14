"""
Brief Router

1-Page Opportunity Brief API - DB 연동
"""

from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.database.repositories.brief import brief_repo
from backend.database.repositories.signal import signal_repo
from backend.database.repositories.scorecard import scorecard_repo
from backend.database.models.brief import BriefStatus


router = APIRouter()


class Customer(BaseModel):
    """고객 정보"""
    segment: str
    buyer_role: str | None = None
    users: str | None = None
    account: str | None = None


class Problem(BaseModel):
    """문제 정의"""
    pain: str
    why_now: str | None = None
    current_process: str | None = None


class SolutionHypothesis(BaseModel):
    """솔루션 가설"""
    approach: str
    integration_points: list[str] | None = None
    data_needed: list[str] | None = None


class ValidationPlan(BaseModel):
    """검증 계획"""
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
    evidence: list[str]
    validation_plan: ValidationPlan
    mvp_scope: dict | None = None
    risks: list[str] | None = None
    owner: str


class BriefResponse(BaseModel):
    """Brief 응답"""
    brief_id: str
    signal_id: str
    title: str
    customer: dict
    problem: dict
    solution_hypothesis: dict
    kpis: list
    evidence: list
    validation_plan: dict
    mvp_scope: dict | None
    risks: list | None
    status: str
    owner: str
    confluence_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class BriefListResponse(BaseModel):
    """Brief 목록 응답"""
    items: list[BriefResponse]
    total: int
    page: int
    page_size: int


class BriefSummary(BaseModel):
    """Brief 요약 (목록용)"""
    brief_id: str
    signal_id: str
    title: str
    status: str
    owner: str
    confluence_url: str | None
    created_at: datetime


class BriefListSummaryResponse(BaseModel):
    """Brief 목록 요약 응답"""
    items: list[BriefSummary]
    total: int
    page: int
    page_size: int


@router.get("", response_model=BriefListSummaryResponse)
async def list_briefs(
    db: AsyncSession = Depends(get_db),
    status: Annotated[str | None, Query(description="상태 필터 (DRAFT, REVIEW, APPROVED, VALIDATED, PILOT_READY)")] = None,
    owner: Annotated[str | None, Query(description="담당자 필터")] = None,
    page: int = 1,
    page_size: int = 20
):
    """Brief 목록 조회"""
    skip = (page - 1) * page_size
    items, total = await brief_repo.get_multi_filtered(
        db, status, owner, skip, page_size
    )

    return BriefListSummaryResponse(
        items=[
            BriefSummary(
                brief_id=item.brief_id,
                signal_id=item.signal_id,
                title=item.title,
                status=item.status.value if hasattr(item.status, 'value') else item.status,
                owner=item.owner,
                confluence_url=item.confluence_url,
                created_at=item.created_at
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/stats")
async def get_brief_stats(db: AsyncSession = Depends(get_db)):
    """Brief 통계 조회"""
    return await brief_repo.get_stats(db)


@router.get("/{brief_id}", response_model=BriefResponse)
async def get_brief(brief_id: str, db: AsyncSession = Depends(get_db)):
    """Brief 상세 조회"""
    brief = await brief_repo.get_by_id(db, brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    return BriefResponse(
        brief_id=brief.brief_id,
        signal_id=brief.signal_id,
        title=brief.title,
        customer=brief.customer,
        problem=brief.problem,
        solution_hypothesis=brief.solution_hypothesis,
        kpis=brief.kpis,
        evidence=brief.evidence,
        validation_plan=brief.validation_plan,
        mvp_scope=brief.mvp_scope,
        risks=brief.risks,
        status=brief.status.value if hasattr(brief.status, 'value') else brief.status,
        owner=brief.owner,
        confluence_url=brief.confluence_url,
        created_at=brief.created_at
    )


@router.post("/generate/{signal_id}")
async def generate_brief(
    signal_id: str,
    db: AsyncSession = Depends(get_db),
    auto_fill: bool = True
):
    """
    Signal에서 Brief 자동 생성

    Args:
        signal_id: Brief를 생성할 Signal ID
        auto_fill: True면 AI로 자동 채움
    """
    # Signal 존재 확인
    signal = await signal_repo.get_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # 이미 Brief가 있는지 확인
    existing = await brief_repo.get_by_signal_id(db, signal_id)
    if existing:
        return {
            "status": "already_exists",
            "signal_id": signal_id,
            "brief_id": existing.brief_id,
            "message": "이미 Brief가 생성된 Signal입니다."
        }

    # Scorecard가 GO인지 확인 (권장)
    scorecard = await scorecard_repo.get_by_signal_id(db, signal_id)
    if scorecard:
        decision = scorecard.recommendation.get("decision", "")
        if decision not in ["GO", "PIVOT"]:
            return {
                "status": "scorecard_not_passed",
                "signal_id": signal_id,
                "scorecard_decision": decision,
                "message": f"Scorecard 판정이 {decision}입니다. GO 또는 PIVOT 판정이 필요합니다."
            }

    if auto_fill:
        # TODO: BriefWriter Agent 호출
        return {
            "status": "generating",
            "signal_id": signal_id,
            "message": "Brief 초안을 생성 중입니다. 승인 후 Confluence에 게시됩니다."
        }
    else:
        return {
            "status": "manual_required",
            "signal_id": signal_id,
            "form_fields": [
                "title", "customer", "problem", "solution_hypothesis",
                "kpis", "evidence", "validation_plan", "risks", "owner"
            ]
        }


@router.post("", response_model=BriefResponse)
async def create_brief(
    brief: BriefCreate,
    db: AsyncSession = Depends(get_db)
):
    """Brief 수동 생성"""
    # Signal 존재 확인
    signal = await signal_repo.get_by_id(db, brief.signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # 이미 Brief가 있는지 확인
    existing = await brief_repo.get_by_signal_id(db, brief.signal_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Signal already has brief: {existing.brief_id}"
        )

    # Brief ID 생성
    brief_id = await brief_repo.generate_brief_id(db)

    # DB 저장
    brief_data = {
        "brief_id": brief_id,
        "signal_id": brief.signal_id,
        "title": brief.title,
        "customer": brief.customer.model_dump(),
        "problem": brief.problem.model_dump(),
        "solution_hypothesis": brief.solution_hypothesis.model_dump(),
        "kpis": brief.kpis,
        "evidence": brief.evidence,
        "validation_plan": brief.validation_plan.model_dump(),
        "mvp_scope": brief.mvp_scope,
        "risks": brief.risks,
        "status": BriefStatus.DRAFT,
        "owner": brief.owner
    }

    db_brief = await brief_repo.create(db, brief_data)
    await db.commit()
    await db.refresh(db_brief)

    return BriefResponse(
        brief_id=db_brief.brief_id,
        signal_id=db_brief.signal_id,
        title=db_brief.title,
        customer=db_brief.customer,
        problem=db_brief.problem,
        solution_hypothesis=db_brief.solution_hypothesis,
        kpis=db_brief.kpis,
        evidence=db_brief.evidence,
        validation_plan=db_brief.validation_plan,
        mvp_scope=db_brief.mvp_scope,
        risks=db_brief.risks,
        status=db_brief.status.value,
        owner=db_brief.owner,
        confluence_url=db_brief.confluence_url,
        created_at=db_brief.created_at
    )


@router.post("/{brief_id}/approve")
async def approve_brief(
    brief_id: str,
    approver: str,
    db: AsyncSession = Depends(get_db)
):
    """Brief 승인 및 Confluence 게시"""
    brief = await brief_repo.get_by_id(db, brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    if brief.status != BriefStatus.DRAFT and brief.status != BriefStatus.REVIEW:
        return {
            "status": "invalid_state",
            "brief_id": brief_id,
            "current_status": brief.status.value,
            "message": f"현재 상태({brief.status.value})에서는 승인할 수 없습니다."
        }

    # TODO: Confluence 페이지 생성 (ConfluenceSync Agent 호출)
    # 임시로 더미 URL 생성
    confluence_url = f"https://confluence.example.com/display/AXBD/{brief_id}"

    # 상태 업데이트
    updated_brief = await brief_repo.update_status(
        db, brief_id, BriefStatus.APPROVED, confluence_url
    )
    await db.commit()

    return {
        "status": "approved",
        "brief_id": brief_id,
        "approver": approver,
        "confluence_url": confluence_url,
        "message": "Brief가 승인되었습니다."
    }


@router.post("/{brief_id}/start-validation")
async def start_validation(
    brief_id: str,
    db: AsyncSession = Depends(get_db),
    method: str = "5DAY_SPRINT"
):
    """Validation Sprint 시작"""
    brief = await brief_repo.get_by_id(db, brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    if brief.status != BriefStatus.APPROVED:
        return {
            "status": "invalid_state",
            "brief_id": brief_id,
            "current_status": brief.status.value,
            "message": f"Validation은 APPROVED 상태에서만 시작할 수 있습니다. 현재: {brief.status.value}"
        }

    # 상태를 VALIDATED로 변경 (검증 진행 중)
    # TODO: SprintFacilitator Agent 호출
    await brief_repo.update_status(db, brief_id, BriefStatus.VALIDATED)
    await db.commit()

    # Validation ID 생성 (간단한 형태)
    validation_id = f"VAL-{datetime.now().year}-{brief_id.split('-')[-1]}"

    return {
        "status": "started",
        "brief_id": brief_id,
        "validation_id": validation_id,
        "method": method,
        "message": f"{method} 검증이 시작되었습니다."
    }


@router.post("/{brief_id}/complete-validation")
async def complete_validation(
    brief_id: str,
    db: AsyncSession = Depends(get_db),
    success: bool = True
):
    """Validation 완료 처리"""
    brief = await brief_repo.get_by_id(db, brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    if brief.status != BriefStatus.VALIDATED:
        return {
            "status": "invalid_state",
            "brief_id": brief_id,
            "current_status": brief.status.value,
            "message": f"Validation 완료는 VALIDATED 상태에서만 가능합니다."
        }

    if success:
        # Pilot-ready로 전환
        await brief_repo.update_status(db, brief_id, BriefStatus.PILOT_READY)
        await db.commit()
        return {
            "status": "pilot_ready",
            "brief_id": brief_id,
            "message": "Validation 성공! Pilot-ready(S3) 상태로 전환되었습니다."
        }
    else:
        # 다시 REVIEW 상태로
        await brief_repo.update_status(db, brief_id, BriefStatus.REVIEW)
        await db.commit()
        return {
            "status": "needs_revision",
            "brief_id": brief_id,
            "message": "Validation 실패. 재검토가 필요합니다."
        }
