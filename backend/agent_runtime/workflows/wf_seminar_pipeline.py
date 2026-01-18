"""
WF-01: Seminar Pipeline

세미나/컨퍼런스 참석 자동화 워크플로
URL → Activity → AAR 템플릿 → Signal 추출 → Confluence 기록
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class SeminarInput:
    """세미나 입력 데이터"""

    url: str
    themes: list[str] | None = None
    play_id: str = "EXT_Desk_D01_Seminar"


@dataclass
class ActivityOutput:
    """Activity 출력"""

    activity_id: str
    title: str
    source: str
    channel: str
    play_id: str
    url: str
    date: str | None
    status: str
    metadata: dict[str, Any]


@dataclass
class AARTemplate:
    """AAR 템플릿"""

    activity_id: str
    content: str
    confluence_url: str | None = None


@dataclass
class SeminarPipelineResult:
    """워크플로 결과"""

    activity: ActivityOutput
    aar_template: AARTemplate
    signals: list[dict[str, Any]]
    confluence_live_doc_updated: bool


class SeminarPipeline:
    """
    WF-01: Seminar Pipeline

    세미나 등록 → Activity 생성 → AAR 템플릿 → Signal 추출
    """

    def __init__(self):
        self.logger = logger.bind(workflow="WF-01")

    async def run(self, input_data: SeminarInput) -> SeminarPipelineResult:
        """워크플로 실행"""
        self.logger.info("Starting seminar pipeline", url=input_data.url)

        # 1. URL 메타데이터 추출
        metadata = await self._extract_metadata(input_data.url)

        # 2. Activity 생성
        activity = await self._create_activity(input_data, metadata)

        # 3. AAR 템플릿 생성
        aar = await self._generate_aar_template(activity, metadata)

        # 4. Confluence Live doc 업데이트
        confluence_updated = await self._update_confluence(activity)

        # 5. Signal 초기 후보 (세미나 참석 후 AAR 작성 시 추출)
        signals: list[dict[str, Any]] = []  # 초기에는 빈 목록

        result = SeminarPipelineResult(
            activity=activity,
            aar_template=aar,
            signals=signals,
            confluence_live_doc_updated=confluence_updated,
        )

        self.logger.info("Seminar pipeline completed", activity_id=activity.activity_id)
        return result

    async def _extract_metadata(self, url: str) -> dict[str, Any]:
        """URL에서 메타데이터 추출"""
        self.logger.info("Extracting metadata from URL", url=url)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True, timeout=10)
                html = response.text

                # 기본 메타데이터 추출
                title = self._extract_title(html)
                description = self._extract_meta(html, "description")
                date = self._extract_date(html)

                return {
                    "url": url,
                    "title": title,
                    "description": description,
                    "date": date,
                    "organizer": self._extract_organizer(html),
                    "fetched_at": datetime.now(UTC).isoformat(),
                }
        except Exception as e:
            self.logger.warning("Failed to extract metadata", error=str(e))
            return {
                "url": url,
                "title": "세미나",
                "description": "",
                "date": None,
                "organizer": None,
                "fetched_at": datetime.now(UTC).isoformat(),
            }

    def _extract_title(self, html: str) -> str:
        """HTML에서 제목 추출"""
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        if match:
            return match.group(1).strip()

        return "세미나"

    def _extract_meta(self, html: str, name: str) -> str:
        """HTML에서 meta 태그 추출"""
        pattern = rf'<meta[^>]+name="{name}"[^>]+content="([^"]+)"'
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        pattern = rf'<meta[^>]+property="og:{name}"[^>]+content="([^"]+)"'
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return ""

    def _extract_date(self, html: str) -> str | None:
        """HTML에서 날짜 추출"""
        # 날짜 패턴 (YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD)
        patterns = [
            r"(\d{4}[-./]\d{1,2}[-./]\d{1,2})",
            r"(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)",
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)

        return None

    def _extract_organizer(self, html: str) -> str | None:
        """HTML에서 주최자 추출"""
        # 간단한 휴리스틱
        patterns = [
            r"주최[:\s]*([^<\n]+)",
            r"organizer[:\s]*([^<\n]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]

        return None

    async def _create_activity(
        self, input_data: SeminarInput, metadata: dict[str, Any]
    ) -> ActivityOutput:
        """Activity 생성"""
        activity_id = f"ACT-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M%S')}"

        activity = ActivityOutput(
            activity_id=activity_id,
            title=metadata.get("title", "세미나"),
            source="대외",
            channel="데스크리서치",
            play_id=input_data.play_id,
            url=input_data.url,
            date=metadata.get("date"),
            status="REGISTERED",
            metadata={
                "themes": input_data.themes or [],
                "organizer": metadata.get("organizer"),
                "description": metadata.get("description"),
            },
        )

        self.logger.info("Activity created", activity_id=activity_id)
        return activity

    async def _generate_aar_template(
        self, activity: ActivityOutput, metadata: dict[str, Any]
    ) -> AARTemplate:
        """AAR 템플릿 생성"""
        content = f"""## After Action Review: {activity.title}

**일시**: {activity.date or "TBD"}
**주최**: {metadata.get("organizer") or "TBD"}
**참석자**: (작성 필요)

---

### 1. 핵심 인사이트 (3개)
1. (작성 필요)
2. (작성 필요)
3. (작성 필요)

### 2. AX BD 관련성
- 관련 Play: {activity.play_id}
- 잠재 기회:

### 3. Follow-up Actions
- [ ] 발표자료 확보
- [ ] 담당자 연락처 확보
- [ ] Signal 등록

### 4. Signal 후보
| 제목 | Pain/Need | 근거 |
|------|----------|------|
| | | |
| | | |

### 5. 종합 평가
- 참석 가치: ⭐⭐⭐☆☆
- 재참석 의사: Y/N

---
*Activity ID: {activity.activity_id}*
*생성일: {datetime.now().strftime("%Y-%m-%d")}*
"""

        aar = AARTemplate(
            activity_id=activity.activity_id,
            content=content,
            confluence_url=None,  # 나중에 업데이트
        )

        self.logger.info("AAR template generated", activity_id=activity.activity_id)
        return aar

    async def _update_confluence(self, activity: ActivityOutput) -> bool:
        """Confluence Live doc 업데이트"""
        import os

        from backend.integrations.mcp_confluence.server import ConfluenceMCP

        mcp = ConfluenceMCP()

        try:
            # 1. Action Log 기록
            action_log_page_id = os.getenv("CONFLUENCE_ACTION_LOG_PAGE_ID", "")
            if action_log_page_id:
                log_entry = f"""
## {activity.activity_id} - {activity.title}

- **일시**: {activity.date or "TBD"}
- **Play**: {activity.play_id}
- **URL**: {activity.url}
- **상태**: {activity.status}
- **생성**: {datetime.now().strftime("%Y-%m-%d %H:%M KST")}

---
"""
                await mcp.append_to_page(page_id=action_log_page_id, append_md=log_entry)

            # 2. Play DB 업데이트
            play_db_page_id = os.getenv("CONFLUENCE_PLAY_DB_PAGE_ID", "")
            if play_db_page_id:
                await mcp.increment_play_activity_count(
                    page_id=play_db_page_id, play_id=activity.play_id
                )

            self.logger.info("Confluence updated", activity_id=activity.activity_id)
            return True

        except Exception as e:
            self.logger.error("Confluence update failed", error=str(e))
            return False


# 워크플로 인스턴스
seminar_pipeline = SeminarPipeline()


async def run_seminar_pipeline(
    url: str, themes: list[str] | None = None, play_id: str = "EXT_Desk_D01_Seminar"
) -> SeminarPipelineResult:
    """세미나 파이프라인 실행 (편의 함수)"""
    input_data = SeminarInput(url=url, themes=themes, play_id=play_id)
    return await seminar_pipeline.run(input_data)


# AG-UI 이벤트 발행을 포함한 파이프라인
class SeminarPipelineWithEvents(SeminarPipeline):
    """
    WF-01: Seminar Pipeline with AG-UI Events

    실시간 이벤트 발행을 포함한 세미나 파이프라인
    SSE 스트리밍을 통해 클라이언트에 진행 상황 전달
    """

    # 단계 정의
    STEPS = [
        {"id": "METADATA_EXTRACTION", "label": "메타데이터 추출"},
        {"id": "ACTIVITY_CREATION", "label": "Activity 생성"},
        {"id": "AAR_TEMPLATE_GENERATION", "label": "AAR 템플릿 생성"},
        {"id": "CONFLUENCE_UPDATE", "label": "Confluence 업데이트"},
    ]

    def __init__(self, emitter: "WorkflowEventEmitter"):
        super().__init__()
        self.emitter = emitter
        self.logger = logger.bind(workflow="WF-01", with_events=True)

    async def run(self, input_data: SeminarInput) -> SeminarPipelineResult:
        """워크플로 실행 (이벤트 발행 포함)"""
        self.logger.info("Starting seminar pipeline with events", url=input_data.url)

        # 실행 시작 이벤트
        await self.emitter.emit_run_started(
            workflow_id="WF-01",
            input_data={
                "url": input_data.url,
                "themes": input_data.themes,
                "play_id": input_data.play_id,
            },
            steps=self.STEPS,
        )

        try:
            # Step 1: 메타데이터 추출
            await self.emitter.emit_step_started(
                step_id="METADATA_EXTRACTION",
                step_index=0,
                step_label="메타데이터 추출",
                message=f"URL에서 세미나 정보를 추출하고 있습니다: {input_data.url}",
            )
            metadata = await self._extract_metadata(input_data.url)
            await self.emitter.emit_step_finished(
                step_id="METADATA_EXTRACTION",
                step_index=0,
                result={"title": metadata.get("title"), "date": metadata.get("date")},
            )

            # Step 2: Activity 생성
            await self.emitter.emit_step_started(
                step_id="ACTIVITY_CREATION",
                step_index=1,
                step_label="Activity 생성",
                message="Activity를 생성하고 있습니다...",
            )
            activity = await self._create_activity(input_data, metadata)

            # Activity 미리보기 Surface 발행
            await self.emitter.emit_surface(
                surface_id=f"activity-{activity.activity_id}",
                surface={
                    "id": f"activity-{activity.activity_id}",
                    "type": "activity_preview",
                    "title": "Activity 생성 완료",
                    "activity": {
                        "activity_id": activity.activity_id,
                        "title": activity.title,
                        "date": activity.date,
                        "organizer": activity.metadata.get("organizer"),
                        "url": activity.url,
                        "play_id": activity.play_id,
                        "themes": activity.metadata.get("themes", []),
                        "source": activity.source,
                        "channel": activity.channel,
                        "status": activity.status,
                    },
                },
            )
            await self.emitter.emit_step_finished(
                step_id="ACTIVITY_CREATION",
                step_index=1,
                result={"activity_id": activity.activity_id},
            )

            # Step 3: AAR 템플릿 생성
            await self.emitter.emit_step_started(
                step_id="AAR_TEMPLATE_GENERATION",
                step_index=2,
                step_label="AAR 템플릿 생성",
                message="AAR(After Action Review) 템플릿을 생성하고 있습니다...",
            )
            aar = await self._generate_aar_template(activity, metadata)

            # AAR 템플릿 Surface 발행
            await self.emitter.emit_surface(
                surface_id=f"aar-{activity.activity_id}",
                surface={
                    "id": f"aar-{activity.activity_id}",
                    "type": "aar_template",
                    "title": "AAR 템플릿",
                    "activityId": aar.activity_id,
                    "content": aar.content,
                    "confluenceUrl": aar.confluence_url,
                },
            )
            await self.emitter.emit_step_finished(
                step_id="AAR_TEMPLATE_GENERATION",
                step_index=2,
            )

            # Step 4: Confluence 업데이트
            await self.emitter.emit_step_started(
                step_id="CONFLUENCE_UPDATE",
                step_index=3,
                step_label="Confluence 업데이트",
                message="Confluence에 Activity를 기록하고 있습니다...",
            )
            confluence_updated = await self._update_confluence(activity)
            await self.emitter.emit_step_finished(
                step_id="CONFLUENCE_UPDATE",
                step_index=3,
                result={"confluence_updated": confluence_updated},
            )

            # Signal 초기 후보
            signals: list[dict[str, Any]] = []

            # 결과 생성
            result = SeminarPipelineResult(
                activity=activity,
                aar_template=aar,
                signals=signals,
                confluence_live_doc_updated=confluence_updated,
            )

            # 실행 완료 이벤트
            await self.emitter.emit_run_finished(
                result={
                    "activity_id": activity.activity_id,
                    "title": activity.title,
                    "confluence_updated": confluence_updated,
                    "signals_count": len(signals),
                }
            )

            self.logger.info(
                "Seminar pipeline with events completed",
                activity_id=activity.activity_id,
            )
            return result

        except Exception as e:
            self.logger.error("Seminar pipeline error", error=str(e))
            await self.emitter.emit_run_error(str(e), recoverable=False)
            raise


# 온톨로지 통합 파이프라인
@dataclass
class SeminarOntologyInput:
    """온톨로지 통합을 위한 세미나 입력 데이터"""

    url: str
    aar_content: str | None = None  # AAR 문서 내용 (엔티티 추출용)
    themes: list[str] | None = None
    play_id: str = "EXT_Desk_D01_Seminar"


@dataclass
class OntologyResult:
    """온톨로지 생성 결과"""

    activity_entity_id: str | None = None
    signal_entity_ids: list[str] | None = None
    entity_count: int = 0
    triple_count: int = 0
    extraction_notes: str | None = None

    def __post_init__(self) -> None:
        if self.signal_entity_ids is None:
            self.signal_entity_ids = []


@dataclass
class SeminarPipelineWithOntologyResult:
    """온톨로지 통합 워크플로 결과"""

    activity: ActivityOutput
    aar_template: AARTemplate
    signals: list[dict[str, Any]]
    confluence_live_doc_updated: bool
    ontology: OntologyResult


class SeminarPipelineWithOntology(SeminarPipelineWithEvents):
    """
    WF-01: Seminar Pipeline with Ontology Integration

    세미나 워크플로 + 온톨로지 자동 생성:
    URL → Activity → Activity Entity → AAR → LLM 추출 → Entity Resolution → Signal/Triple 생성

    단계:
    1. METADATA_EXTRACTION: URL 메타데이터 추출
    2. ACTIVITY_CREATION: Activity 생성
    3. ACTIVITY_ENTITY_CREATION: Activity → Entity 변환
    4. AAR_TEMPLATE_GENERATION: AAR 템플릿 생성
    5. ENTITY_EXTRACTION: LLM 엔티티 추출
    6. RELATION_EXTRACTION: LLM 관계 추출
    7. ENTITY_RESOLUTION: 동일 엔티티 식별/병합
    8. SIGNAL_CREATION: Signal Entity 생성
    9. TRIPLE_CREATION: 관계 Triple 생성
    10. CONFLUENCE_UPDATE: Confluence 업데이트
    """

    # 확장된 단계 정의
    STEPS = [
        {"id": "METADATA_EXTRACTION", "label": "메타데이터 추출"},
        {"id": "ACTIVITY_CREATION", "label": "Activity 생성"},
        {"id": "ACTIVITY_ENTITY_CREATION", "label": "Activity Entity 생성"},
        {"id": "AAR_TEMPLATE_GENERATION", "label": "AAR 템플릿 생성"},
        {"id": "ENTITY_EXTRACTION", "label": "엔티티 추출"},
        {"id": "RELATION_EXTRACTION", "label": "관계 추출"},
        {"id": "ENTITY_RESOLUTION", "label": "엔티티 해결"},
        {"id": "SIGNAL_CREATION", "label": "Signal 생성"},
        {"id": "TRIPLE_CREATION", "label": "Triple 생성"},
        {"id": "CONFLUENCE_UPDATE", "label": "Confluence 업데이트"},
    ]

    def __init__(self, emitter: "WorkflowEventEmitter", db_session=None):
        super().__init__(emitter)
        self.db_session = db_session
        self.logger = logger.bind(workflow="WF-01", with_ontology=True)

    async def run_with_ontology(
        self, input_data: SeminarOntologyInput
    ) -> SeminarPipelineWithOntologyResult:
        """온톨로지 통합 워크플로 실행"""
        from backend.services.llm_extraction_service import llm_extraction_service
        from backend.services.ontology_integration_service import ontology_integration_service

        self.logger.info(
            "Starting seminar pipeline with ontology",
            url=input_data.url,
            has_aar=input_data.aar_content is not None,
        )

        # 실행 시작 이벤트
        await self.emitter.emit_run_started(
            workflow_id="WF-01-ONTOLOGY",
            input_data={
                "url": input_data.url,
                "themes": input_data.themes,
                "play_id": input_data.play_id,
                "has_aar_content": input_data.aar_content is not None,
            },
            steps=self.STEPS,
        )

        ontology_result = OntologyResult()

        try:
            # Step 1: 메타데이터 추출
            await self.emitter.emit_step_started(
                step_id="METADATA_EXTRACTION",
                step_index=0,
                step_label="메타데이터 추출",
                message=f"URL에서 세미나 정보를 추출하고 있습니다: {input_data.url}",
            )
            metadata = await self._extract_metadata(input_data.url)
            await self.emitter.emit_step_finished(
                step_id="METADATA_EXTRACTION",
                step_index=0,
                result={"title": metadata.get("title"), "date": metadata.get("date")},
            )

            # Step 2: Activity 생성
            await self.emitter.emit_step_started(
                step_id="ACTIVITY_CREATION",
                step_index=1,
                step_label="Activity 생성",
                message="Activity를 생성하고 있습니다...",
            )
            seminar_input = SeminarInput(
                url=input_data.url,
                themes=input_data.themes,
                play_id=input_data.play_id,
            )
            activity = await self._create_activity(seminar_input, metadata)

            await self.emitter.emit_surface(
                surface_id=f"activity-{activity.activity_id}",
                surface={
                    "id": f"activity-{activity.activity_id}",
                    "type": "activity_preview",
                    "title": "Activity 생성 완료",
                    "activity": {
                        "activity_id": activity.activity_id,
                        "title": activity.title,
                        "date": activity.date,
                        "url": activity.url,
                        "play_id": activity.play_id,
                    },
                },
            )
            await self.emitter.emit_step_finished(
                step_id="ACTIVITY_CREATION",
                step_index=1,
                result={"activity_id": activity.activity_id},
            )

            # Step 3: Activity Entity 생성
            await self.emitter.emit_step_started(
                step_id="ACTIVITY_ENTITY_CREATION",
                step_index=2,
                step_label="Activity Entity 생성",
                message="Activity를 온톨로지 Entity로 변환하고 있습니다...",
            )

            if self.db_session:
                activity_entity = await ontology_integration_service.create_activity_entity(
                    db=self.db_session,
                    activity_id=activity.activity_id,
                    title=activity.title,
                    activity_type="seminar",
                    url=activity.url,
                    date=activity.date,
                    created_by="WF-01-ONTOLOGY",
                )
                ontology_result.activity_entity_id = activity_entity.entity_id
                ontology_result.entity_count += 1

            await self.emitter.emit_step_finished(
                step_id="ACTIVITY_ENTITY_CREATION",
                step_index=2,
                result={"activity_entity_id": ontology_result.activity_entity_id},
            )

            # Step 4: AAR 템플릿 생성
            await self.emitter.emit_step_started(
                step_id="AAR_TEMPLATE_GENERATION",
                step_index=3,
                step_label="AAR 템플릿 생성",
                message="AAR 템플릿을 생성하고 있습니다...",
            )
            aar = await self._generate_aar_template(activity, metadata)

            await self.emitter.emit_surface(
                surface_id=f"aar-{activity.activity_id}",
                surface={
                    "id": f"aar-{activity.activity_id}",
                    "type": "aar_template",
                    "title": "AAR 템플릿",
                    "activityId": aar.activity_id,
                    "content": aar.content,
                },
            )
            await self.emitter.emit_step_finished(
                step_id="AAR_TEMPLATE_GENERATION",
                step_index=3,
            )

            # AAR 내용이 있으면 엔티티/관계 추출 진행
            signals: list[dict[str, Any]] = []

            if input_data.aar_content and self.db_session:
                # Step 5: 엔티티 추출
                await self.emitter.emit_step_started(
                    step_id="ENTITY_EXTRACTION",
                    step_index=4,
                    step_label="엔티티 추출",
                    message="AAR 문서에서 엔티티를 추출하고 있습니다...",
                )
                extracted_entities = await llm_extraction_service.extract_entities(
                    input_data.aar_content
                )
                await self.emitter.emit_step_finished(
                    step_id="ENTITY_EXTRACTION",
                    step_index=4,
                    result={"entity_count": len(extracted_entities)},
                )

                # Step 6: 관계 추출
                await self.emitter.emit_step_started(
                    step_id="RELATION_EXTRACTION",
                    step_index=5,
                    step_label="관계 추출",
                    message="엔티티 간 관계를 추출하고 있습니다...",
                )
                extracted_relations = await llm_extraction_service.extract_relations(
                    input_data.aar_content, extracted_entities
                )
                await self.emitter.emit_step_finished(
                    step_id="RELATION_EXTRACTION",
                    step_index=5,
                    result={"relation_count": len(extracted_relations)},
                )

                # Step 7: Entity Resolution
                await self.emitter.emit_step_started(
                    step_id="ENTITY_RESOLUTION",
                    step_index=6,
                    step_label="엔티티 해결",
                    message="동일 엔티티를 식별하고 병합하고 있습니다...",
                )
                from backend.services.llm_extraction_service import ExtractionResult

                extraction_result = ExtractionResult(
                    entities=extracted_entities,
                    relations=extracted_relations,
                )
                await self.emitter.emit_step_finished(
                    step_id="ENTITY_RESOLUTION",
                    step_index=6,
                    result={"entities": len(extracted_entities)},
                )

                # Step 8: Signal 생성
                await self.emitter.emit_step_started(
                    step_id="SIGNAL_CREATION",
                    step_index=7,
                    step_label="Signal 생성",
                    message="Signal Entity를 생성하고 있습니다...",
                )
                # Signal 엔티티 개수 세기
                signal_entities = [e for e in extracted_entities if e.entity_type.value == "Signal"]
                await self.emitter.emit_step_finished(
                    step_id="SIGNAL_CREATION",
                    step_index=7,
                    result={"signal_count": len(signal_entities)},
                )

                # Step 9: Triple 생성
                await self.emitter.emit_step_started(
                    step_id="TRIPLE_CREATION",
                    step_index=8,
                    step_label="Triple 생성",
                    message="온톨로지를 생성하고 있습니다...",
                )
                creation_result = await ontology_integration_service.create_from_extraction(
                    db=self.db_session,
                    extraction_result=extraction_result,
                    source_ref=activity.activity_id,
                    created_by="WF-01-ONTOLOGY",
                )

                ontology_result.entity_count += creation_result.entity_created_count
                ontology_result.triple_count = creation_result.triple_created_count
                ontology_result.signal_entity_ids = [
                    e.entity_id
                    for e in creation_result.created_entities
                    if e.entity_type.value == "Signal"
                ]
                ontology_result.extraction_notes = (
                    f"Created {creation_result.entity_created_count} entities, "
                    f"merged {creation_result.entity_merged_count}, "
                    f"created {creation_result.triple_created_count} triples"
                )

                # Surface로 온톨로지 결과 발행
                await self.emitter.emit_surface(
                    surface_id=f"ontology-{activity.activity_id}",
                    surface={
                        "id": f"ontology-{activity.activity_id}",
                        "type": "ontology_result",
                        "title": "온톨로지 생성 결과",
                        "activityId": activity.activity_id,
                        "entityCount": ontology_result.entity_count,
                        "tripleCount": ontology_result.triple_count,
                        "signalCount": len(ontology_result.signal_entity_ids),
                    },
                )

                await self.emitter.emit_step_finished(
                    step_id="TRIPLE_CREATION",
                    step_index=8,
                    result={
                        "entity_count": creation_result.entity_created_count,
                        "triple_count": creation_result.triple_created_count,
                    },
                )

                # Signal 정보를 결과에 추가
                for signal_entity in creation_result.created_entities:
                    if signal_entity.entity_type.value == "Signal":
                        props = signal_entity.properties or {}
                        signals.append(
                            {
                                "entity_id": signal_entity.entity_id,
                                "title": signal_entity.name,
                                "pain": props.get("pain", ""),
                            }
                        )

            else:
                # AAR 없으면 스킵
                for step_index, step in enumerate(self.STEPS[4:9], start=4):
                    await self.emitter.emit_step_started(
                        step_id=step["id"],
                        step_index=step_index,
                        step_label=step["label"],
                        message="AAR 내용이 없어 스킵합니다.",
                    )
                    await self.emitter.emit_step_finished(
                        step_id=step["id"],
                        step_index=step_index,
                        result={"skipped": True},
                    )

            # Step 10: Confluence 업데이트
            await self.emitter.emit_step_started(
                step_id="CONFLUENCE_UPDATE",
                step_index=9,
                step_label="Confluence 업데이트",
                message="Confluence에 기록하고 있습니다...",
            )
            confluence_updated = await self._update_confluence(activity)
            await self.emitter.emit_step_finished(
                step_id="CONFLUENCE_UPDATE",
                step_index=9,
                result={"confluence_updated": confluence_updated},
            )

            # 결과 생성
            result = SeminarPipelineWithOntologyResult(
                activity=activity,
                aar_template=aar,
                signals=signals,
                confluence_live_doc_updated=confluence_updated,
                ontology=ontology_result,
            )

            # 실행 완료 이벤트
            await self.emitter.emit_run_finished(
                result={
                    "activity_id": activity.activity_id,
                    "title": activity.title,
                    "confluence_updated": confluence_updated,
                    "signals_count": len(signals),
                    "ontology": {
                        "activity_entity_id": ontology_result.activity_entity_id,
                        "entity_count": ontology_result.entity_count,
                        "triple_count": ontology_result.triple_count,
                    },
                }
            )

            self.logger.info(
                "Seminar pipeline with ontology completed",
                activity_id=activity.activity_id,
                entity_count=ontology_result.entity_count,
                triple_count=ontology_result.triple_count,
            )

            return result

        except Exception as e:
            self.logger.error("Seminar pipeline with ontology error", error=str(e))
            await self.emitter.emit_run_error(str(e), recoverable=False)
            raise


# 타입 힌트를 위한 import (순환 참조 방지)
if __name__ != "__main__":
    from backend.agent_runtime.event_manager import WorkflowEventEmitter
