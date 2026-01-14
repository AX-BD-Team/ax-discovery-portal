"""
WF-01: Seminar Pipeline

세미나/컨퍼런스 참석 자동화 워크플로
URL → Activity → AAR 템플릿 → Signal 추출 → Confluence 기록
"""

import re
from datetime import datetime
from typing import Any
from dataclasses import dataclass
import structlog
import httpx

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
        signals = []  # 초기에는 빈 목록
        
        result = SeminarPipelineResult(
            activity=activity,
            aar_template=aar,
            signals=signals,
            confluence_live_doc_updated=confluence_updated
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
                    "fetched_at": datetime.utcnow().isoformat()
                }
        except Exception as e:
            self.logger.warning("Failed to extract metadata", error=str(e))
            return {
                "url": url,
                "title": "세미나",
                "description": "",
                "date": None,
                "organizer": None,
                "fetched_at": datetime.utcnow().isoformat()
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
            r'(\d{4}[-./]\d{1,2}[-./]\d{1,2})',
            r'(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)',
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
            r'주최[:\s]*([^<\n]+)',
            r'organizer[:\s]*([^<\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]
        
        return None
    
    async def _create_activity(
        self,
        input_data: SeminarInput,
        metadata: dict[str, Any]
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
            }
        )
        
        self.logger.info("Activity created", activity_id=activity_id)
        return activity
    
    async def _generate_aar_template(
        self,
        activity: ActivityOutput,
        metadata: dict[str, Any]
    ) -> AARTemplate:
        """AAR 템플릿 생성"""
        content = f"""## After Action Review: {activity.title}

**일시**: {activity.date or 'TBD'}
**주최**: {metadata.get('organizer') or 'TBD'}
**참석자**: 

---

### 1. 핵심 인사이트 (3개)
1. 
2. 
3. 

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
*생성일: {datetime.now().strftime('%Y-%m-%d')}*
"""
        
        aar = AARTemplate(
            activity_id=activity.activity_id,
            content=content,
            confluence_url=None  # 나중에 업데이트
        )
        
        self.logger.info("AAR template generated", activity_id=activity.activity_id)
        return aar
    
    async def _update_confluence(self, activity: ActivityOutput) -> bool:
        """Confluence Live doc 업데이트"""
        from backend.integrations.mcp_confluence.server import ConfluenceMCP
        import os

        mcp = ConfluenceMCP()

        try:
            # 1. Action Log 기록
            action_log_page_id = os.getenv("CONFLUENCE_ACTION_LOG_PAGE_ID", "")
            if action_log_page_id:
                log_entry = f"""
## {activity.activity_id} - {activity.title}

- **일시**: {activity.date or 'TBD'}
- **Play**: {activity.play_id}
- **URL**: {activity.url}
- **상태**: {activity.status}
- **생성**: {datetime.now().strftime('%Y-%m-%d %H:%M KST')}

---
"""
                await mcp.append_to_page(
                    page_id=action_log_page_id,
                    append_md=log_entry
                )

            # 2. Play DB 업데이트
            play_db_page_id = os.getenv("CONFLUENCE_PLAY_DB_PAGE_ID", "")
            if play_db_page_id:
                await mcp.increment_play_activity_count(
                    page_id=play_db_page_id,
                    play_id=activity.play_id
                )

            self.logger.info("Confluence updated", activity_id=activity.activity_id)
            return True

        except Exception as e:
            self.logger.error("Confluence update failed", error=str(e))
            return False


# 워크플로 인스턴스
seminar_pipeline = SeminarPipeline()


async def run_seminar_pipeline(
    url: str,
    themes: list[str] | None = None,
    play_id: str = "EXT_Desk_D01_Seminar"
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


# 타입 힌트를 위한 import (순환 참조 방지)
if __name__ != "__main__":
    from backend.agent_runtime.event_manager import WorkflowEventEmitter
