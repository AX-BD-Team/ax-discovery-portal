"""
WF-03: VoC Mining

VoC/티켓 데이터 → 테마화 → Signal 생성 → Brief 후보
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class VoCInput:
    """VoC 입력"""

    data_source: str  # VoC 데이터 소스 (링크 또는 데이터 요약)
    play_id: str = "KT_Desk_V01_VoC"
    min_frequency: int = 5  # 최소 빈도


@dataclass
class VoCOutput:
    """VoC 분석 출력"""

    themes: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    brief_candidates: list[dict[str, Any]]


class VoCMiningPipeline:
    """
    WF-03: VoC Mining

    트리거: /ax:voc
    """

    def __init__(self):
        self.logger = logger.bind(workflow="WF-03")

    async def run(self, input_data: VoCInput) -> VoCOutput:
        """파이프라인 실행"""
        self.logger.info("Starting VoC Mining Pipeline")

        # 1. VoC 데이터 분석 및 테마화
        themes = await self._analyze_themes(input_data)

        # 2. 테마별 Signal 생성
        signals = await self._create_signals(themes, input_data.play_id)

        # 3. Brief 후보 선정 (빈도/심각도 기준)
        brief_candidates = await self._select_brief_candidates(signals)

        self.logger.info(
            "VoC Mining completed",
            themes=len(themes),
            signals=len(signals),
            candidates=len(brief_candidates),
        )

        return VoCOutput(themes=themes, signals=signals, brief_candidates=brief_candidates)

    async def _analyze_themes(self, input_data: VoCInput) -> list[dict[str, Any]]:
        """VoC 데이터에서 테마 추출"""
        # TODO: VoCAnalyst Agent 호출
        # LLM을 사용하여 테마 클러스터링

        return [
            {
                "theme_id": "THEME-001",
                "name": "응답 시간 지연",
                "frequency": 45,
                "severity": "HIGH",
                "keywords": ["느림", "대기", "시간"],
                "sample_tickets": [],
            },
            {
                "theme_id": "THEME-002",
                "name": "복잡한 절차",
                "frequency": 32,
                "severity": "MEDIUM",
                "keywords": ["복잡", "어려움", "단계"],
                "sample_tickets": [],
            },
        ]

    async def _create_signals(
        self, themes: list[dict[str, Any]], play_id: str
    ) -> list[dict[str, Any]]:
        """테마에서 Signal 생성"""
        signals = []

        for i, theme in enumerate(themes):
            signal_id = f"SIG-{datetime.now().year}-VOC{i + 1:03d}"

            signals.append(
                {
                    "signal_id": signal_id,
                    "title": f"[VoC] {theme['name']}",
                    "source": "KT",
                    "channel": "데스크리서치",
                    "play_id": play_id,
                    "pain": f"고객 VoC에서 {theme['frequency']}건 발생: {theme['name']}",
                    "evidence": [
                        {
                            "type": "ticket",
                            "title": f"VoC 테마: {theme['name']}",
                            "url": "",
                            "note": f"빈도: {theme['frequency']}건",
                        }
                    ],
                    "tags": theme.get("keywords", []),
                    "status": "NEW",
                    "confidence": min(theme["frequency"] / 50, 1.0),
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )

        return signals

    async def _select_brief_candidates(self, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Brief 후보 선정"""
        # 신뢰도 0.7 이상인 Signal을 Brief 후보로
        candidates = [s for s in signals if s.get("confidence", 0) >= 0.7]

        return candidates[:2]  # 상위 2개만


workflow = VoCMiningPipeline()


async def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """워크플로 진입점"""
    voc_input = VoCInput(
        data_source=input_data["data_source"],
        play_id=input_data.get("play_id", "KT_Desk_V01_VoC"),
        min_frequency=input_data.get("min_frequency", 5),
    )

    result = await workflow.run(voc_input)

    return {
        "themes": result.themes,
        "signals": result.signals,
        "brief_candidates": result.brief_candidates,
    }
