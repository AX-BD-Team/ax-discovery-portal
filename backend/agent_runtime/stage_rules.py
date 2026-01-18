"""
Stage Rules

단계별 전환 규칙 및 HITL 요구사항 정의
"""

from dataclasses import dataclass, field
from enum import Enum

from backend.database.models.opportunity import OpportunityStage


class ApprovalRequirement(str, Enum):
    """승인 요구사항 유형"""

    NONE = "NONE"  # 승인 불필요 (자동 전환)
    OPTIONAL = "OPTIONAL"  # 선택적 승인
    REQUIRED = "REQUIRED"  # 필수 승인 (HITL)


@dataclass
class StageRule:
    """단계 전환 규칙"""

    stage: OpportunityStage
    label: str
    description: str

    # 승인 요구사항
    approval: ApprovalRequirement = ApprovalRequirement.NONE

    # 필수 승인자 역할
    required_approvers: list[str] = field(default_factory=list)

    # 선택적 승인자 역할
    optional_approvers: list[str] = field(default_factory=list)

    # 진입 조건 (필수 아티팩트)
    required_artifacts: list[str] = field(default_factory=list)

    # 예상 체류 기간 (일)
    expected_duration_days: int | None = None

    # SLA (일)
    sla_days: int | None = None


# 단계별 규칙 정의
STAGE_RULES: dict[OpportunityStage, StageRule] = {
    OpportunityStage.DISCOVERY: StageRule(
        stage=OpportunityStage.DISCOVERY,
        label="01 발굴",
        description="Activity 생성, 초기 기회 포착",
        approval=ApprovalRequirement.NONE,
        expected_duration_days=7,
    ),
    OpportunityStage.IDEA_CARD: StageRule(
        stage=OpportunityStage.IDEA_CARD,
        label="02 수집 (아이디어카드)",
        description="Signal 등록, 기본 정보 수집",
        approval=ApprovalRequirement.NONE,
        required_artifacts=["signal_id"],
        expected_duration_days=5,
    ),
    OpportunityStage.GATE1_SELECTION: StageRule(
        stage=OpportunityStage.GATE1_SELECTION,
        label="03 선정 (Gate1)",
        description="Scorecard 평가 후 GO/NO_GO 판정",
        approval=ApprovalRequirement.REQUIRED,
        required_approvers=["BD_OWNER"],
        required_artifacts=["signal_id", "scorecard_id"],
        sla_days=7,
    ),
    OpportunityStage.MOCKUP: StageRule(
        stage=OpportunityStage.MOCKUP,
        label="04 형상화 (Mock-up)",
        description="Brief 초안 작성, 솔루션 가설 수립",
        approval=ApprovalRequirement.NONE,
        required_artifacts=["brief_id"],
        expected_duration_days=14,
    ),
    OpportunityStage.GATE2_VALIDATION: StageRule(
        stage=OpportunityStage.GATE2_VALIDATION,
        label="05 사용자검증 (Gate2)",
        description="Brief 승인, 사용자 검증 완료",
        approval=ApprovalRequirement.REQUIRED,
        required_approvers=["BD_OWNER"],
        optional_approvers=["DATA_TEAM", "SECURITY_TEAM"],
        required_artifacts=["brief_id"],
        sla_days=14,
    ),
    OpportunityStage.BIZ_PLANNING: StageRule(
        stage=OpportunityStage.BIZ_PLANNING,
        label="06 사업기획·임원보고",
        description="사업 기획서 작성, 임원 보고 및 승인",
        approval=ApprovalRequirement.REQUIRED,
        required_approvers=["BD_OWNER", "EXECUTIVE"],
        expected_duration_days=21,
    ),
    OpportunityStage.PILOT_POC: StageRule(
        stage=OpportunityStage.PILOT_POC,
        label="07 파일럿/PoC",
        description="파일럿 프로젝트 진행",
        approval=ApprovalRequirement.OPTIONAL,
        optional_approvers=["BD_OWNER"],
        expected_duration_days=30,
    ),
    OpportunityStage.PRE_PROPOSAL: StageRule(
        stage=OpportunityStage.PRE_PROPOSAL,
        label="08 선제안 (Pre-컨설팅)",
        description="선제안 문서 작성 및 고객 제안",
        approval=ApprovalRequirement.REQUIRED,
        required_approvers=["BD_OWNER"],
        expected_duration_days=14,
    ),
    OpportunityStage.HANDOFF: StageRule(
        stage=OpportunityStage.HANDOFF,
        label="09 실제안 (인계)",
        description="영업팀으로 인계",
        approval=ApprovalRequirement.REQUIRED,
        required_approvers=["BD_OWNER", "RECEIVING_TEAM"],
        sla_days=7,
    ),
    OpportunityStage.HOLD: StageRule(
        stage=OpportunityStage.HOLD,
        label="보류",
        description="일시적으로 진행 보류",
        approval=ApprovalRequirement.NONE,
    ),
    OpportunityStage.DROP: StageRule(
        stage=OpportunityStage.DROP,
        label="중단",
        description="기회 추진 중단",
        approval=ApprovalRequirement.NONE,
    ),
}


def get_stage_rule(stage: OpportunityStage) -> StageRule | None:
    """단계별 규칙 조회"""
    return STAGE_RULES.get(stage)


def is_hitl_required(stage: OpportunityStage) -> bool:
    """HITL 필수 여부 확인"""
    rule = get_stage_rule(stage)
    return rule is not None and rule.approval == ApprovalRequirement.REQUIRED


def get_required_approvers(stage: OpportunityStage) -> list[str]:
    """필수 승인자 역할 목록 조회"""
    rule = get_stage_rule(stage)
    return rule.required_approvers if rule else []


def get_required_artifacts(stage: OpportunityStage) -> list[str]:
    """필수 아티팩트 목록 조회"""
    rule = get_stage_rule(stage)
    return rule.required_artifacts if rule else []


def can_transition(
    from_stage: OpportunityStage,
    to_stage: OpportunityStage,
) -> tuple[bool, str | None]:
    """
    단계 전환 가능 여부 확인

    Returns:
        (bool, str | None): (전환 가능 여부, 불가 사유)
    """
    # HOLD/DROP으로의 전환은 항상 가능
    if to_stage in (OpportunityStage.HOLD, OpportunityStage.DROP):
        return True, None

    # HOLD에서 복귀는 특별 처리
    if from_stage == OpportunityStage.HOLD:
        return True, None

    # DROP에서는 복귀 불가
    if from_stage == OpportunityStage.DROP:
        return False, "중단된 기회는 복귀할 수 없습니다."

    # 일반적인 순방향 전환 확인
    stage_order = [
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

    try:
        from_idx = stage_order.index(from_stage)
        to_idx = stage_order.index(to_stage)

        # 바로 다음 단계로만 전환 가능 (스킵 불가)
        if to_idx == from_idx + 1:
            return True, None
        elif to_idx > from_idx:
            return False, f"단계를 건너뛸 수 없습니다. 다음 단계: {stage_order[from_idx + 1].value}"
        else:
            return False, "이전 단계로 전환할 수 없습니다."

    except ValueError:
        return False, "유효하지 않은 단계입니다."


def validate_artifacts(
    target_stage: OpportunityStage,
    artifacts: dict,
) -> tuple[bool, list[str]]:
    """
    필수 아티팩트 검증

    Returns:
        (bool, list[str]): (유효 여부, 누락된 아티팩트 목록)
    """
    required = get_required_artifacts(target_stage)
    missing = [a for a in required if not artifacts.get(a)]
    return len(missing) == 0, missing


# 단계별 메타데이터 (UI용)
STAGE_METADATA = [
    {"stage": "01_DISCOVERY", "label": "발굴", "color": "#6B7280", "icon": "search"},
    {"stage": "02_IDEA_CARD", "label": "수집", "color": "#3B82F6", "icon": "lightbulb"},
    {"stage": "03_GATE1", "label": "선정", "color": "#F59E0B", "icon": "gate"},
    {"stage": "04_MOCKUP", "label": "형상화", "color": "#8B5CF6", "icon": "puzzle"},
    {"stage": "05_GATE2", "label": "검증", "color": "#EF4444", "icon": "check"},
    {"stage": "06_BIZ_PLANNING", "label": "기획", "color": "#10B981", "icon": "document"},
    {"stage": "07_PILOT", "label": "파일럿", "color": "#06B6D4", "icon": "rocket"},
    {"stage": "08_PRE_PROPOSAL", "label": "선제안", "color": "#EC4899", "icon": "send"},
    {"stage": "09_HANDOFF", "label": "인계", "color": "#14B8A6", "icon": "handshake"},
    {"stage": "HOLD", "label": "보류", "color": "#9CA3AF", "icon": "pause"},
    {"stage": "DROP", "label": "중단", "color": "#DC2626", "icon": "stop"},
]
