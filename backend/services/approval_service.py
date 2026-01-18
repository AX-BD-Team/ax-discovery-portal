"""
ApprovalService

HITL(Human-in-the-Loop) 승인 요청 관리 서비스
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.approval_request import ApprovalRequest, ApprovalStatus, ApprovalType
from backend.database.models.opportunity import Opportunity, OpportunityStage
from backend.database.models.stage_transition import GateDecision, TransitionTrigger
from backend.database.repositories.opportunity import (
    approval_request_repo,
    opportunity_repo,
    stage_transition_repo,
)

logger = structlog.get_logger()


class ApprovalService:
    """
    HITL 승인 요청 관리 서비스

    Gate1, Gate2 등 HITL 필수 단계에서 승인 요청을 관리합니다.
    """

    # 승인 만료 시간 (기본 7일)
    DEFAULT_EXPIRY_DAYS = 7

    # 단계별 기본 승인자 역할
    STAGE_APPROVERS = {
        OpportunityStage.GATE1_SELECTION: [
            {"role": "BD_OWNER", "required": True},
        ],
        OpportunityStage.GATE2_VALIDATION: [
            {"role": "BD_OWNER", "required": True},
            {"role": "DATA_TEAM", "required": False},
            {"role": "SECURITY_TEAM", "required": False},
        ],
        OpportunityStage.BIZ_PLANNING: [
            {"role": "BD_OWNER", "required": True},
            {"role": "EXECUTIVE", "required": True},
        ],
        OpportunityStage.PRE_PROPOSAL: [
            {"role": "BD_OWNER", "required": True},
        ],
        OpportunityStage.HANDOFF: [
            {"role": "BD_OWNER", "required": True},
            {"role": "RECEIVING_TEAM", "required": True},
        ],
    }

    def __init__(self):
        self.logger = logger.bind(service="ApprovalService")

    async def request_approval(
        self,
        db: AsyncSession,
        opportunity_id: str,
        target_stage: OpportunityStage,
        requested_by: str,
        request_reason: str | None = None,
        artifacts: dict | None = None,
        custom_approvers: list[dict] | None = None,
    ) -> ApprovalRequest:
        """
        승인 요청 생성

        Args:
            db: 데이터베이스 세션
            opportunity_id: Opportunity ID
            target_stage: 목표 단계
            requested_by: 요청자
            request_reason: 요청 사유
            artifacts: 관련 아티팩트 (scorecard_id, brief_id 등)
            custom_approvers: 커스텀 승인자 목록

        Returns:
            ApprovalRequest: 생성된 승인 요청
        """
        # Opportunity 확인
        opp = await opportunity_repo.get_by_id(db, opportunity_id)
        if not opp:
            raise ValueError(f"Opportunity not found: {opportunity_id}")

        # 이미 대기 중인 승인 요청 확인
        existing_requests = await approval_request_repo.get_by_opportunity_id(db, opportunity_id)
        for req in existing_requests:
            if req.status == ApprovalStatus.PENDING and req.target_stage == target_stage.value:
                raise ValueError(f"Pending approval request already exists: {req.request_id}")

        # 승인자 목록 결정
        approvers = custom_approvers or self._get_default_approvers(target_stage, opp)

        # 승인 유형 결정
        approval_type = self._get_approval_type(target_stage)

        # 만료 시간 설정
        expires_at = datetime.now(UTC) + timedelta(days=self.DEFAULT_EXPIRY_DAYS)

        # 승인 요청 생성
        request_id = await approval_request_repo.generate_request_id(db)

        approval_data = {
            "request_id": request_id,
            "opportunity_id": opportunity_id,
            "target_stage": target_stage.value,
            "approval_type": approval_type,
            "status": ApprovalStatus.PENDING,
            "approvers": approvers,
            "requested_by": requested_by,
            "request_reason": request_reason,
            "artifacts": artifacts or {},
            "expires_at": expires_at,
            "responses": [],
        }

        approval = await approval_request_repo.create(db, approval_data)

        self.logger.info(
            "Approval request created",
            request_id=request_id,
            opportunity_id=opportunity_id,
            target_stage=target_stage.value,
            approval_type=approval_type.value,
        )

        return approval

    async def process_decision(
        self,
        db: AsyncSession,
        request_id: str,
        decision: str,
        responded_by: str,
        comments: str | None = None,
    ) -> dict:
        """
        승인/거부 결정 처리

        Args:
            db: 데이터베이스 세션
            request_id: 승인 요청 ID
            decision: "APPROVED" 또는 "REJECTED"
            responded_by: 응답자
            comments: 코멘트

        Returns:
            dict: 처리 결과
        """
        approval = await approval_request_repo.get_by_id(db, request_id)
        if not approval:
            raise ValueError(f"Approval request not found: {request_id}")

        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request is not pending. Current status: {approval.status.value}")

        # 응답 기록 추가
        responses = approval.responses or []
        responses.append(
            {
                "user_id": responded_by,
                "decision": decision,
                "responded_at": datetime.now(UTC).isoformat(),
                "comments": comments,
            }
        )
        approval.responses = responses

        # 결과 처리
        result = {
            "request_id": request_id,
            "decision": decision,
            "responded_by": responded_by,
        }

        if decision == "APPROVED":
            # 모든 필수 승인이 완료되었는지 확인
            if self._check_all_required_approvals(approval):
                approval.status = ApprovalStatus.APPROVED
                approval.completed_at = datetime.now(UTC)
                approval.completed_by = responded_by
                approval.final_comments = comments

                # 단계 전환 수행
                await self._perform_stage_transition(
                    db,
                    approval,
                    responded_by,
                    comments,
                )

                result["status"] = "completed"
                result["message"] = "승인이 완료되었습니다. 단계가 전환되었습니다."
            else:
                result["status"] = "partial"
                result["message"] = "승인이 기록되었습니다. 추가 승인이 필요합니다."

        else:  # REJECTED
            approval.status = ApprovalStatus.REJECTED
            approval.completed_at = datetime.now(UTC)
            approval.completed_by = responded_by
            approval.final_comments = comments

            result["status"] = "rejected"
            result["message"] = "승인 요청이 거부되었습니다."

        self.logger.info(
            "Approval decision processed",
            request_id=request_id,
            decision=decision,
            responded_by=responded_by,
            final_status=approval.status.value,
        )

        return result

    async def check_expired_requests(self, db: AsyncSession) -> list[str]:
        """
        만료된 승인 요청 확인 및 처리

        Returns:
            list[str]: 만료된 요청 ID 목록
        """
        expired_ids = []

        # 모든 대기 중인 요청 조회
        pending_requests, _ = await approval_request_repo.get_pending_all(db, skip=0, limit=1000)

        now = datetime.now(UTC)
        for req in pending_requests:
            if req.expires_at and req.expires_at < now:
                req.status = ApprovalStatus.EXPIRED
                req.final_comments = "자동 만료됨"
                expired_ids.append(req.request_id)

                self.logger.warning(
                    "Approval request expired",
                    request_id=req.request_id,
                    opportunity_id=req.opportunity_id,
                )

        return expired_ids

    def _get_default_approvers(
        self,
        target_stage: OpportunityStage,
        opp: Opportunity,
    ) -> list[dict]:
        """단계별 기본 승인자 목록 반환"""
        template = self.STAGE_APPROVERS.get(target_stage, [])
        approvers = []

        for t in template:
            approver = {
                "role": t["role"],
                "required": t["required"],
            }

            # BD_OWNER의 경우 실제 담당자 ID 추가
            if t["role"] == "BD_OWNER" and opp.bd_owner:
                approver["user_id"] = opp.bd_owner

            approvers.append(approver)

        return approvers

    def _get_approval_type(self, target_stage: OpportunityStage) -> ApprovalType:
        """단계에 따른 승인 유형 반환"""
        type_map = {
            OpportunityStage.GATE1_SELECTION: ApprovalType.GATE1,
            OpportunityStage.GATE2_VALIDATION: ApprovalType.GATE2,
            OpportunityStage.BIZ_PLANNING: ApprovalType.BIZ_APPROVAL,
            OpportunityStage.PRE_PROPOSAL: ApprovalType.PRE_PROPOSAL,
            OpportunityStage.HANDOFF: ApprovalType.HANDOFF,
        }
        return type_map.get(target_stage, ApprovalType.STAGE_ADVANCE)

    def _check_all_required_approvals(self, approval: ApprovalRequest) -> bool:
        """모든 필수 승인이 완료되었는지 확인"""
        required_roles = {a["role"] for a in approval.approvers if a.get("required", False)}

        approved_by = set()
        for resp in approval.responses or []:
            if resp.get("decision") == "APPROVED":
                # 응답자의 역할 확인 (실제 구현에서는 사용자 역할 조회 필요)
                user_id = resp.get("user_id")
                # 간단한 구현: 모든 응답을 역할로 간주
                for a in approval.approvers:
                    if a.get("user_id") == user_id or a.get("role") == user_id:
                        approved_by.add(a["role"])

        # 모든 필수 역할이 승인했는지 확인
        return required_roles <= approved_by

    async def _perform_stage_transition(
        self,
        db: AsyncSession,
        approval: ApprovalRequest,
        approver: str,
        comments: str | None,
    ) -> None:
        """승인에 따른 단계 전환 수행"""
        opp = await opportunity_repo.get_by_id(db, approval.opportunity_id)
        if not opp:
            return

        target_stage = OpportunityStage(approval.target_stage)

        # 전환 이력 생성
        transition_id = await stage_transition_repo.generate_transition_id(db)
        transition_data = {
            "transition_id": transition_id,
            "opportunity_id": opp.opportunity_id,
            "from_stage": opp.current_stage.value,
            "to_stage": target_stage.value,
            "trigger": TransitionTrigger.GATE,
            "gate_decision": GateDecision.GO,
            "approver": approver,
            "approved_at": datetime.now(UTC),
            "notes": comments,
        }

        await stage_transition_repo.create(db, transition_data)

        # Opportunity 단계 업데이트
        opp.current_stage = target_stage

        # Gate 판정 기록
        gate_key = f"gate_{approval.approval_type.value.lower()}"
        gate_decisions = opp.gate_decisions or {}
        gate_decisions[gate_key] = {
            "decision": "GO",
            "approver": approver,
            "approved_at": datetime.now(UTC).isoformat(),
            "comments": comments,
        }
        opp.gate_decisions = gate_decisions

        self.logger.info(
            "Stage transition completed via approval",
            opportunity_id=opp.opportunity_id,
            from_stage=transition_data["from_stage"],
            to_stage=target_stage.value,
        )


# 싱글톤 인스턴스
approval_service = ApprovalService()
