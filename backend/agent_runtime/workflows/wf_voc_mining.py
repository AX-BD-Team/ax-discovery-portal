"""
WF-03: VoC Mining

VoC/티켓 데이터 → 테마화 → Signal 생성 → Brief 후보

트리거:
- /ax:voc 커맨드
- KT_Desk_V01_VoC Play ID

입력: VoC/티켓 데이터 (CSV, Excel, API, 텍스트)
출력: 테마 5개 + Signal 다건 + Brief 후보 1~2개
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

from .voc_data_handlers import VoCRecord, get_handler

logger = structlog.get_logger()


# ============================================================
# 데이터 모델
# ============================================================


class Severity(str, Enum):
    """심각도"""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class VoCInput:
    """VoC 입력 (확장된 버전)

    Args:
        source_type: 데이터 소스 타입 ("csv", "excel", "api", "text")
        file_content: 파일 바이너리 내용 (CSV/Excel)
        api_data: API 응답 데이터 (list[dict])
        text_content: 텍스트 내용
        play_id: Play ID
        source: 원천 (KT, 그룹사, 대외)
        channel: 채널 (데스크리서치, 영업PM 등)
        min_frequency: 테마 최소 빈도
        max_themes: 최대 테마 개수

    Legacy Args (하위 호환):
        data_source: 레거시 필드 (text_content로 매핑)
    """

    # 하위 호환을 위해 data_source를 첫 번째로 (기존 테스트 호환)
    data_source: str | None = None

    source_type: str = "text"  # "csv", "excel", "api", "text"
    file_content: bytes | None = None
    api_data: list[dict[str, Any]] | None = None
    text_content: str | None = None
    play_id: str = "KT_Desk_V01_VoC"
    source: str = "KT"
    channel: str = "데스크리서치"
    min_frequency: int = 5
    max_themes: int = 5

    def __post_init__(self):
        """레거시 필드 매핑"""
        # data_source가 있으면 text_content로 매핑
        if self.data_source and not self.text_content:
            self.text_content = self.data_source


@dataclass
class VoCTheme:
    """VoC 테마"""

    theme_id: str
    name: str
    frequency: int
    severity: Severity
    keywords: list[str]
    sample_texts: list[str] = field(default_factory=list)
    confidence: float = 0.7


@dataclass
class VoCOutput:
    """VoC 분석 출력"""

    themes: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    brief_candidates: list[dict[str, Any]]
    summary: dict[str, Any] = field(default_factory=dict)


# ============================================================
# 테마 추출 로직
# ============================================================


# 테마 키워드 맵핑 (휴리스틱 기반)
THEME_KEYWORDS = {
    "응답 시간 지연": {
        "keywords": ["느림", "대기", "시간", "지연", "오래", "늦", "기다"],
        "severity": Severity.HIGH,
    },
    "복잡한 절차": {
        "keywords": ["복잡", "어려", "단계", "절차", "불편", "번거"],
        "severity": Severity.MEDIUM,
    },
    "시스템 오류": {
        "keywords": ["오류", "에러", "버그", "실패", "안됨", "안돼", "안 됨"],
        "severity": Severity.HIGH,
    },
    "UI/UX 불만": {
        "keywords": ["화면", "디자인", "메뉴", "찾기", "어디", "버튼"],
        "severity": Severity.LOW,
    },
    "정보 부족": {
        "keywords": ["정보", "설명", "안내", "모르", "이해", "헷갈"],
        "severity": Severity.MEDIUM,
    },
}


def extract_themes_from_records(
    records: list[VoCRecord], min_frequency: int = 5, max_themes: int = 5
) -> list[VoCTheme]:
    """VoC 레코드에서 테마 추출 (휴리스틱 기반)

    실제 프로덕션에서는 LLM을 사용하여 클러스터링/테마 추출
    """
    # 테마별 매칭 카운트
    theme_counts: dict[str, list[VoCRecord]] = {name: [] for name in THEME_KEYWORDS}

    for record in records:
        text_lower = record.text.lower()
        for theme_name, theme_info in THEME_KEYWORDS.items():
            if any(kw in text_lower for kw in theme_info["keywords"]):
                theme_counts[theme_name].append(record)

    # 빈도 기준 필터링 및 정렬
    themes = []
    sorted_themes = sorted(theme_counts.items(), key=lambda x: len(x[1]), reverse=True)

    for i, (theme_name, matched_records) in enumerate(sorted_themes):
        if len(matched_records) < min_frequency:
            continue
        if len(themes) >= max_themes:
            break

        theme_info = THEME_KEYWORDS[theme_name]
        theme = VoCTheme(
            theme_id=f"THEME-{i + 1:03d}",
            name=theme_name,
            frequency=len(matched_records),
            severity=theme_info["severity"],
            keywords=theme_info["keywords"][:5],
            sample_texts=[r.text[:100] for r in matched_records[:3]],
            confidence=min(len(matched_records) / 50, 1.0),
        )
        themes.append(theme)

    return themes


def extract_themes_simple(
    texts: list[str], min_frequency: int = 5, max_themes: int = 5
) -> list[VoCTheme]:
    """간단한 텍스트 리스트에서 테마 추출"""
    records = [VoCRecord(text=t) for t in texts]
    return extract_themes_from_records(records, min_frequency, max_themes)


# ============================================================
# 메인 파이프라인
# ============================================================


class VoCMiningPipeline:
    """
    WF-03: VoC Mining

    트리거: /ax:voc
    """

    # 단계 정의
    STEPS = [
        {"id": "DATA_LOADING", "label": "데이터 로딩"},
        {"id": "DATA_PREPROCESSING", "label": "데이터 전처리"},
        {"id": "THEME_EXTRACTION", "label": "테마 추출"},
        {"id": "SIGNAL_GENERATION", "label": "Signal 생성"},
        {"id": "BRIEF_SELECTION", "label": "Brief 후보 선정"},
    ]

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

    async def _load_data(self, input_data: VoCInput) -> list[VoCRecord]:
        """데이터 로딩"""
        self.logger.info("Loading VoC data", source_type=input_data.source_type)

        # 소스 타입에 따라 핸들러 선택
        try:
            handler = get_handler(input_data.source_type)
        except ValueError:
            self.logger.warning(
                "Unknown source type, falling back to text",
                source_type=input_data.source_type,
            )
            handler = get_handler("text")

        # 데이터 파싱
        if (
            input_data.source_type in ("csv", "excel")
            and input_data.file_content
        ):
            records = handler.parse(input_data.file_content)
        elif input_data.source_type == "api" and input_data.api_data:
            records = handler.parse(input_data.api_data)
        elif input_data.text_content:
            records = handler.parse(input_data.text_content)
        elif input_data.data_source:
            # 레거시 호환
            records = handler.parse(input_data.data_source)
        else:
            self.logger.warning("No data provided")
            records = []

        self.logger.info("Data loaded", total_records=len(records))
        return records

    async def _preprocess(self, records: list[VoCRecord]) -> list[VoCRecord]:
        """데이터 전처리"""
        self.logger.info("Preprocessing VoC data")

        # 중복 제거
        seen_texts = set()
        unique_records = []
        for record in records:
            normalized = record.text.strip().lower()
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique_records.append(record)

        self.logger.info(
            "Preprocessing completed",
            original=len(records),
            unique=len(unique_records),
        )
        return unique_records

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

    async def _select_brief_candidates(
        self, signals: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Brief 후보 선정"""
        # 신뢰도 0.7 이상인 Signal을 Brief 후보로
        candidates = [s for s in signals if s.get("confidence", 0) >= 0.7]

        return candidates[:2]  # 상위 2개만


# ============================================================
# AG-UI 이벤트 발행 버전
# ============================================================


class VoCMiningPipelineWithEvents(VoCMiningPipeline):
    """
    WF-03: VoC Mining with AG-UI Events

    실시간 이벤트 발행을 포함한 VoC Mining 파이프라인
    """

    def __init__(self, emitter: "WorkflowEventEmitter"):
        super().__init__()
        self.emitter = emitter
        self.logger = logger.bind(workflow="WF-03", with_events=True)

    async def run(self, input_data: VoCInput) -> VoCOutput:
        """워크플로 실행 (이벤트 발행 포함)"""
        self.logger.info(
            "Starting VoC Mining pipeline with events",
            source_type=input_data.source_type,
            play_id=input_data.play_id,
        )

        # 실행 시작 이벤트
        await self.emitter.emit_run_started(
            workflow_id="WF-03",
            input_data={
                "source_type": input_data.source_type,
                "play_id": input_data.play_id,
                "source": input_data.source,
                "channel": input_data.channel,
                "min_frequency": input_data.min_frequency,
                "max_themes": input_data.max_themes,
            },
            steps=self.STEPS,
        )

        try:
            # Step 1: 데이터 로딩
            await self.emitter.emit_step_started(
                step_id="DATA_LOADING",
                step_index=0,
                step_label="데이터 로딩",
                message=f"{input_data.source_type} 데이터를 로딩하고 있습니다...",
            )
            records = await self._load_data(input_data)
            await self.emitter.emit_step_finished(
                step_id="DATA_LOADING",
                step_index=0,
                result={"records_count": len(records)},
            )

            # Step 2: 전처리
            await self.emitter.emit_step_started(
                step_id="DATA_PREPROCESSING",
                step_index=1,
                step_label="데이터 전처리",
                message="중복 제거 및 정규화를 진행합니다...",
            )
            records = await self._preprocess(records)
            await self.emitter.emit_step_finished(
                step_id="DATA_PREPROCESSING",
                step_index=1,
                result={"unique_records": len(records)},
            )

            # Step 3: 테마 추출
            await self.emitter.emit_step_started(
                step_id="THEME_EXTRACTION",
                step_index=2,
                step_label="테마 추출",
                message="VoC 데이터에서 테마를 추출하고 있습니다...",
            )
            themes = await self._analyze_themes(input_data)

            # 테마 Surface 발행
            for theme in themes:
                await self.emitter.emit_surface(
                    surface_id=f"theme-{theme['theme_id']}",
                    surface={
                        "id": f"theme-{theme['theme_id']}",
                        "type": "voc_theme",
                        "title": f"테마: {theme['name']}",
                        "theme": theme,
                    },
                )

            await self.emitter.emit_step_finished(
                step_id="THEME_EXTRACTION",
                step_index=2,
                result={"themes_count": len(themes)},
            )

            # Step 4: Signal 생성
            await self.emitter.emit_step_started(
                step_id="SIGNAL_GENERATION",
                step_index=3,
                step_label="Signal 생성",
                message=f"{len(themes)}개 테마에서 Signal을 생성합니다...",
            )
            signals = await self._create_signals(themes, input_data.play_id)

            # Signal Surface 발행
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
                step_id="SIGNAL_GENERATION",
                step_index=3,
                result={"signals_count": len(signals)},
            )

            # Step 5: Brief 후보 선정
            await self.emitter.emit_step_started(
                step_id="BRIEF_SELECTION",
                step_index=4,
                step_label="Brief 후보 선정",
                message="Brief 후보를 선정합니다...",
            )
            brief_candidates = await self._select_brief_candidates(signals)

            # Brief 후보 Surface 발행
            for candidate in brief_candidates:
                await self.emitter.emit_surface(
                    surface_id=f"brief-candidate-{candidate['signal_id']}",
                    surface={
                        "id": f"brief-candidate-{candidate['signal_id']}",
                        "type": "brief_candidate",
                        "title": f"Brief 후보: {candidate['title']}",
                        "candidate": {
                            "signal_id": candidate["signal_id"],
                            "title": candidate["title"],
                            "confidence": candidate.get("confidence", 0.7),
                        },
                    },
                )

            await self.emitter.emit_step_finished(
                step_id="BRIEF_SELECTION",
                step_index=4,
                result={"candidates_count": len(brief_candidates)},
            )

            # 결과 요약
            summary = {
                "total_records": len(records),
                "themes_found": len(themes),
                "signals_created": len(signals),
                "brief_candidates": len(brief_candidates),
            }

            result = VoCOutput(
                themes=themes,
                signals=signals,
                brief_candidates=brief_candidates,
                summary=summary,
            )

            # 실행 완료 이벤트
            await self.emitter.emit_run_finished(result=summary)

            self.logger.info("VoC Mining pipeline with events completed", **summary)

            return result

        except Exception as e:
            self.logger.error("Pipeline error", error=str(e))
            await self.emitter.emit_run_error(str(e), recoverable=False)
            raise


# ============================================================
# DB 연동 버전
# ============================================================


class VoCMiningPipelineWithDB(VoCMiningPipelineWithEvents):
    """
    WF-03: VoC Mining with DB Integration

    데이터베이스 연동을 포함한 완전한 파이프라인
    """

    def __init__(self, emitter: "WorkflowEventEmitter", db: "AsyncSession"):
        super().__init__(emitter)
        self.db = db
        self.logger = logger.bind(workflow="WF-03", with_db=True)

    async def save_to_db(
        self,
        signals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """결과를 DB에 저장"""
        from backend.database.models.signal import SignalStatus
        from backend.database.repositories.signal import signal_repo

        saved = {"signals": []}

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

        await self.db.commit()
        return saved


# ============================================================
# 워크플로 인스턴스 및 진입점
# ============================================================

workflow = VoCMiningPipeline()


async def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """워크플로 진입점"""
    voc_input = VoCInput(
        data_source=input_data.get("data_source"),
        source_type=input_data.get("source_type", "text"),
        file_content=input_data.get("file_content"),
        api_data=input_data.get("api_data"),
        text_content=input_data.get("text_content"),
        play_id=input_data.get("play_id", "KT_Desk_V01_VoC"),
        source=input_data.get("source", "KT"),
        channel=input_data.get("channel", "데스크리서치"),
        min_frequency=input_data.get("min_frequency", 5),
        max_themes=input_data.get("max_themes", 5),
    )

    result = await workflow.run(voc_input)

    return {
        "themes": result.themes,
        "signals": result.signals,
        "brief_candidates": result.brief_candidates,
    }


async def run_with_events(
    input_data: dict[str, Any], emitter: "WorkflowEventEmitter"
) -> dict[str, Any]:
    """이벤트 발행을 포함한 워크플로 실행"""
    voc_input = VoCInput(
        data_source=input_data.get("data_source"),
        source_type=input_data.get("source_type", "text"),
        file_content=input_data.get("file_content"),
        api_data=input_data.get("api_data"),
        text_content=input_data.get("text_content"),
        play_id=input_data.get("play_id", "KT_Desk_V01_VoC"),
        source=input_data.get("source", "KT"),
        channel=input_data.get("channel", "데스크리서치"),
        min_frequency=input_data.get("min_frequency", 5),
        max_themes=input_data.get("max_themes", 5),
    )

    pipeline = VoCMiningPipelineWithEvents(emitter)
    result = await pipeline.run(voc_input)

    return {
        "themes": result.themes,
        "signals": result.signals,
        "brief_candidates": result.brief_candidates,
        "summary": result.summary,
    }


# 타입 힌트를 위한 import (순환 참조 방지)
if __name__ != "__main__":
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.agent_runtime.event_manager import WorkflowEventEmitter
