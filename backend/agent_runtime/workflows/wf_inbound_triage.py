"""
WF-04: Inbound Triage

Intake Form 제출 → 중복 체크 → Scorecard 초안 → Brief 승격 (48h SLA)
"""

from typing import Any
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class InboundInput:
    """Intake Form 입력"""
    title: str
    description: str
    customer_segment: str | None = None
    pain: str | None = None
    submitter: str | None = None
    urgency: str = "NORMAL"  # URGENT, NORMAL, LOW


@dataclass
class InboundOutput:
    """Inbound Triage 출력"""
    signal_id: str
    is_duplicate: bool
    duplicate_of: str | None
    scorecard: dict[str, Any] | None
    next_action: str
    sla_deadline: str


class InboundTriagePipeline:
    """
    WF-04: Inbound Triage
    
    트리거: Intake Form 제출
    SLA: 48시간 내 처리
    """
    
    def __init__(self):
        self.logger = logger.bind(workflow="WF-04")
        self.sla_hours = 48
    
    async def run(self, input_data: InboundInput) -> InboundOutput:
        """파이프라인 실행"""
        self.logger.info("Starting Inbound Triage", title=input_data.title)
        
        # 1. Signal 생성
        signal = await self._create_signal(input_data)
        signal_id = signal["signal_id"]
        
        # 2. 중복 체크
        duplicate_check = await self._check_duplicate(signal)
        
        if duplicate_check["is_duplicate"]:
            return InboundOutput(
                signal_id=signal_id,
                is_duplicate=True,
                duplicate_of=duplicate_check["duplicate_of"],
                scorecard=None,
                next_action="MERGE_OR_CLOSE",
                sla_deadline=self._calculate_sla()
            )
        
        # 3. Scorecard 초안 생성
        scorecard = await self._create_scorecard_draft(signal)
        
        # 4. 다음 액션 결정
        next_action = self._determine_next_action(scorecard)
        
        self.logger.info(
            "Inbound Triage completed",
            signal_id=signal_id,
            decision=scorecard["recommendation"]["decision"]
        )
        
        return InboundOutput(
            signal_id=signal_id,
            is_duplicate=False,
            duplicate_of=None,
            scorecard=scorecard,
            next_action=next_action,
            sla_deadline=self._calculate_sla()
        )
    
    async def _create_signal(self, input_data: InboundInput) -> dict[str, Any]:
        """Signal 생성"""
        signal_id = f"SIG-{datetime.now().year}-INB{datetime.now().strftime('%m%d%H%M')}"
        
        return {
            "signal_id": signal_id,
            "title": input_data.title,
            "description": input_data.description,
            "source": "KT",  # 기본값, 필요시 변경
            "channel": "인바운드",
            "play_id": self._route_to_play(input_data),
            "customer_segment": input_data.customer_segment,
            "pain": input_data.pain or input_data.description,
            "submitter": input_data.submitter,
            "urgency": input_data.urgency,
            "status": "NEW",
            "created_at": datetime.utcnow().isoformat()
        }
    
    def _route_to_play(self, input_data: InboundInput) -> str:
        """Play ID 라우팅"""
        # TODO: 키워드/카테고리 기반 라우팅 로직
        return "KT_Inbound_I01"
    
    async def _check_duplicate(self, signal: dict[str, Any]) -> dict[str, Any]:
        """중복 Signal 체크"""
        # TODO: 유사도 검색 구현
        # - 제목/설명 유사도
        # - 고객 세그먼트 매칭
        # - 최근 30일 내 유사 Signal
        
        return {
            "is_duplicate": False,
            "duplicate_of": None,
            "similarity_score": 0.0
        }
    
    async def _create_scorecard_draft(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Scorecard 초안 생성"""
        # TODO: AI 기반 초안 생성
        
        scorecard_id = f"SCR-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}"
        
        return {
            "scorecard_id": scorecard_id,
            "signal_id": signal["signal_id"],
            "total_score": 50,  # 초안이므로 중간값
            "dimension_scores": {
                "problem_severity": 10,
                "willingness_to_pay": 10,
                "data_availability": 10,
                "feasibility": 10,
                "strategic_fit": 10
            },
            "red_flags": [],
            "recommendation": {
                "decision": "PIVOT",
                "next_step": "NEED_MORE_EVIDENCE",
                "rationale": "초안 - 검토 필요"
            },
            "is_draft": True,
            "scored_at": datetime.utcnow().isoformat()
        }
    
    def _determine_next_action(self, scorecard: dict[str, Any]) -> str:
        """다음 액션 결정"""
        decision = scorecard["recommendation"]["decision"]
        
        if decision == "GO":
            return "CREATE_BRIEF"
        elif decision == "PIVOT":
            return "REVIEW_AND_ENHANCE"
        elif decision == "HOLD":
            return "SCHEDULE_FOLLOW_UP"
        else:
            return "ARCHIVE"
    
    def _calculate_sla(self) -> str:
        """SLA 마감 시간 계산"""
        from datetime import timedelta
        deadline = datetime.utcnow() + timedelta(hours=self.sla_hours)
        return deadline.isoformat()


workflow = InboundTriagePipeline()


async def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """워크플로 진입점"""
    inbound_input = InboundInput(
        title=input_data["title"],
        description=input_data["description"],
        customer_segment=input_data.get("customer_segment"),
        pain=input_data.get("pain"),
        submitter=input_data.get("submitter"),
        urgency=input_data.get("urgency", "NORMAL")
    )
    
    result = await workflow.run(inbound_input)
    
    return {
        "signal_id": result.signal_id,
        "is_duplicate": result.is_duplicate,
        "duplicate_of": result.duplicate_of,
        "scorecard": result.scorecard,
        "next_action": result.next_action,
        "sla_deadline": result.sla_deadline
    }
