"""
Stages Router

Opportunity 단계 관리 API
- Opportunity CRUD
- 단계 전환 (Advance/Hold/Drop/Resume)
- 승인 요청 관리
- 대시보드 및 퍼널 분석
"""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.database.models.approval_request import ApprovalStatus, ApprovalType
from backend.database.models.opportunity import OpportunityStage
from backend.database.models.stage_transition import GateDecision, TransitionTrigger
from backend.database.repositories.opportunity import (
    approval_request_repo,
    opportunity_repo,
    stage_transition_repo,
)

router = APIRouter()


# ============================================================
# Pydantic 스키마
# ============================================================


class OpportunityCreate(BaseModel):
    """Opportunity 생성 요청"""

    title: str = Field(..., description="기회 제목")
    description: str | None = Field(None, description="설명")
    signal_id: str | None = Field(None, description="연결된 Signal ID")
    brief_id: str | None = Field(None, description="연결된 Brief ID")
    bd_owner: str | None = Field(None, description="BD 담당자")
    play_id: str | None = Field(None, description="Play ID")
    tags: list[str] | None = Field(None, description="태그")


class OpportunityResponse(BaseModel):
    """Opportunity 응답"""

    opportunity_id: str
    title: str
    description: str | None = None
    current_stage: str
    signal_id: str | None = None
    brief_id: str | None = None
    bd_owner: str | None = None
    play_id: str | None = None
    stage_artifacts: dict | None = None
    gate_decisions: dict | None = None
    hold_reason: str | None = None
    drop_reason: str | None = None
    tags: list | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class OpportunityListResponse(BaseModel):
    """Opportunity 목록 응답"""

    items: list[OpportunityResponse]
    total: int
    page: int
    page_size: int


class StageAdvanceRequest(BaseModel):
    """단계 전환 요청"""

    notes: str | None = Field(None, description="전환 사유/메모")
    triggered_by: str | None = Field(None, description="요청자")


class HoldRequest(BaseModel):
    """HOLD 전환 요청"""

    reason: str = Field(..., description="보류 사유")
    triggered_by: str | None = Field(None, description="요청자")


class DropRequest(BaseModel):
    """DROP 전환 요청"""

    reason: str = Field(..., description="중단 사유")
    triggered_by: str | None = Field(None, description="요청자")


class ApprovalRequestCreate(BaseModel):
    """승인 요청 생성"""

    target_stage: str = Field(..., description="목표 단계")
    approval_type: str = Field(default="STAGE_ADVANCE", description="승인 유형")
    approvers: list[dict] = Field(..., description="승인자 목록")
    requested_by: str = Field(..., description="요청자")
    request_reason: str | None = Field(None, description="요청 사유")
    artifacts: dict | None = Field(None, description="관련 아티팩트")


class ApprovalResponse(BaseModel):
    """승인 요청 응답"""

    request_id: str
    opportunity_id: str
    target_stage: str
    approval_type: str
    status: str
    approvers: list
    responses: list | None = None
    requested_by: str
    request_reason: str | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalDecisionRequest(BaseModel):
    """승인/거부 요청"""

    decision: str = Field(..., description="APPROVED 또는 REJECTED")
    responded_by: str = Field(..., description="응답자")
    comments: str | None = Field(None, description="코멘트")


class StageTransitionResponse(BaseModel):
    """단계 전환 이력 응답"""

    transition_id: str
    opportunity_id: str
    from_stage: str
    to_stage: str
    trigger: str
    gate_decision: str | None = None
    approver: str | None = None
    approved_at: datetime | None = None
    triggered_by: str | None = None
    notes: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Opportunity CRUD
# ============================================================


@router.get("/opportunities", response_model=OpportunityListResponse)
async def list_opportunities(
    db: Annotated[AsyncSession, Depends(get_db)],
    stage: Annotated[str | None, Query(description="단계 필터")] = None,
    bd_owner: Annotated[str | None, Query(description="BD 담당자 필터")] = None,
    play_id: Annotated[str | None, Query(description="Play ID 필터")] = None,
    is_active: Annotated[bool | None, Query(description="활성 상태 필터")] = None,
    page: int = 1,
    page_size: int = 20,
):
    """Opportunity 목록 조회"""
    skip = (page - 1) * page_size
    items, total = await opportunity_repo.get_multi_filtered(
        db,
        stage=stage,
        bd_owner=bd_owner,
        play_id=play_id,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )

    return OpportunityListResponse(
        items=[
            OpportunityResponse(
                opportunity_id=item.opportunity_id,
                title=item.title,
                description=item.description,
                current_stage=item.current_stage.value,
                signal_id=item.signal_id,
                brief_id=item.brief_id,
                bd_owner=item.bd_owner,
                play_id=item.play_id,
                stage_artifacts=item.stage_artifacts,
                gate_decisions=item.gate_decisions,
                hold_reason=item.hold_reason,
                drop_reason=item.drop_reason,
                tags=item.tags,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Opportunity 상세 조회"""
    opp = await opportunity_repo.get_by_id(db, opportunity_id, include_relations=True)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return OpportunityResponse(
        opportunity_id=opp.opportunity_id,
        title=opp.title,
        description=opp.description,
        current_stage=opp.current_stage.value,
        signal_id=opp.signal_id,
        brief_id=opp.brief_id,
        bd_owner=opp.bd_owner,
        play_id=opp.play_id,
        stage_artifacts=opp.stage_artifacts,
        gate_decisions=opp.gate_decisions,
        hold_reason=opp.hold_reason,
        drop_reason=opp.drop_reason,
        tags=opp.tags,
        created_at=opp.created_at,
        updated_at=opp.updated_at,
    )


@router.post("/opportunities", response_model=OpportunityResponse)
async def create_opportunity(
    data: OpportunityCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Opportunity 생성"""
    opportunity_id = await opportunity_repo.generate_opportunity_id(db)

    opp_data: dict[str, Any] = {
        "opportunity_id": opportunity_id,
        "title": data.title,
        "description": data.description,
        "current_stage": OpportunityStage.DISCOVERY,
        "signal_id": data.signal_id,
        "brief_id": data.brief_id,
        "bd_owner": data.bd_owner,
        "play_id": data.play_id,
        "tags": data.tags,
        "stage_artifacts": {},
        "gate_decisions": {},
    }

    opp = await opportunity_repo.create(db, opp_data)
    await db.commit()

    return OpportunityResponse(
        opportunity_id=opp.opportunity_id,
        title=opp.title,
        description=opp.description,
        current_stage=opp.current_stage.value,
        signal_id=opp.signal_id,
        brief_id=opp.brief_id,
        bd_owner=opp.bd_owner,
        play_id=opp.play_id,
        stage_artifacts=opp.stage_artifacts,
        gate_decisions=opp.gate_decisions,
        hold_reason=opp.hold_reason,
        drop_reason=opp.drop_reason,
        tags=opp.tags,
        created_at=opp.created_at,
        updated_at=opp.updated_at,
    )


# ============================================================
# 단계 전환
# ============================================================

# 단계 순서 정의
STAGE_ORDER = [
    OpportunityStage.DISCOVERY,
    OpportunityStage.IDEA_CARD,
    OpportunityStage.GATE1_SELECTION,
    OpportunityStage.MOCKUP,
    OpportunityStage.GATE2_VALIDATION,
    OpportunityStage.BIZ_PLANNING,
    OpportunityStage.PILOT_POC,
    OpportunityStage.PRE_PROPOSAL,
    OpportunityStage.HANDOFF,
]

# HITL 필수 단계
HITL_REQUIRED_STAGES = {
    OpportunityStage.GATE1_SELECTION,
    OpportunityStage.GATE2_VALIDATION,
    OpportunityStage.BIZ_PLANNING,
    OpportunityStage.PRE_PROPOSAL,
    OpportunityStage.HANDOFF,
}


def get_next_stage(current: OpportunityStage) -> OpportunityStage | None:
    """다음 단계 반환"""
    try:
        current_idx = STAGE_ORDER.index(current)
        if current_idx < len(STAGE_ORDER) - 1:
            return STAGE_ORDER[current_idx + 1]
    except ValueError:
        pass
    return None


@router.post("/opportunities/{opportunity_id}/advance")
async def advance_opportunity(
    opportunity_id: str,
    data: StageAdvanceRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """다음 단계로 전환"""
    opp = await opportunity_repo.get_by_id(db, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opp.current_stage in (OpportunityStage.HOLD, OpportunityStage.DROP):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot advance from {opp.current_stage.value} state. Use /resume first.",
        )

    next_stage = get_next_stage(opp.current_stage)
    if not next_stage:
        raise HTTPException(
            status_code=400,
            detail=f"Already at final stage: {opp.current_stage.value}",
        )

    # HITL 필수 단계인 경우 승인 요청 확인
    if next_stage in HITL_REQUIRED_STAGES:
        pending_approval = await _check_pending_approval(db, opportunity_id, next_stage.value)
        if pending_approval:
            raise HTTPException(
                status_code=400,
                detail=f"Stage {next_stage.value} requires approval. Approval request: {pending_approval.request_id}",
            )

    # 단계 전환 수행
    from_stage = opp.current_stage
    await _perform_transition(
        db,
        opp,
        from_stage,
        next_stage,
        TransitionTrigger.MANUAL,
        data.triggered_by,
        data.notes,
    )

    await db.commit()

    return {
        "status": "success",
        "opportunity_id": opportunity_id,
        "from_stage": from_stage.value,
        "to_stage": next_stage.value,
        "message": f"단계가 {from_stage.value}에서 {next_stage.value}(으)로 전환되었습니다.",
    }


@router.post("/opportunities/{opportunity_id}/hold")
async def hold_opportunity(
    opportunity_id: str,
    data: HoldRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """HOLD 상태로 전환"""
    opp = await opportunity_repo.get_by_id(db, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opp.current_stage == OpportunityStage.HOLD:
        raise HTTPException(status_code=400, detail="Already in HOLD state")

    if opp.current_stage == OpportunityStage.DROP:
        raise HTTPException(status_code=400, detail="Cannot hold a dropped opportunity")

    from_stage = opp.current_stage

    # 단계 전환 수행
    await _perform_transition(
        db,
        opp,
        from_stage,
        OpportunityStage.HOLD,
        TransitionTrigger.MANUAL,
        data.triggered_by,
        data.reason,
        gate_decision=GateDecision.HOLD,
    )

    # hold_reason 저장
    opp.hold_reason = data.reason
    await db.commit()

    return {
        "status": "success",
        "opportunity_id": opportunity_id,
        "from_stage": from_stage.value,
        "to_stage": "HOLD",
        "reason": data.reason,
        "message": "기회가 보류 상태로 전환되었습니다.",
    }


@router.post("/opportunities/{opportunity_id}/drop")
async def drop_opportunity(
    opportunity_id: str,
    data: DropRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """DROP 상태로 전환"""
    opp = await opportunity_repo.get_by_id(db, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opp.current_stage == OpportunityStage.DROP:
        raise HTTPException(status_code=400, detail="Already dropped")

    from_stage = opp.current_stage

    # 단계 전환 수행
    await _perform_transition(
        db,
        opp,
        from_stage,
        OpportunityStage.DROP,
        TransitionTrigger.MANUAL,
        data.triggered_by,
        data.reason,
        gate_decision=GateDecision.STOP,
    )

    # drop_reason 저장
    opp.drop_reason = data.reason
    await db.commit()

    return {
        "status": "success",
        "opportunity_id": opportunity_id,
        "from_stage": from_stage.value,
        "to_stage": "DROP",
        "reason": data.reason,
        "message": "기회가 중단되었습니다.",
    }


@router.post("/opportunities/{opportunity_id}/resume")
async def resume_opportunity(
    opportunity_id: str,
    data: StageAdvanceRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """HOLD 상태에서 복귀"""
    opp = await opportunity_repo.get_by_id(db, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opp.current_stage != OpportunityStage.HOLD:
        raise HTTPException(status_code=400, detail="Not in HOLD state")

    # 마지막 HOLD 전환 이력에서 이전 단계 찾기
    transitions = await stage_transition_repo.get_by_opportunity_id(db, opportunity_id)
    previous_stage = None
    for t in transitions:
        if t.to_stage == "HOLD":
            previous_stage = OpportunityStage(t.from_stage)
            break

    if not previous_stage:
        previous_stage = OpportunityStage.DISCOVERY

    # 복귀 전환 수행
    await _perform_transition(
        db,
        opp,
        OpportunityStage.HOLD,
        previous_stage,
        TransitionTrigger.MANUAL,
        data.triggered_by,
        data.notes or "HOLD 상태에서 복귀",
    )

    # hold_reason 초기화
    opp.hold_reason = None
    await db.commit()

    return {
        "status": "success",
        "opportunity_id": opportunity_id,
        "from_stage": "HOLD",
        "to_stage": previous_stage.value,
        "message": f"기회가 {previous_stage.value} 단계로 복귀되었습니다.",
    }


@router.get(
    "/opportunities/{opportunity_id}/transitions", response_model=list[StageTransitionResponse]
)
async def get_opportunity_transitions(
    opportunity_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
):
    """Opportunity 단계 전환 이력 조회"""
    opp = await opportunity_repo.get_by_id(db, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    transitions = await stage_transition_repo.get_by_opportunity_id(db, opportunity_id, limit)

    return [
        StageTransitionResponse(
            transition_id=t.transition_id,
            opportunity_id=t.opportunity_id,
            from_stage=t.from_stage,
            to_stage=t.to_stage,
            trigger=t.trigger.value,
            gate_decision=t.gate_decision.value if t.gate_decision else None,
            approver=t.approver,
            approved_at=t.approved_at,
            triggered_by=t.triggered_by,
            notes=t.notes,
            created_at=t.created_at,
        )
        for t in transitions
    ]


# ============================================================
# 승인 요청 관리
# ============================================================


@router.get("/approvals", response_model=list[ApprovalResponse])
async def list_pending_approvals(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
):
    """대기 중인 승인 요청 목록 조회"""
    skip = (page - 1) * page_size
    items, _ = await approval_request_repo.get_pending_all(db, skip, page_size)

    return [
        ApprovalResponse(
            request_id=item.request_id,
            opportunity_id=item.opportunity_id,
            target_stage=item.target_stage,
            approval_type=item.approval_type.value,
            status=item.status.value,
            approvers=item.approvers,
            responses=item.responses,
            requested_by=item.requested_by,
            request_reason=item.request_reason,
            expires_at=item.expires_at,
            created_at=item.created_at,
        )
        for item in items
    ]


@router.post("/opportunities/{opportunity_id}/approval-request", response_model=ApprovalResponse)
async def create_approval_request(
    opportunity_id: str,
    data: ApprovalRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """승인 요청 생성"""
    opp = await opportunity_repo.get_by_id(db, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # 이미 대기 중인 승인 요청이 있는지 확인
    existing = await _check_pending_approval(db, opportunity_id, data.target_stage)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Pending approval request already exists: {existing.request_id}",
        )

    request_id = await approval_request_repo.generate_request_id(db)

    approval_data = {
        "request_id": request_id,
        "opportunity_id": opportunity_id,
        "target_stage": data.target_stage,
        "approval_type": ApprovalType(data.approval_type),
        "status": ApprovalStatus.PENDING,
        "approvers": data.approvers,
        "requested_by": data.requested_by,
        "request_reason": data.request_reason,
        "artifacts": data.artifacts,
        "responses": [],
    }

    approval = await approval_request_repo.create(db, approval_data)
    await db.commit()

    return ApprovalResponse(
        request_id=approval.request_id,
        opportunity_id=approval.opportunity_id,
        target_stage=approval.target_stage,
        approval_type=approval.approval_type.value,
        status=approval.status.value,
        approvers=approval.approvers,
        responses=approval.responses,
        requested_by=approval.requested_by,
        request_reason=approval.request_reason,
        expires_at=approval.expires_at,
        created_at=approval.created_at,
    )


@router.post("/approvals/{request_id}/approve")
async def approve_request(
    request_id: str,
    data: ApprovalDecisionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """승인 요청 승인"""
    return await _process_approval_decision(db, request_id, data, "APPROVED")


@router.post("/approvals/{request_id}/reject")
async def reject_request(
    request_id: str,
    data: ApprovalDecisionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """승인 요청 거부"""
    return await _process_approval_decision(db, request_id, data, "REJECTED")


# ============================================================
# 대시보드 및 분석
# ============================================================


@router.get("/dashboard")
async def get_stage_dashboard(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """단계별 현황 대시보드"""
    stats = await opportunity_repo.get_stage_stats(db)

    return {
        "total": stats["total"],
        "active": stats["active"],
        "inactive": stats["inactive"],
        "by_stage": stats["by_stage"],
    }


@router.get("/funnel")
async def get_funnel_analysis(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """파이프라인 퍼널 분석"""
    funnel_data = await opportunity_repo.get_funnel_data(db)

    # 전환율 계산
    for i, stage in enumerate(funnel_data):
        if i == 0:
            stage["conversion_rate"] = 100.0
        else:
            prev_count = funnel_data[i - 1]["count"]
            if prev_count > 0:
                stage["conversion_rate"] = round((stage["count"] / prev_count) * 100, 1)
            else:
                stage["conversion_rate"] = 0.0

    return {
        "stages": funnel_data,
        "total_opportunities": funnel_data[0]["count"] if funnel_data else 0,
        "final_stage_count": funnel_data[-1]["count"] if funnel_data else 0,
    }


# ============================================================
# 헬퍼 함수
# ============================================================


async def _perform_transition(
    db: AsyncSession,
    opp,
    from_stage: OpportunityStage,
    to_stage: OpportunityStage,
    trigger: TransitionTrigger,
    triggered_by: str | None,
    notes: str | None,
    gate_decision: GateDecision | None = None,
    approver: str | None = None,
):
    """단계 전환 수행 및 이력 저장"""
    # 전환 이력 저장
    transition_id = await stage_transition_repo.generate_transition_id(db)
    transition_data = {
        "transition_id": transition_id,
        "opportunity_id": opp.opportunity_id,
        "from_stage": from_stage.value,
        "to_stage": to_stage.value,
        "trigger": trigger,
        "gate_decision": gate_decision,
        "triggered_by": triggered_by,
        "notes": notes,
        "approver": approver,
        "approved_at": datetime.now(UTC) if approver else None,
    }

    await stage_transition_repo.create(db, transition_data)

    # Opportunity 단계 업데이트
    opp.current_stage = to_stage


async def _check_pending_approval(
    db: AsyncSession,
    opportunity_id: str,
    target_stage: str,
):
    """대기 중인 승인 요청 확인"""
    approvals = await approval_request_repo.get_by_opportunity_id(db, opportunity_id)
    for a in approvals:
        if a.status == ApprovalStatus.PENDING and a.target_stage == target_stage:
            return a
    return None


async def _process_approval_decision(
    db: AsyncSession,
    request_id: str,
    data: ApprovalDecisionRequest,
    decision: str,
):
    """승인/거부 처리"""
    approval = await approval_request_repo.get_by_id(db, request_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending. Current status: {approval.status.value}",
        )

    # 응답 기록 추가
    responses = approval.responses or []
    responses.append(
        {
            "user_id": data.responded_by,
            "decision": decision,
            "responded_at": datetime.now(UTC).isoformat(),
            "comments": data.comments,
        }
    )
    approval.responses = responses

    # 상태 업데이트
    if decision == "APPROVED":
        approval.status = ApprovalStatus.APPROVED
        approval.completed_at = datetime.now(UTC)
        approval.completed_by = data.responded_by

        # 승인된 경우 단계 전환 수행
        opp = approval.opportunity
        if opp:
            target_stage = OpportunityStage(approval.target_stage)
            await _perform_transition(
                db,
                opp,
                opp.current_stage,
                target_stage,
                TransitionTrigger.GATE,
                data.responded_by,
                data.comments,
                GateDecision.GO,
                data.responded_by,
            )

            # Gate 판정 기록
            gate_key = f"gate_{approval.approval_type.value.lower()}"
            gate_decisions = opp.gate_decisions or {}
            gate_decisions[gate_key] = {
                "decision": "GO",
                "approver": data.responded_by,
                "approved_at": datetime.now(UTC).isoformat(),
                "comments": data.comments,
            }
            opp.gate_decisions = gate_decisions

    else:
        approval.status = ApprovalStatus.REJECTED
        approval.completed_at = datetime.now(UTC)
        approval.completed_by = data.responded_by

    approval.final_comments = data.comments
    await db.commit()

    return {
        "status": "success",
        "request_id": request_id,
        "decision": decision,
        "responded_by": data.responded_by,
        "message": f"승인 요청이 {decision}되었습니다.",
    }
