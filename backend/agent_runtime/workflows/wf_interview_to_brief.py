"""
WF-02: Interview to Brief

인터뷰 노트 → Signal 추출 → Scorecard 평가 → Brief 생성
"""

from typing import Any
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class InterviewInput:
    """인터뷰 입력"""
    content: str  # 인터뷰 노트 텍스트 또는 문서 링크
    play_id: str | None = None
    customer: str | None = None


@dataclass
class InterviewOutput:
    """인터뷰 파이프라인 출력"""
    signals: list[dict[str, Any]]
    scorecards: list[dict[str, Any]]
    briefs: list[dict[str, Any]]
    pending_approvals: list[str]


class InterviewToBriefPipeline:
    """
    WF-02: Interview to Brief
    
    트리거: /ax:interview
    """
    
    def __init__(self):
        self.logger = logger.bind(workflow="WF-02")
    
    async def run(self, input_data: InterviewInput) -> InterviewOutput:
        """파이프라인 실행"""
        self.logger.info("Starting Interview-to-Brief Pipeline")
        
        # 1. 인터뷰 노트에서 Signal 추출
        signals = await self._extract_signals(input_data)
        
        # 2. 각 Signal에 대해 Scorecard 평가
        scorecards = []
        go_signals = []
        
        for signal in signals:
            scorecard = await self._evaluate_signal(signal)
            scorecards.append(scorecard)
            
            if scorecard["recommendation"]["decision"] == "GO":
                go_signals.append(signal)
        
        # 3. GO 판정 Signal에 대해 Brief 생성 (승인 대기)
        briefs = []
        pending_approvals = []
        
        for signal in go_signals:
            brief_draft = await self._generate_brief_draft(signal)
            briefs.append(brief_draft)
            pending_approvals.append(brief_draft["brief_id"])
        
        self.logger.info(
            "Interview-to-Brief Pipeline completed",
            signals=len(signals),
            go_count=len(go_signals),
            briefs=len(briefs)
        )
        
        return InterviewOutput(
            signals=signals,
            scorecards=scorecards,
            briefs=briefs,
            pending_approvals=pending_approvals
        )
    
    async def _extract_signals(self, input_data: InterviewInput) -> list[dict[str, Any]]:
        """인터뷰 노트에서 Signal 추출"""
        # TODO: InterviewMiner Agent 호출
        # LLM을 사용하여 Pain Point, 니즈, 기회 추출
        
        signal_id = f"SIG-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}"
        
        return [{
            "signal_id": signal_id,
            "title": "인터뷰에서 추출한 Signal",
            "source": "KT",
            "channel": "영업PM",
            "play_id": input_data.play_id or "KT_Sales_S01_Interview",
            "customer_segment": input_data.customer,
            "pain": "인터뷰에서 식별된 Pain Point",
            "evidence": [
                {
                    "type": "meeting_note",
                    "title": "인터뷰 노트",
                    "url": ""
                }
            ],
            "status": "NEW",
            "created_at": datetime.utcnow().isoformat()
        }]
    
    async def _evaluate_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Signal Scorecard 평가"""
        # TODO: ScorecardEvaluator Agent 호출
        
        scorecard_id = f"SCR-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}"
        
        return {
            "scorecard_id": scorecard_id,
            "signal_id": signal["signal_id"],
            "total_score": 65,  # 예시
            "dimension_scores": {
                "problem_severity": 15,
                "willingness_to_pay": 12,
                "data_availability": 14,
                "feasibility": 12,
                "strategic_fit": 12
            },
            "red_flags": [],
            "recommendation": {
                "decision": "PIVOT",
                "next_step": "NEED_MORE_EVIDENCE",
                "rationale": "추가 조사 필요"
            },
            "scored_at": datetime.utcnow().isoformat()
        }
    
    async def _generate_brief_draft(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Brief 초안 생성"""
        # TODO: BriefWriter Agent 호출
        
        brief_id = f"BRF-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}"
        
        return {
            "brief_id": brief_id,
            "signal_id": signal["signal_id"],
            "title": signal["title"],
            "status": "DRAFT",
            "created_at": datetime.utcnow().isoformat()
        }


workflow = InterviewToBriefPipeline()


async def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """워크플로 진입점"""
    interview_input = InterviewInput(
        content=input_data["content"],
        play_id=input_data.get("play_id"),
        customer=input_data.get("customer")
    )
    
    result = await workflow.run(interview_input)
    
    return {
        "signals": result.signals,
        "scorecards": result.scorecards,
        "briefs": result.briefs,
        "pending_approvals": result.pending_approvals
    }
