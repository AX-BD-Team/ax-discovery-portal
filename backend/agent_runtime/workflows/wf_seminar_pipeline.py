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
        # TODO: ConfluenceSync 에이전트 호출
        self.logger.info("Updating Confluence", activity_id=activity.activity_id)
        return False  # 아직 미구현


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
