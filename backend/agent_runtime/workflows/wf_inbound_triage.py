"""
WF-04: Inbound Triage

Intake Form 제출 → 중복 체크 → Scorecard 초안 → Brief 승격 (48h SLA)

트리거:
- Intake Form 제출
- /ax:triage 커맨드

흐름:
1. Signal 생성 (Intake Form → Signal)
2. 중복 체크 (기존 Signal과 유사도 비교)
3. Play 라우팅 (키워드 기반 자동 배정)
4. Scorecard 초안 생성 (AI 기반 예비 평가)
5. SLA 추적 (48시간 내 처리)

SLA:
- URGENT: 24시간
- NORMAL: 48시간
- LOW: 72시간
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


# ============================================================
# Enums & Constants
# ============================================================


class Urgency(str, Enum):
    """긴급도"""

    URGENT = "URGENT"  # 24h SLA
    NORMAL = "NORMAL"  # 48h SLA
    LOW = "LOW"  # 72h SLA


class TriageAction(str, Enum):
    """Triage 후 다음 액션"""

    CREATE_BRIEF = "CREATE_BRIEF"  # GO → Brief 생성
    REVIEW_AND_ENHANCE = "REVIEW_AND_ENHANCE"  # PIVOT → 추가 조사
    SCHEDULE_FOLLOW_UP = "SCHEDULE_FOLLOW_UP"  # HOLD → 후속 일정
    ARCHIVE = "ARCHIVE"  # NO_GO → 아카이브
    MERGE_OR_CLOSE = "MERGE_OR_CLOSE"  # 중복 → 병합/종료


# SLA 시간 (시간 단위)
SLA_HOURS = {
    Urgency.URGENT: 24,
    Urgency.NORMAL: 48,
    Urgency.LOW: 72,
}

# Play 라우팅 규칙 (키워드 → Play ID)
PLAY_ROUTING_RULES: list[dict[str, Any]] = [
    # KT 관련
    {"keywords": ["kt", "케이티", "콜센터", "고객센터", "상담"], "play_id": "KT_Sales_S01"},
    {"keywords": ["데이터", "분석", "ai", "ml", "머신러닝"], "play_id": "KT_Desk_D01_AI"},
    {"keywords": ["클라우드", "인프라", "서버"], "play_id": "KT_Sales_S02_Cloud"},
    # 금융 관련
    {"keywords": ["금융", "은행", "보험", "증권", "카드"], "play_id": "GRP_Sales_S01_Finance"},
    # 통신 관련
    {"keywords": ["통신", "네트워크", "5g", "iot"], "play_id": "KT_Desk_D02_Telecom"},
    # 기본값
    {"keywords": [], "play_id": "KT_Inbound_I01"},
]


# ============================================================
# Data Classes
# ============================================================


@dataclass
class InboundInput:
    """Intake Form 입력"""

    title: str
    description: str
    customer_segment: str | None = None
    pain: str | None = None
    submitter: str | None = None
    submitter_email: str | None = None
    urgency: str = "NORMAL"
    source: str = "KT"  # 원천 (KT, 그룹사, 대외)
    contact_info: str | None = None  # 연락처


@dataclass
class DuplicateCheckResult:
    """중복 체크 결과"""

    is_duplicate: bool
    duplicate_of: str | None = None
    similarity_score: float = 0.0
    similar_signals: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ScorecardDraft:
    """Scorecard 초안"""

    scorecard_id: str
    signal_id: str
    total_score: int
    dimension_scores: dict[str, int]
    red_flags: list[str]
    decision: str
    next_step: str
    rationale: str
    is_draft: bool = True


@dataclass
class InboundOutput:
    """Inbound Triage 출력"""

    signal_id: str
    is_duplicate: bool
    duplicate_of: str | None
    scorecard: dict[str, Any] | None
    next_action: str
    sla_deadline: str
    play_id: str
    summary: dict[str, Any] = field(default_factory=dict)


# ============================================================
# 유틸리티 함수
# ============================================================


def calculate_text_similarity(text1: str, text2: str) -> float:
    """간단한 텍스트 유사도 계산 (Jaccard 유사도)

    실제 구현에서는 임베딩 기반 유사도 사용 권장
    """
    if not text1 or not text2:
        return 0.0

    # 소문자 변환 및 단어 분리
    words1 = set(re.findall(r"\w+", text1.lower()))
    words2 = set(re.findall(r"\w+", text2.lower()))

    if not words1 or not words2:
        return 0.0

    # Jaccard 유사도
    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0


def route_to_play(title: str, description: str, customer_segment: str | None) -> str:
    """키워드 기반 Play 라우팅"""
    # 모든 텍스트를 합쳐서 검색
    combined_text = f"{title} {description} {customer_segment or ''}".lower()

    for rule in PLAY_ROUTING_RULES:
        if not rule["keywords"]:
            continue
        if any(keyword in combined_text for keyword in rule["keywords"]):
            return rule["play_id"]

    # 기본값
    return "KT_Inbound_I01"


def calculate_sla_deadline(urgency: str) -> datetime:
    """SLA 마감 시간 계산"""
    try:
        urgency_enum = Urgency(urgency)
    except ValueError:
        urgency_enum = Urgency.NORMAL

    hours = SLA_HOURS[urgency_enum]
    return datetime.now(UTC) + timedelta(hours=hours)


# ============================================================
# Scorecard 초안 생성 로직
# ============================================================


def create_scorecard_draft_from_signal(signal: dict[str, Any]) -> ScorecardDraft:
    """Signal로부터 Scorecard 초안 생성

    WF-02의 평가 로직을 재사용하되, is_draft=True로 표시
    """
    from backend.agent_runtime.workflows.wf_interview_to_brief import (
        detect_red_flags,
        evaluate_dimension_score,
        get_recommendation,
    )

    scorecard_id = f"SCR-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M%S')}"

    # 각 차원 점수 계산
    dimensions = [
        "problem_severity",
        "willingness_to_pay",
        "data_availability",
        "feasibility",
        "strategic_fit",
    ]

    dimension_scores = {}
    for dim in dimensions:
        dimension_scores[dim] = evaluate_dimension_score(dim, signal)

    total_score = sum(dimension_scores.values())

    # Red Flag 탐지
    red_flags = detect_red_flags(signal)

    # Recommendation 도출
    recommendation = get_recommendation(total_score, red_flags)

    return ScorecardDraft(
        scorecard_id=scorecard_id,
        signal_id=signal["signal_id"],
        total_score=total_score,
        dimension_scores=dimension_scores,
        red_flags=red_flags,
        decision=recommendation["decision"],
        next_step=recommendation["next_step"],
        rationale=recommendation["rationale"],
        is_draft=True,
    )


def determine_next_action(decision: str, is_duplicate: bool) -> str:
    """다음 액션 결정"""
    if is_duplicate:
        return TriageAction.MERGE_OR_CLOSE.value

    action_map = {
        "GO": TriageAction.CREATE_BRIEF.value,
        "PIVOT": TriageAction.REVIEW_AND_ENHANCE.value,
        "HOLD": TriageAction.SCHEDULE_FOLLOW_UP.value,
        "NO_GO": TriageAction.ARCHIVE.value,
    }

    return action_map.get(decision, TriageAction.REVIEW_AND_ENHANCE.value)


# ============================================================
# 메인 파이프라인
# ============================================================


class InboundTriagePipeline:
    """
    WF-04: Inbound Triage

    트리거: Intake Form 제출
    SLA: 48시간 내 처리
    """

    # 단계 정의
    STEPS = [
        {"id": "SIGNAL_CREATION", "label": "Signal 생성"},
        {"id": "DUPLICATE_CHECK", "label": "중복 체크"},
        {"id": "PLAY_ROUTING", "label": "Play 라우팅"},
        {"id": "SCORECARD_DRAFT", "label": "Scorecard 초안"},
        {"id": "SLA_TRACKING", "label": "SLA 설정"},
    ]

    def __init__(self):
        self.logger = logger.bind(workflow="WF-04")

    async def run(self, input_data: InboundInput) -> InboundOutput:
        """파이프라인 실행"""
        self.logger.info(
            "Starting Inbound Triage",
            title=input_data.title,
            urgency=input_data.urgency,
        )

        # 1. Play 라우팅 (Signal 생성 전 결정)
        play_id = route_to_play(
            input_data.title,
            input_data.description,
            input_data.customer_segment,
        )

        # 2. Signal 생성
        signal = await self._create_signal(input_data, play_id)
        signal_id = signal["signal_id"]

        # 3. 중복 체크
        duplicate_result = await self._check_duplicate(signal)

        if duplicate_result.is_duplicate:
            sla_deadline = calculate_sla_deadline(input_data.urgency)

            return InboundOutput(
                signal_id=signal_id,
                is_duplicate=True,
                duplicate_of=duplicate_result.duplicate_of,
                scorecard=None,
                next_action=TriageAction.MERGE_OR_CLOSE.value,
                sla_deadline=sla_deadline.isoformat(),
                play_id=play_id,
                summary={
                    "status": "duplicate_detected",
                    "similarity_score": duplicate_result.similarity_score,
                    "similar_signals": duplicate_result.similar_signals,
                },
            )

        # 4. Scorecard 초안 생성
        scorecard_draft = create_scorecard_draft_from_signal(signal)

        # 5. 다음 액션 결정
        next_action = determine_next_action(scorecard_draft.decision, False)

        # 6. SLA 계산
        sla_deadline = calculate_sla_deadline(input_data.urgency)

        self.logger.info(
            "Inbound Triage completed",
            signal_id=signal_id,
            decision=scorecard_draft.decision,
            next_action=next_action,
        )

        return InboundOutput(
            signal_id=signal_id,
            is_duplicate=False,
            duplicate_of=None,
            scorecard={
                "scorecard_id": scorecard_draft.scorecard_id,
                "signal_id": scorecard_draft.signal_id,
                "total_score": scorecard_draft.total_score,
                "dimension_scores": scorecard_draft.dimension_scores,
                "red_flags": scorecard_draft.red_flags,
                "recommendation": {
                    "decision": scorecard_draft.decision,
                    "next_step": scorecard_draft.next_step,
                    "rationale": scorecard_draft.rationale,
                },
                "is_draft": True,
                "scored_at": datetime.now(UTC).isoformat(),
            },
            next_action=next_action,
            sla_deadline=sla_deadline.isoformat(),
            play_id=play_id,
            summary={
                "status": "triage_completed",
                "total_score": scorecard_draft.total_score,
                "decision": scorecard_draft.decision,
            },
        )

    async def _create_signal(
        self,
        input_data: InboundInput,
        play_id: str,
    ) -> dict[str, Any]:
        """Signal 생성"""
        signal_id = f"SIG-{datetime.now().year}-INB{datetime.now().strftime('%m%d%H%M')}"

        signal = {
            "signal_id": signal_id,
            "title": input_data.title,
            "source": input_data.source,
            "channel": "인바운드",
            "play_id": play_id,
            "customer_segment": input_data.customer_segment,
            "pain": input_data.pain or input_data.description,
            "evidence": [
                {
                    "type": "intake_form",
                    "title": "Intake Form 제출",
                    "url": "",
                    "note": f"제출자: {input_data.submitter or 'N/A'}",
                }
            ],
            "kpi_hypothesis": [],
            "tags": ["inbound", input_data.urgency.lower()],
            "status": "NEW",
            "owner": input_data.submitter,
            "submitter_email": input_data.submitter_email,
            "urgency": input_data.urgency,
            "created_at": datetime.now(UTC).isoformat(),
        }

        self.logger.info("Signal created", signal_id=signal_id, play_id=play_id)
        return signal

    async def _check_duplicate(
        self,
        signal: dict[str, Any],
    ) -> DuplicateCheckResult:
        """중복 Signal 체크

        현재는 메모리 내 비교, DB 연동 시 실제 쿼리로 대체
        """
        # TODO: DB에서 최근 30일 Signal 조회 후 유사도 비교
        # 임시로 중복 없음 반환

        self.logger.info("Duplicate check completed", is_duplicate=False)

        return DuplicateCheckResult(
            is_duplicate=False,
            duplicate_of=None,
            similarity_score=0.0,
            similar_signals=[],
        )


# ============================================================
# AG-UI 이벤트 발행 버전
# ============================================================


class InboundTriagePipelineWithEvents(InboundTriagePipeline):
    """
    WF-04: Inbound Triage with AG-UI Events

    실시간 이벤트 발행을 포함한 인바운드 Triage 파이프라인
    """

    def __init__(self, emitter: "WorkflowEventEmitter"):
        super().__init__()
        self.emitter = emitter
        self.logger = logger.bind(workflow="WF-04", with_events=True)

    async def run(self, input_data: InboundInput) -> InboundOutput:
        """워크플로 실행 (이벤트 발행 포함)"""
        self.logger.info(
            "Starting Inbound Triage with events",
            title=input_data.title,
        )

        # 실행 시작 이벤트
        await self.emitter.emit_run_started(
            workflow_id="WF-04",
            input_data={
                "title": input_data.title,
                "urgency": input_data.urgency,
                "source": input_data.source,
                "submitter": input_data.submitter,
            },
            steps=self.STEPS,
        )

        try:
            # Step 1: Signal 생성
            await self.emitter.emit_step_started(
                step_id="SIGNAL_CREATION",
                step_index=0,
                step_label="Signal 생성",
                message="Intake Form에서 Signal을 생성하고 있습니다...",
            )

            # Play 라우팅 먼저 수행
            play_id = route_to_play(
                input_data.title,
                input_data.description,
                input_data.customer_segment,
            )

            signal = await self._create_signal(input_data, play_id)
            signal_id = signal["signal_id"]

            await self.emitter.emit_surface(
                surface_id=f"signal-{signal_id}",
                surface={
                    "id": f"signal-{signal_id}",
                    "type": "signal_created",
                    "title": f"Signal: {signal['title']}",
                    "signal": {
                        "signal_id": signal_id,
                        "title": signal["title"],
                        "pain": signal["pain"],
                        "channel": signal["channel"],
                        "play_id": play_id,
                    },
                },
            )

            await self.emitter.emit_step_finished(
                step_id="SIGNAL_CREATION",
                step_index=0,
                result={"signal_id": signal_id},
            )

            # Step 2: 중복 체크
            await self.emitter.emit_step_started(
                step_id="DUPLICATE_CHECK",
                step_index=1,
                step_label="중복 체크",
                message="기존 Signal과 유사도를 비교하고 있습니다...",
            )

            duplicate_result = await self._check_duplicate(signal)

            if duplicate_result.is_duplicate:
                await self.emitter.emit_surface(
                    surface_id=f"duplicate-{signal_id}",
                    surface={
                        "id": f"duplicate-{signal_id}",
                        "type": "duplicate_detected",
                        "title": "중복 Signal 감지",
                        "duplicate": {
                            "original_id": duplicate_result.duplicate_of,
                            "similarity_score": duplicate_result.similarity_score,
                        },
                    },
                )

            await self.emitter.emit_step_finished(
                step_id="DUPLICATE_CHECK",
                step_index=1,
                result={
                    "is_duplicate": duplicate_result.is_duplicate,
                    "similarity_score": duplicate_result.similarity_score,
                },
            )

            if duplicate_result.is_duplicate:
                # 중복인 경우 조기 종료
                sla_deadline = calculate_sla_deadline(input_data.urgency)

                result = InboundOutput(
                    signal_id=signal_id,
                    is_duplicate=True,
                    duplicate_of=duplicate_result.duplicate_of,
                    scorecard=None,
                    next_action=TriageAction.MERGE_OR_CLOSE.value,
                    sla_deadline=sla_deadline.isoformat(),
                    play_id=play_id,
                    summary={
                        "status": "duplicate_detected",
                        "similarity_score": duplicate_result.similarity_score,
                    },
                )

                await self.emitter.emit_run_finished(result=result.summary)
                return result

            # Step 3: Play 라우팅
            await self.emitter.emit_step_started(
                step_id="PLAY_ROUTING",
                step_index=2,
                step_label="Play 라우팅",
                message="적합한 Play를 자동 배정하고 있습니다...",
            )

            await self.emitter.emit_surface(
                surface_id=f"routing-{signal_id}",
                surface={
                    "id": f"routing-{signal_id}",
                    "type": "play_routing",
                    "title": "Play 라우팅 완료",
                    "routing": {
                        "play_id": play_id,
                        "signal_id": signal_id,
                    },
                },
            )

            await self.emitter.emit_step_finished(
                step_id="PLAY_ROUTING",
                step_index=2,
                result={"play_id": play_id},
            )

            # Step 4: Scorecard 초안
            await self.emitter.emit_step_started(
                step_id="SCORECARD_DRAFT",
                step_index=3,
                step_label="Scorecard 초안",
                message="AI 기반 예비 평가를 진행하고 있습니다...",
            )

            scorecard_draft = create_scorecard_draft_from_signal(signal)

            await self.emitter.emit_surface(
                surface_id=f"scorecard-{scorecard_draft.scorecard_id}",
                surface={
                    "id": f"scorecard-{scorecard_draft.scorecard_id}",
                    "type": "scorecard_draft",
                    "title": "Scorecard 초안",
                    "scorecard": {
                        "scorecard_id": scorecard_draft.scorecard_id,
                        "signal_id": signal_id,
                        "total_score": scorecard_draft.total_score,
                        "dimension_scores": scorecard_draft.dimension_scores,
                        "decision": scorecard_draft.decision,
                        "is_draft": True,
                    },
                },
            )

            await self.emitter.emit_step_finished(
                step_id="SCORECARD_DRAFT",
                step_index=3,
                result={
                    "total_score": scorecard_draft.total_score,
                    "decision": scorecard_draft.decision,
                },
            )

            # Step 5: SLA 설정
            await self.emitter.emit_step_started(
                step_id="SLA_TRACKING",
                step_index=4,
                step_label="SLA 설정",
                message=f"{input_data.urgency} 긴급도에 따른 SLA를 설정합니다...",
            )

            sla_deadline = calculate_sla_deadline(input_data.urgency)
            next_action = determine_next_action(scorecard_draft.decision, False)

            await self.emitter.emit_surface(
                surface_id=f"sla-{signal_id}",
                surface={
                    "id": f"sla-{signal_id}",
                    "type": "sla_set",
                    "title": "SLA 설정 완료",
                    "sla": {
                        "urgency": input_data.urgency,
                        "deadline": sla_deadline.isoformat(),
                        "next_action": next_action,
                    },
                },
            )

            await self.emitter.emit_step_finished(
                step_id="SLA_TRACKING",
                step_index=4,
                result={
                    "sla_deadline": sla_deadline.isoformat(),
                    "next_action": next_action,
                },
            )

            # 결과 생성
            result = InboundOutput(
                signal_id=signal_id,
                is_duplicate=False,
                duplicate_of=None,
                scorecard={
                    "scorecard_id": scorecard_draft.scorecard_id,
                    "signal_id": scorecard_draft.signal_id,
                    "total_score": scorecard_draft.total_score,
                    "dimension_scores": scorecard_draft.dimension_scores,
                    "red_flags": scorecard_draft.red_flags,
                    "recommendation": {
                        "decision": scorecard_draft.decision,
                        "next_step": scorecard_draft.next_step,
                        "rationale": scorecard_draft.rationale,
                    },
                    "is_draft": True,
                    "scored_at": datetime.now(UTC).isoformat(),
                },
                next_action=next_action,
                sla_deadline=sla_deadline.isoformat(),
                play_id=play_id,
                summary={
                    "status": "triage_completed",
                    "total_score": scorecard_draft.total_score,
                    "decision": scorecard_draft.decision,
                    "next_action": next_action,
                },
            )

            # 실행 완료 이벤트
            await self.emitter.emit_run_finished(result=result.summary)

            self.logger.info(
                "Inbound Triage with events completed",
                signal_id=signal_id,
                decision=scorecard_draft.decision,
            )

            return result

        except Exception as e:
            self.logger.error("Pipeline error", error=str(e))
            await self.emitter.emit_run_error(str(e), recoverable=False)
            raise


# ============================================================
# DB 연동 버전
# ============================================================


class InboundTriagePipelineWithDB(InboundTriagePipelineWithEvents):
    """
    WF-04: Inbound Triage with DB Integration

    데이터베이스 연동을 포함한 완전한 파이프라인
    """

    def __init__(self, emitter: "WorkflowEventEmitter", db: "AsyncSession"):
        super().__init__(emitter)
        self.db = db
        self.logger = logger.bind(workflow="WF-04", with_db=True)

    async def _check_duplicate(
        self,
        signal: dict[str, Any],
    ) -> DuplicateCheckResult:
        """DB 기반 중복 체크"""

        from backend.database.repositories.signal import signal_repo

        # 같은 Play ID의 Signal 조회 (최근 데이터 기반)
        items, _ = await signal_repo.get_multi_filtered(
            self.db,
            channel="인바운드",
            skip=0,
            limit=100,
        )

        # 유사도 비교
        similar_signals = []
        max_similarity = 0.0
        most_similar_id = None

        title_to_check = signal.get("title", "")
        pain_to_check = signal.get("pain", "")

        for existing in items:
            # 제목 유사도
            title_sim = calculate_text_similarity(
                title_to_check,
                existing.title,
            )
            # Pain 유사도
            pain_sim = calculate_text_similarity(
                pain_to_check,
                existing.pain,
            )

            # 가중 평균
            avg_sim = (title_sim * 0.4) + (pain_sim * 0.6)

            if avg_sim > 0.5:  # 50% 이상 유사
                similar_signals.append(
                    {
                        "signal_id": existing.signal_id,
                        "title": existing.title,
                        "similarity": avg_sim,
                    }
                )

            if avg_sim > max_similarity:
                max_similarity = avg_sim
                most_similar_id = existing.signal_id

        # 70% 이상 유사하면 중복으로 판단
        is_duplicate = max_similarity >= 0.7

        self.logger.info(
            "DB duplicate check completed",
            is_duplicate=is_duplicate,
            max_similarity=max_similarity,
            similar_count=len(similar_signals),
        )

        return DuplicateCheckResult(
            is_duplicate=is_duplicate,
            duplicate_of=most_similar_id if is_duplicate else None,
            similarity_score=max_similarity,
            similar_signals=similar_signals[:5],  # 상위 5개만
        )

    async def save_to_db(
        self,
        signal: dict[str, Any],
        scorecard: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """결과를 DB에 저장 (Signal + Scorecard + Opportunity)"""
        from backend.database.models.opportunity import OpportunityStage
        from backend.database.models.signal import SignalStatus
        from backend.database.repositories.opportunity import opportunity_repo
        from backend.database.repositories.scorecard import scorecard_repo
        from backend.database.repositories.signal import signal_repo

        saved: dict[str, str | None] = {
            "signal_id": None,
            "scorecard_id": None,
            "opportunity_id": None,
        }

        # Signal 저장
        try:
            signal_id = await signal_repo.generate_signal_id(self.db)
            signal["signal_id"] = signal_id
            signal["status"] = SignalStatus.NEW

            db_signal = await signal_repo.create(self.db, signal)
            saved["signal_id"] = db_signal.signal_id

            self.logger.info("Signal saved", signal_id=signal_id)
        except Exception as e:
            self.logger.error("Failed to save signal", error=str(e))

        # Scorecard 저장 (초안)
        if scorecard and saved["signal_id"]:
            try:
                scorecard_id = await scorecard_repo.generate_scorecard_id(self.db)
                scorecard["scorecard_id"] = scorecard_id
                scorecard["signal_id"] = saved["signal_id"]

                db_scorecard = await scorecard_repo.create(self.db, scorecard)
                saved["scorecard_id"] = db_scorecard.scorecard_id

                self.logger.info("Scorecard draft saved", scorecard_id=scorecard_id)
            except Exception as e:
                self.logger.error("Failed to save scorecard", error=str(e))

        # Opportunity 생성 (Signal과 연결)
        if saved["signal_id"]:
            try:
                opportunity_id = await opportunity_repo.generate_opportunity_id(self.db)

                # Scorecard 점수에 따라 초기 단계 결정
                initial_stage = OpportunityStage.DISCOVERY
                if scorecard:
                    total_score = scorecard.get("total_score", 0)
                    decision = scorecard.get("recommendation", {}).get("decision", "")
                    # GO 판정이고 점수가 70 이상이면 IDEA_CARD 단계로 시작
                    if decision == "GO" and total_score >= 70:
                        initial_stage = OpportunityStage.IDEA_CARD

                opp_data = {
                    "opportunity_id": opportunity_id,
                    "title": signal.get("title", "Untitled Opportunity"),
                    "description": signal.get("pain", ""),
                    "current_stage": initial_stage,
                    "signal_id": saved["signal_id"],
                    "bd_owner": signal.get("owner"),
                    "play_id": signal.get("play_id"),
                    "tags": signal.get("tags", []),
                    "stage_artifacts": {
                        "signal_id": saved["signal_id"],
                        "scorecard_id": saved["scorecard_id"],
                    },
                    "gate_decisions": {},
                }

                db_opp = await opportunity_repo.create(self.db, opp_data)
                saved["opportunity_id"] = db_opp.opportunity_id

                self.logger.info(
                    "Opportunity created",
                    opportunity_id=opportunity_id,
                    initial_stage=initial_stage.value,
                )
            except Exception as e:
                self.logger.error("Failed to create opportunity", error=str(e))

        await self.db.commit()
        return saved


# ============================================================
# 워크플로 인스턴스 및 진입점
# ============================================================

workflow = InboundTriagePipeline()


async def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """워크플로 진입점"""
    inbound_input = InboundInput(
        title=input_data["title"],
        description=input_data["description"],
        customer_segment=input_data.get("customer_segment"),
        pain=input_data.get("pain"),
        submitter=input_data.get("submitter"),
        submitter_email=input_data.get("submitter_email"),
        urgency=input_data.get("urgency", "NORMAL"),
        source=input_data.get("source", "KT"),
        contact_info=input_data.get("contact_info"),
    )

    result = await workflow.run(inbound_input)

    return {
        "signal_id": result.signal_id,
        "is_duplicate": result.is_duplicate,
        "duplicate_of": result.duplicate_of,
        "scorecard": result.scorecard,
        "next_action": result.next_action,
        "sla_deadline": result.sla_deadline,
        "play_id": result.play_id,
        "summary": result.summary,
    }


async def run_with_events(
    input_data: dict[str, Any], emitter: "WorkflowEventEmitter"
) -> dict[str, Any]:
    """이벤트 발행을 포함한 워크플로 실행"""
    inbound_input = InboundInput(
        title=input_data["title"],
        description=input_data["description"],
        customer_segment=input_data.get("customer_segment"),
        pain=input_data.get("pain"),
        submitter=input_data.get("submitter"),
        submitter_email=input_data.get("submitter_email"),
        urgency=input_data.get("urgency", "NORMAL"),
        source=input_data.get("source", "KT"),
        contact_info=input_data.get("contact_info"),
    )

    pipeline = InboundTriagePipelineWithEvents(emitter)
    result = await pipeline.run(inbound_input)

    return {
        "signal_id": result.signal_id,
        "is_duplicate": result.is_duplicate,
        "duplicate_of": result.duplicate_of,
        "scorecard": result.scorecard,
        "next_action": result.next_action,
        "sla_deadline": result.sla_deadline,
        "play_id": result.play_id,
        "summary": result.summary,
    }


# 타입 힌트를 위한 import (순환 참조 방지)
if __name__ != "__main__":
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.agent_runtime.event_manager import WorkflowEventEmitter
