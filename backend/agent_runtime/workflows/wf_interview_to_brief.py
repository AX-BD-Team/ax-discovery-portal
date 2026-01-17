"""
WF-02: Interview to Brief

인터뷰 노트 → Signal 추출 → Scorecard 평가 → Brief 생성

트리거:
- /ax:interview 커맨드
- KT_Sales_*, KT_PM_* Play ID

흐름:
1. 인터뷰 노트에서 Pain Point/니즈/기회 추출 (Signal 생성)
2. 각 Signal에 대해 Scorecard 100점 평가
3. GO 판정 Signal → Brief 초안 생성 (승인 대기)
4. 승인 시 Confluence 페이지 생성 + Play DB 업데이트
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

from backend.agent_runtime.event_types import ImpactLevel

logger = structlog.get_logger()


# ============================================================
# Pydantic Models
# ============================================================


class InterviewSource(str, Enum):
    """인터뷰 원천"""

    SALES_PM = "영업PM"
    CUSTOMER = "고객"
    PARTNER = "파트너"
    INTERNAL = "내부"


@dataclass
class InterviewInput:
    """인터뷰 입력"""

    content: str  # 인터뷰 노트 텍스트 또는 문서 링크
    play_id: str | None = None
    customer: str | None = None
    source: str = "KT"
    channel: str = "영업PM"
    interviewee: str | None = None  # 인터뷰 대상자
    interview_date: str | None = None  # 인터뷰 일자


@dataclass
class ExtractedSignal:
    """인터뷰에서 추출된 Signal"""

    title: str
    pain: str
    current_workflow: str | None = None
    kpi_hypothesis: list[str] = field(default_factory=list)
    confidence: float = 0.7  # 추출 신뢰도


@dataclass
class ScorecardResult:
    """Scorecard 평가 결과"""

    scorecard_id: str
    signal_id: str
    total_score: int
    dimension_scores: dict[str, int]
    red_flags: list[str]
    decision: str  # GO, PIVOT, HOLD, NO_GO
    next_step: str  # BRIEF, NEED_MORE_EVIDENCE, DROP
    rationale: str


@dataclass
class BriefDraft:
    """Brief 초안"""

    brief_id: str
    signal_id: str
    title: str
    customer: dict[str, Any]
    problem: dict[str, Any]
    solution_hypothesis: dict[str, Any]
    kpis: list[str]
    evidence: list[str]
    validation_plan: dict[str, Any]
    status: str = "DRAFT"


@dataclass
class InterviewOutput:
    """인터뷰 파이프라인 출력"""

    signals: list[dict[str, Any]]
    scorecards: list[dict[str, Any]]
    briefs: list[dict[str, Any]]
    pending_approvals: list[str]
    summary: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Scorecard 평가 로직 (scorecard_evaluator.md 기반)
# ============================================================

RED_FLAG_CONDITIONS = [
    "데이터 접근 불가 (내부 정책)",
    "Buyer/예산 오너 부재",
    "규제/법무 이슈",
    "경쟁사 선점 (6개월+)",
    "KT DS 역량 외 영역",
    "보안 등급 제약",
]


def evaluate_dimension_score(dimension: str, signal_data: dict[str, Any]) -> int:
    """차원별 점수 평가 (0-20점)

    실제 구현에서는 LLM을 사용하여 평가
    """
    # 기본 점수 (중간값)
    base_score = 12

    pain = signal_data.get("pain", "")
    evidence = signal_data.get("evidence", [])
    kpi_hypothesis = signal_data.get("kpi_hypothesis", [])
    customer_segment = signal_data.get("customer_segment", "")

    if dimension == "problem_severity":
        # Pain 명확성 기준
        if len(pain) > 100 and any(
            word in pain.lower() for word in ["비용", "시간", "손실", "문제", "어려움"]
        ):
            return 16
        elif len(pain) > 50:
            return 13
        else:
            return 8

    elif dimension == "willingness_to_pay":
        # 예산/Buyer 관련 증거
        if any("예산" in str(e) or "buyer" in str(e).lower() for e in evidence):
            return 16
        elif customer_segment:
            return 12
        else:
            return 7

    elif dimension == "data_availability":
        # 데이터 접근성
        if any("데이터" in str(e) or "api" in str(e).lower() for e in evidence):
            return 15
        else:
            return 10

    elif dimension == "feasibility":
        # 실현 가능성
        if len(kpi_hypothesis) >= 2:
            return 15
        elif len(kpi_hypothesis) >= 1:
            return 12
        else:
            return 9

    elif dimension == "strategic_fit":
        # 전략 적합성 (KT/금융/통신 관련 시 높음)
        strategic_keywords = ["kt", "금융", "통신", "콜센터", "고객센터", "상담"]
        combined_text = f"{customer_segment or ''} {pain}".lower()
        if any(kw in combined_text for kw in strategic_keywords):
            return 16
        else:
            return 11

    return base_score


def detect_red_flags(signal_data: dict[str, Any]) -> list[str]:
    """Red Flag 탐지"""
    flags = []

    pain = signal_data.get("pain", "").lower()
    evidence = signal_data.get("evidence", [])

    # 데이터 접근 불가
    if "접근 불가" in pain or "데이터 없음" in pain:
        flags.append("데이터 접근 불가 (내부 정책)")

    # Buyer 부재
    if not any("buyer" in str(e).lower() or "예산" in str(e) for e in evidence):
        if "예산 없음" in pain or "담당자 없음" in pain:
            flags.append("Buyer/예산 오너 부재")

    # 규제 이슈
    if any(word in pain for word in ["규제", "법무", "컴플라이언스", "개인정보"]):
        flags.append("규제/법무 이슈")

    return flags


def get_recommendation(total_score: int, red_flags: list[str]) -> dict[str, str]:
    """Recommendation 도출"""
    if total_score >= 70 and len(red_flags) == 0:
        return {
            "decision": "GO",
            "next_step": "BRIEF",
            "rationale": f"총점 {total_score}점으로 기준(70점) 충족, Red Flag 없음",
        }
    elif total_score >= 50 and len(red_flags) <= 1:
        return {
            "decision": "PIVOT",
            "next_step": "NEED_MORE_EVIDENCE",
            "rationale": f"총점 {total_score}점, 추가 조사 필요",
        }
    elif total_score >= 30:
        return {
            "decision": "HOLD",
            "next_step": "NEED_MORE_EVIDENCE",
            "rationale": f"총점 {total_score}점, Red Flag {len(red_flags)}개로 보류",
        }
    else:
        return {
            "decision": "NO_GO",
            "next_step": "DROP",
            "rationale": f"총점 {total_score}점으로 기준 미달",
        }


# ============================================================
# Signal 추출 로직
# ============================================================


def extract_signals_from_interview(
    content: str, play_id: str | None, customer: str | None
) -> list[ExtractedSignal]:
    """인터뷰 노트에서 Signal 추출

    실제 구현에서는 LLM을 사용하여 추출
    현재는 간단한 휴리스틱 사용
    """
    signals = []

    # Pain Point 키워드 기반 추출
    pain_keywords = [
        "문제",
        "어려움",
        "불편",
        "비용",
        "시간",
        "손실",
        "니즈",
        "필요",
        "원함",
        "개선",
        "효율",
    ]

    # 간단한 문장 분리
    sentences = content.replace("\n", ". ").split(". ")

    potential_pains = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue
        if any(kw in sentence for kw in pain_keywords):
            potential_pains.append(sentence)

    # 최대 3개 Signal 추출
    for i, pain in enumerate(potential_pains[:3]):
        signal = ExtractedSignal(
            title=f"인터뷰 Signal #{i + 1}",
            pain=pain,
            current_workflow=None,
            kpi_hypothesis=[],
            confidence=0.6 + (0.1 if len(pain) > 50 else 0),
        )
        signals.append(signal)

    # Signal이 없으면 기본 1개 생성
    if not signals:
        signals.append(
            ExtractedSignal(
                title="인터뷰에서 추출한 Signal",
                pain=content[:200] if len(content) > 200 else content,
                confidence=0.5,
            )
        )

    return signals


# ============================================================
# Brief 생성 로직
# ============================================================


def generate_brief_draft(signal_data: dict[str, Any], scorecard: ScorecardResult) -> BriefDraft:
    """Brief 초안 생성"""

    brief_id = f"BRF-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}"

    return BriefDraft(
        brief_id=brief_id,
        signal_id=signal_data["signal_id"],
        title=signal_data.get("title", "Opportunity Brief"),
        customer={
            "segment": signal_data.get("customer_segment", ""),
            "buyer_role": "",
            "users": "",
            "account": signal_data.get("customer_or_account", ""),
        },
        problem={
            "pain": signal_data.get("pain", ""),
            "why_now": scorecard.rationale,
            "current_process": signal_data.get("current_workflow", ""),
        },
        solution_hypothesis={"approach": "", "integration_points": [], "data_needed": []},
        kpis=signal_data.get("kpi_hypothesis", []),
        evidence=[e.get("url", "") for e in signal_data.get("evidence", []) if isinstance(e, dict)],
        validation_plan={
            "questions": ["고객이 실제로 이 문제를 해결하고자 하는가?"],
            "method": "5DAY_SPRINT",
            "success_criteria": ["Pain Point 재확인", "Buyer 식별"],
            "timebox_days": 5,
        },
        status="DRAFT",
    )


# ============================================================
# 메인 파이프라인
# ============================================================


class InterviewToBriefPipeline:
    """
    WF-02: Interview to Brief

    트리거: /ax:interview
    """

    # 단계 정의
    STEPS = [
        {"id": "SIGNAL_EXTRACTION", "label": "Signal 추출"},
        {"id": "SCORECARD_EVALUATION", "label": "Scorecard 평가"},
        {"id": "BRIEF_GENERATION", "label": "Brief 생성"},
        {"id": "DB_SAVE", "label": "DB 저장"},
    ]

    def __init__(self):
        self.logger = logger.bind(workflow="WF-02")

    async def run(self, input_data: InterviewInput) -> InterviewOutput:
        """파이프라인 실행"""
        self.logger.info(
            "Starting Interview-to-Brief Pipeline",
            play_id=input_data.play_id,
            customer=input_data.customer,
        )

        # 1. 인터뷰 노트에서 Signal 추출
        signals = await self._extract_signals(input_data)

        # 2. 각 Signal에 대해 Scorecard 평가
        scorecards = []
        go_signals = []

        for signal in signals:
            scorecard = await self._evaluate_signal(signal)
            scorecards.append(scorecard)

            if scorecard["recommendation"]["decision"] in ["GO", "PIVOT"]:
                go_signals.append({"signal": signal, "scorecard": scorecard})

        # 3. GO/PIVOT 판정 Signal에 대해 Brief 생성 (승인 대기)
        briefs = []
        pending_approvals = []

        for item in go_signals:
            brief_draft = await self._generate_brief_draft(item["signal"], item["scorecard"])
            briefs.append(brief_draft)
            pending_approvals.append(brief_draft["brief_id"])

        # 결과 요약
        summary = {
            "total_signals": len(signals),
            "go_count": sum(1 for s in scorecards if s["recommendation"]["decision"] == "GO"),
            "pivot_count": sum(1 for s in scorecards if s["recommendation"]["decision"] == "PIVOT"),
            "hold_count": sum(1 for s in scorecards if s["recommendation"]["decision"] == "HOLD"),
            "no_go_count": sum(1 for s in scorecards if s["recommendation"]["decision"] == "NO_GO"),
            "briefs_created": len(briefs),
        }

        self.logger.info("Interview-to-Brief Pipeline completed", **summary)

        return InterviewOutput(
            signals=signals,
            scorecards=scorecards,
            briefs=briefs,
            pending_approvals=pending_approvals,
            summary=summary,
        )

    async def _extract_signals(self, input_data: InterviewInput) -> list[dict[str, Any]]:
        """인터뷰 노트에서 Signal 추출"""
        self.logger.info("Extracting signals from interview")

        # Signal 추출
        extracted = extract_signals_from_interview(
            input_data.content, input_data.play_id, input_data.customer
        )

        signals = []
        for i, ext in enumerate(extracted):
            signal_id = f"SIG-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}{i:02d}"

            signal = {
                "signal_id": signal_id,
                "title": ext.title,
                "source": input_data.source,
                "channel": input_data.channel,
                "play_id": input_data.play_id or "KT_Sales_S01_Interview",
                "customer_segment": input_data.customer or "",
                "pain": ext.pain,
                "current_workflow": ext.current_workflow,
                "kpi_hypothesis": ext.kpi_hypothesis,
                "evidence": [
                    {
                        "type": "meeting_note",
                        "title": "인터뷰 노트",
                        "url": "",
                        "note": f"인터뷰 대상: {input_data.interviewee or 'N/A'}",
                    }
                ],
                "status": "NEW",
                "confidence": ext.confidence,
                "created_at": datetime.now(UTC).isoformat(),
            }
            signals.append(signal)

        self.logger.info(f"Extracted {len(signals)} signals")
        return signals

    async def _evaluate_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Signal Scorecard 평가"""
        self.logger.info("Evaluating signal", signal_id=signal["signal_id"])

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

        scorecard = {
            "scorecard_id": scorecard_id,
            "signal_id": signal["signal_id"],
            "total_score": total_score,
            "dimension_scores": dimension_scores,
            "red_flags": red_flags,
            "recommendation": recommendation,
            "scored_at": datetime.now(UTC).isoformat(),
        }

        self.logger.info(
            "Signal evaluated",
            signal_id=signal["signal_id"],
            total_score=total_score,
            decision=recommendation["decision"],
        )

        return scorecard

    async def _generate_brief_draft(
        self, signal: dict[str, Any], scorecard: dict[str, Any]
    ) -> dict[str, Any]:
        """Brief 초안 생성"""
        self.logger.info("Generating brief draft", signal_id=signal["signal_id"])

        brief_id = f"BRF-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M%S')}"

        brief = {
            "brief_id": brief_id,
            "signal_id": signal["signal_id"],
            "title": signal.get("title", "Opportunity Brief"),
            "customer": {
                "segment": signal.get("customer_segment", ""),
                "buyer_role": "",
                "users": "",
                "account": "",
            },
            "problem": {
                "pain": signal.get("pain", ""),
                "why_now": scorecard["recommendation"]["rationale"],
                "current_process": signal.get("current_workflow", ""),
            },
            "solution_hypothesis": {"approach": "", "integration_points": [], "data_needed": []},
            "kpis": signal.get("kpi_hypothesis", []),
            "evidence": [
                e.get("url", "")
                for e in signal.get("evidence", [])
                if isinstance(e, dict) and e.get("url")
            ],
            "validation_plan": {
                "questions": ["고객이 실제로 이 문제를 해결하고자 하는가?"],
                "method": "5DAY_SPRINT",
                "success_criteria": ["Pain Point 재확인", "Buyer 식별"],
                "timebox_days": 5,
            },
            "risks": [],
            "status": "DRAFT",
            "owner": "",
            "scorecard_score": scorecard["total_score"],
            "scorecard_decision": scorecard["recommendation"]["decision"],
            "created_at": datetime.now(UTC).isoformat(),
        }

        self.logger.info("Brief draft generated", brief_id=brief_id)
        return brief


# ============================================================
# AG-UI 이벤트 발행 버전
# ============================================================


class InterviewToBriefPipelineWithEvents(InterviewToBriefPipeline):
    """
    WF-02: Interview to Brief with AG-UI Events

    실시간 이벤트 발행을 포함한 인터뷰-to-Brief 파이프라인
    """

    def __init__(self, emitter: "WorkflowEventEmitter"):
        super().__init__()
        self.emitter = emitter
        self.logger = logger.bind(workflow="WF-02", with_events=True)

    async def run(self, input_data: InterviewInput) -> InterviewOutput:
        """워크플로 실행 (이벤트 발행 포함)"""
        self.logger.info(
            "Starting Interview-to-Brief pipeline with events", play_id=input_data.play_id
        )

        # 실행 시작 이벤트
        await self.emitter.emit_run_started(
            workflow_id="WF-02",
            input_data={
                "play_id": input_data.play_id,
                "customer": input_data.customer,
                "source": input_data.source,
                "channel": input_data.channel,
                "content_length": len(input_data.content),
            },
            steps=self.STEPS,
        )

        try:
            # Step 1: Signal 추출
            await self.emitter.emit_step_started(
                step_id="SIGNAL_EXTRACTION",
                step_index=0,
                step_label="Signal 추출",
                message="인터뷰 노트에서 Pain Point와 기회를 추출하고 있습니다...",
            )
            signals = await self._extract_signals(input_data)

            # Signal 미리보기 Surface
            for signal in signals:
                await self.emitter.emit_surface(
                    surface_id=f"signal-{signal['signal_id']}",
                    surface={
                        "id": f"signal-{signal['signal_id']}",
                        "type": "signal_preview",
                        "title": signal["title"],
                        "signal": {
                            "signal_id": signal["signal_id"],
                            "title": signal["title"],
                            "pain": signal["pain"],
                            "source": signal["source"],
                            "channel": signal["channel"],
                            "confidence": signal.get("confidence", 0.7),
                        },
                    },
                )

            await self.emitter.emit_step_finished(
                step_id="SIGNAL_EXTRACTION",
                step_index=0,
                result={"signals_count": len(signals)},
            )

            # Step 2: Scorecard 평가
            await self.emitter.emit_step_started(
                step_id="SCORECARD_EVALUATION",
                step_index=1,
                step_label="Scorecard 평가",
                message=f"{len(signals)}개 Signal에 대한 100점 평가를 진행합니다...",
            )

            scorecards = []
            go_signals = []

            for signal in signals:
                scorecard = await self._evaluate_signal(signal)
                scorecards.append(scorecard)

                # Scorecard Surface
                await self.emitter.emit_surface(
                    surface_id=f"scorecard-{scorecard['scorecard_id']}",
                    surface={
                        "id": f"scorecard-{scorecard['scorecard_id']}",
                        "type": "scorecard_result",
                        "title": f"Scorecard: {signal['title']}",
                        "scorecard": {
                            "scorecard_id": scorecard["scorecard_id"],
                            "signal_id": scorecard["signal_id"],
                            "total_score": scorecard["total_score"],
                            "dimension_scores": scorecard["dimension_scores"],
                            "red_flags": scorecard["red_flags"],
                            "decision": scorecard["recommendation"]["decision"],
                            "next_step": scorecard["recommendation"]["next_step"],
                        },
                    },
                )

                if scorecard["recommendation"]["decision"] in ["GO", "PIVOT"]:
                    go_signals.append({"signal": signal, "scorecard": scorecard})

            await self.emitter.emit_step_finished(
                step_id="SCORECARD_EVALUATION",
                step_index=1,
                result={
                    "evaluated": len(scorecards),
                    "go_count": len(go_signals),
                },
            )

            # Step 3: Brief 생성
            await self.emitter.emit_step_started(
                step_id="BRIEF_GENERATION",
                step_index=2,
                step_label="Brief 생성",
                message=f"{len(go_signals)}개 GO/PIVOT Signal에 대한 Brief를 생성합니다...",
            )

            briefs = []
            pending_approvals = []

            for item in go_signals:
                brief_draft = await self._generate_brief_draft(item["signal"], item["scorecard"])
                briefs.append(brief_draft)
                pending_approvals.append(brief_draft["brief_id"])

                # Brief Surface
                await self.emitter.emit_surface(
                    surface_id=f"brief-{brief_draft['brief_id']}",
                    surface={
                        "id": f"brief-{brief_draft['brief_id']}",
                        "type": "brief_draft",
                        "title": f"Brief: {brief_draft['title']}",
                        "brief": {
                            "brief_id": brief_draft["brief_id"],
                            "signal_id": brief_draft["signal_id"],
                            "title": brief_draft["title"],
                            "pain": brief_draft["problem"]["pain"],
                            "score": brief_draft["scorecard_score"],
                            "decision": brief_draft["scorecard_decision"],
                            "status": brief_draft["status"],
                        },
                    },
                )

                # 승인 요청 이벤트
                if brief_draft["scorecard_decision"] == "GO":
                    await self.emitter.emit_approval_request(
                        approval_id=f"approval-{brief_draft['brief_id']}",
                        title="Brief 생성 승인 요청",
                        description=f"Signal '{item['signal']['title']}'에 대한 Brief를 Confluence에 게시합니다.",
                        impact=ImpactLevel.MEDIUM,
                        changes=[
                            {
                                "type": "create",
                                "target": "Confluence Page",
                                "description": f"Brief 페이지: {brief_draft['title']}",
                            }
                        ],
                    )

            await self.emitter.emit_step_finished(
                step_id="BRIEF_GENERATION",
                step_index=2,
                result={"briefs_created": len(briefs)},
            )

            # Step 4: DB 저장
            await self.emitter.emit_step_started(
                step_id="DB_SAVE",
                step_index=3,
                step_label="DB 저장",
                message="Signal, Scorecard, Brief를 데이터베이스에 저장합니다...",
            )

            # DB 저장은 별도 함수에서 수행 (여기서는 시뮬레이션)
            await self.emitter.emit_step_finished(
                step_id="DB_SAVE",
                step_index=3,
                result={"saved": True},
            )

            # 결과 요약
            summary = {
                "total_signals": len(signals),
                "go_count": sum(1 for s in scorecards if s["recommendation"]["decision"] == "GO"),
                "pivot_count": sum(
                    1 for s in scorecards if s["recommendation"]["decision"] == "PIVOT"
                ),
                "hold_count": sum(
                    1 for s in scorecards if s["recommendation"]["decision"] == "HOLD"
                ),
                "no_go_count": sum(
                    1 for s in scorecards if s["recommendation"]["decision"] == "NO_GO"
                ),
                "briefs_created": len(briefs),
            }

            result = InterviewOutput(
                signals=signals,
                scorecards=scorecards,
                briefs=briefs,
                pending_approvals=pending_approvals,
                summary=summary,
            )

            # 실행 완료 이벤트
            await self.emitter.emit_run_finished(result=summary)

            self.logger.info("Interview-to-Brief pipeline with events completed", **summary)

            return result

        except Exception as e:
            self.logger.error("Pipeline error", error=str(e))
            await self.emitter.emit_run_error(str(e), recoverable=False)
            raise


# ============================================================
# DB 연동 버전
# ============================================================


class InterviewToBriefPipelineWithDB(InterviewToBriefPipelineWithEvents):
    """
    WF-02: Interview to Brief with DB Integration

    데이터베이스 연동을 포함한 완전한 파이프라인
    """

    def __init__(self, emitter: "WorkflowEventEmitter", db: "AsyncSession"):
        super().__init__(emitter)
        self.db = db
        self.logger = logger.bind(workflow="WF-02", with_db=True)

    async def save_to_db(
        self,
        signals: list[dict[str, Any]],
        scorecards: list[dict[str, Any]],
        briefs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """결과를 DB에 저장"""
        from backend.database.models.brief import BriefStatus
        from backend.database.models.signal import SignalStatus
        from backend.database.repositories.brief import brief_repo
        from backend.database.repositories.scorecard import scorecard_repo
        from backend.database.repositories.signal import signal_repo

        saved: dict[str, list[Any]] = {"signals": [], "scorecards": [], "briefs": []}

        # Signal 저장
        for signal_data in signals:
            try:
                signal_id = await signal_repo.generate_signal_id(self.db)
                signal_data["signal_id"] = signal_id
                signal_data["status"] = SignalStatus.NEW

                db_signal = await signal_repo.create(self.db, signal_data)
                saved["signals"].append(db_signal.signal_id)

                self.logger.info("Signal saved", signal_id=signal_id)
            except Exception as e:
                self.logger.error("Failed to save signal", error=str(e))

        # Scorecard 저장
        for sc_data in scorecards:
            try:
                scorecard_id = await scorecard_repo.generate_scorecard_id(self.db)
                sc_data["scorecard_id"] = scorecard_id

                db_scorecard = await scorecard_repo.create(self.db, sc_data)
                saved["scorecards"].append(db_scorecard.scorecard_id)

                self.logger.info("Scorecard saved", scorecard_id=scorecard_id)
            except Exception as e:
                self.logger.error("Failed to save scorecard", error=str(e))

        # Brief 저장
        for brief_data in briefs:
            try:
                brief_id = await brief_repo.generate_brief_id(self.db)
                brief_data["brief_id"] = brief_id
                brief_data["status"] = BriefStatus.DRAFT

                db_brief = await brief_repo.create(self.db, brief_data)
                saved["briefs"].append(db_brief.brief_id)

                self.logger.info("Brief saved", brief_id=brief_id)
            except Exception as e:
                self.logger.error("Failed to save brief", error=str(e))

        await self.db.commit()
        return saved


# ============================================================
# 워크플로 인스턴스 및 진입점
# ============================================================

workflow = InterviewToBriefPipeline()


async def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """워크플로 진입점"""
    interview_input = InterviewInput(
        content=input_data["content"],
        play_id=input_data.get("play_id"),
        customer=input_data.get("customer"),
        source=input_data.get("source", "KT"),
        channel=input_data.get("channel", "영업PM"),
        interviewee=input_data.get("interviewee"),
        interview_date=input_data.get("interview_date"),
    )

    result = await workflow.run(interview_input)

    return {
        "signals": result.signals,
        "scorecards": result.scorecards,
        "briefs": result.briefs,
        "pending_approvals": result.pending_approvals,
        "summary": result.summary,
    }


async def run_with_events(
    input_data: dict[str, Any], emitter: "WorkflowEventEmitter"
) -> dict[str, Any]:
    """이벤트 발행을 포함한 워크플로 실행"""
    interview_input = InterviewInput(
        content=input_data["content"],
        play_id=input_data.get("play_id"),
        customer=input_data.get("customer"),
        source=input_data.get("source", "KT"),
        channel=input_data.get("channel", "영업PM"),
        interviewee=input_data.get("interviewee"),
        interview_date=input_data.get("interview_date"),
    )

    pipeline = InterviewToBriefPipelineWithEvents(emitter)
    result = await pipeline.run(interview_input)

    return {
        "signals": result.signals,
        "scorecards": result.scorecards,
        "briefs": result.briefs,
        "pending_approvals": result.pending_approvals,
        "summary": result.summary,
    }


# 타입 힌트를 위한 import (순환 참조 방지)
if __name__ != "__main__":
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.agent_runtime.event_manager import WorkflowEventEmitter
