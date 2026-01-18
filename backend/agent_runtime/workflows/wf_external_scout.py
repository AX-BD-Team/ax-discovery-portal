"""
WF-07: External Scout Pipeline

외부 세미나/이벤트 정보를 자동으로 수집하여 Activity로 등록하는 워크플로

지원 소스:
- RSS 피드 (기술 블로그, 이벤트 사이트)
- OnOffMix (온오프믹스) - 한국 IT/스타트업 이벤트
- EventUs (이벤터스) - 한국 IT 이벤트
- DevEvent (GitHub) - 개발자 커뮤니티 이벤트
- Eventbrite - 글로벌 이벤트

⚠️ DEPRECATED 소스:
- Festa (festa.io) - 2025.01.31 서비스 종료

흐름:
1. 각 소스에서 AI/AX 관련 세미나 정보 수집
2. AI/AX 키워드 필터링
3. 중복 제거 (URL, external_id 기준)
4. Activity 생성 및 DB 저장
5. Confluence Action Log 기록
6. 결과 요약 반환
"""

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.repositories.activity import activity_repo
from backend.integrations.external_sources import (
    AI_AX_KEYWORDS,
    DevEventCollector,
    EventbriteCollector,
    EventUsCollector,
    FestaCollector,
    OnOffMixCollector,
    RSSCollector,
    SeminarInfo,
)

logger = structlog.get_logger()


@dataclass
class ExternalScoutInput:
    """외부 스카우트 입력 데이터"""

    # 수집 소스 (rss, onoffmix, eventus, devevent, eventbrite)
    # ⚠️ festa는 2025.01.31 서비스 종료로 사용 불가
    sources: list[str] = field(
        default_factory=lambda: ["rss", "onoffmix", "eventus", "devevent", "eventbrite"]
    )

    # 필터링 (기본: AI/AX 키워드)
    keywords: list[str] | None = field(
        default_factory=lambda: AI_AX_KEYWORDS[:10]
    )  # 상위 10개 AI/AX 키워드
    categories: list[str] | None = None  # 카테고리 필터

    # 소스별 설정
    rss_feed_urls: list[str] | None = None  # RSS 피드 URL 목록
    onoffmix_categories: list[str] | None = None  # 온오프믹스 카테고리 (it, startup)
    eventus_categories: list[str] | None = None  # 이벤터스 카테고리 (it, startup)
    devevent_months_back: int = 2  # Dev-Event 몇 개월 전까지 수집
    eventbrite_location: str | None = None  # Eventbrite 지역
    eventbrite_organizer_ids: list[str] | None = None  # Eventbrite 주최자 ID

    # 공통 설정
    limit_per_source: int = 50  # 소스당 최대 수집 개수
    play_id: str = "EXT_Desk_D01_Seminar"  # 기본 Play ID
    save_to_db: bool = True  # DB 저장 여부
    sync_confluence: bool = True  # Confluence 동기화 여부


@dataclass
class ExternalScoutOutput:
    """외부 스카우트 출력 데이터"""

    # 수집 결과
    total_collected: int  # 총 수집된 세미나 수
    total_saved: int  # DB에 저장된 Activity 수
    duplicates_skipped: int  # 중복으로 스킵된 수
    errors: list[dict[str, Any]]  # 에러 목록

    # 소스별 통계
    by_source: dict[str, dict[str, int]]  # {"rss": {"collected": 10, "saved": 8}}

    # 저장된 Activity 목록
    activities: list[dict[str, Any]]

    # Confluence 동기화 결과
    confluence_updated: bool
    confluence_url: str | None

    # 메타데이터
    started_at: str
    finished_at: str
    duration_seconds: float


class ExternalScoutPipeline:
    """
    WF-07: External Scout Pipeline

    외부 세미나 정보 배치 수집
    """

    def __init__(self):
        self.logger = logger.bind(workflow="WF-07")

        # 수집기 초기화
        self.collectors = {
            "rss": RSSCollector(),
            "onoffmix": OnOffMixCollector(),
            "eventus": EventUsCollector(),
            "devevent": DevEventCollector(),
            "eventbrite": EventbriteCollector(),
            # DEPRECATED: 2025.01.31 서비스 종료
            "festa": FestaCollector(),
        }

    async def run(self, input_data: ExternalScoutInput) -> ExternalScoutOutput:
        """워크플로 실행"""
        started_at = datetime.now(UTC)
        self.logger.info(
            "Starting external scout pipeline",
            sources=input_data.sources,
            keywords=input_data.keywords,
        )

        # 결과 초기화
        all_seminars: list[SeminarInfo] = []
        by_source: dict[str, dict[str, int]] = {}
        errors: list[dict[str, Any]] = []

        # 1. 각 소스에서 세미나 수집
        for source in input_data.sources:
            if source not in self.collectors:
                self.logger.warning(f"Unknown source: {source}")
                continue

            try:
                seminars = await self._collect_from_source(source, input_data)
                all_seminars.extend(seminars)
                by_source[source] = {
                    "collected": len(seminars),
                    "saved": 0,  # 나중에 업데이트
                }
                self.logger.info(
                    "Source collection completed",
                    source=source,
                    count=len(seminars),
                )
            except Exception as e:
                self.logger.error(
                    "Source collection failed",
                    source=source,
                    error=str(e),
                )
                errors.append(
                    {
                        "source": source,
                        "error": str(e),
                        "type": "collection",
                    }
                )

        total_collected = len(all_seminars)
        self.logger.info(f"Total collected: {total_collected} seminars")

        # 2. 중복 제거 (URL 기준)
        seen_urls = set()
        unique_seminars = []
        for seminar in all_seminars:
            if seminar.url not in seen_urls:
                seen_urls.add(seminar.url)
                unique_seminars.append(seminar)

        duplicates_in_batch = total_collected - len(unique_seminars)
        self.logger.info(
            "Duplicates removed in batch",
            original=total_collected,
            unique=len(unique_seminars),
            removed=duplicates_in_batch,
        )

        # 3. Activity 생성 결과
        activities: list[dict[str, Any]] = []
        total_saved = 0
        duplicates_skipped = duplicates_in_batch

        # 4. DB 저장 (옵션)
        if not input_data.save_to_db:
            # DB 저장 없이 수집 결과만 반환
            for seminar in unique_seminars:
                activity_data = seminar.to_activity_data()
                activity_data["play_id"] = input_data.play_id
                activities.append(activity_data)
        else:
            self.logger.info("DB 저장은 ExternalScoutPipelineWithDB를 사용하세요")
            for seminar in unique_seminars:
                activity_data = seminar.to_activity_data()
                activity_data["play_id"] = input_data.play_id
                activities.append(activity_data)

        # 5. 결과 생성
        finished_at = datetime.now(UTC)
        duration = (finished_at - started_at).total_seconds()

        result = ExternalScoutOutput(
            total_collected=total_collected,
            total_saved=total_saved,
            duplicates_skipped=duplicates_skipped,
            errors=errors,
            by_source=by_source,
            activities=activities,
            confluence_updated=False,
            confluence_url=None,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_seconds=duration,
        )

        self.logger.info(
            "External scout pipeline completed",
            total_collected=total_collected,
            unique=len(unique_seminars),
            duration=duration,
        )

        return result

    async def _collect_from_source(
        self,
        source: str,
        input_data: ExternalScoutInput,
    ) -> list[SeminarInfo]:
        """
        단일 소스에서 세미나 수집

        Args:
            source: 소스 타입
            input_data: 입력 데이터

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        collector = self.collectors[source]

        # 소스별 파라미터 구성
        kwargs: dict[str, Any] = {}

        if source == "rss":
            # RSS 피드 URL
            feed_urls = input_data.rss_feed_urls or self._get_default_rss_feeds()
            kwargs["feed_urls"] = feed_urls

        elif source == "onoffmix":
            # 온오프믹스 카테고리
            if input_data.onoffmix_categories:
                kwargs["categories"] = input_data.onoffmix_categories

        elif source == "eventus":
            # 이벤터스 카테고리
            if input_data.eventus_categories:
                kwargs["categories"] = input_data.eventus_categories

        elif source == "devevent":
            # Dev-Event 수집 기간
            kwargs["months_back"] = input_data.devevent_months_back

        elif source == "eventbrite":
            # Eventbrite 지역 및 주최자
            if input_data.eventbrite_location:
                kwargs["location"] = input_data.eventbrite_location
            if input_data.eventbrite_organizer_ids:
                kwargs["organizer_ids"] = input_data.eventbrite_organizer_ids

        elif source == "festa":
            # DEPRECATED: 경고 로그만 출력, 빈 결과 반환
            self.logger.warning(
                "Festa 수집기는 서비스 종료로 사용 불가",
                source=source,
                service_ended="2025-01-31",
            )

        # 공통 파라미터
        seminars = await collector.fetch_seminars(
            keywords=input_data.keywords,
            categories=input_data.categories,
            limit=input_data.limit_per_source,
            **kwargs,
        )

        return seminars

    def _get_default_rss_feeds(self) -> list[str]:
        """기본 RSS 피드 URL 목록"""
        # 환경변수에서 가져오기
        feeds_env = os.getenv("SEMINAR_RSS_FEEDS", "")
        if feeds_env:
            return [f.strip() for f in feeds_env.split(",") if f.strip()]

        # 기본 피드 (예시)
        return [
            # 기술 컨퍼런스/세미나 피드 예시
            # "https://example.com/tech-events.rss",
        ]


class ExternalScoutPipelineWithDB(ExternalScoutPipeline):
    """
    WF-07: External Scout Pipeline with DB

    DB 저장 및 Confluence 동기화 포함
    """

    def __init__(self, db: AsyncSession):
        super().__init__()
        self.db = db
        self.logger = logger.bind(workflow="WF-07", with_db=True)

    async def run(self, input_data: ExternalScoutInput) -> ExternalScoutOutput:
        """워크플로 실행 (DB 저장 포함)"""
        started_at = datetime.now(UTC)
        self.logger.info(
            "Starting external scout pipeline with DB",
            sources=input_data.sources,
            keywords=input_data.keywords,
        )

        # 결과 초기화
        all_seminars: list[SeminarInfo] = []
        by_source: dict[str, dict[str, int]] = {}
        errors: list[dict[str, Any]] = []

        # 1. 각 소스에서 세미나 수집
        for source in input_data.sources:
            if source not in self.collectors:
                self.logger.warning(f"Unknown source: {source}")
                continue

            try:
                seminars = await self._collect_from_source(source, input_data)
                all_seminars.extend(seminars)
                by_source[source] = {
                    "collected": len(seminars),
                    "saved": 0,
                }
            except Exception as e:
                self.logger.error(
                    "Source collection failed",
                    source=source,
                    error=str(e),
                )
                errors.append(
                    {
                        "source": source,
                        "error": str(e),
                        "type": "collection",
                    }
                )

        total_collected = len(all_seminars)

        # 2. 중복 제거 및 DB 저장
        activities: list[dict[str, Any]] = []
        total_saved = 0
        duplicates_skipped = 0

        for seminar in all_seminars:
            try:
                # 중복 체크
                existing = await activity_repo.check_duplicate(
                    self.db,
                    url=seminar.url,
                    title=seminar.title,
                    date=seminar.date,
                    external_id=seminar.external_id,
                )

                if existing:
                    duplicates_skipped += 1
                    self.logger.debug(
                        "Skipping duplicate activity",
                        url=seminar.url,
                        existing_id=existing.entity_id,
                    )
                    continue

                # Activity 생성
                activity_data = seminar.to_activity_data()
                activity_data["play_id"] = input_data.play_id

                entity = await activity_repo.create_activity(self.db, activity_data)
                total_saved += 1

                # 소스별 통계 업데이트
                source_type = seminar.source_type
                if source_type in by_source:
                    by_source[source_type]["saved"] += 1

                activities.append(entity.to_dict())

                self.logger.info(
                    "Activity saved",
                    activity_id=entity.entity_id,
                    title=entity.name[:50],
                )

            except Exception as e:
                self.logger.error(
                    "Failed to save activity",
                    url=seminar.url,
                    error=str(e),
                )
                errors.append(
                    {
                        "url": seminar.url,
                        "error": str(e),
                        "type": "save",
                    }
                )

        # 커밋
        await self.db.commit()

        # 3. Confluence 동기화 (옵션)
        confluence_updated = False
        confluence_url = None

        if input_data.sync_confluence and total_saved > 0:
            try:
                confluence_result = await self._sync_to_confluence(
                    activities,
                    input_data.play_id,
                )
                confluence_updated = confluence_result.get("success", False)
                confluence_url = confluence_result.get("page_url")
            except Exception as e:
                self.logger.error("Confluence sync failed", error=str(e))
                errors.append(
                    {
                        "type": "confluence_sync",
                        "error": str(e),
                    }
                )

        # 4. 결과 생성
        finished_at = datetime.now(UTC)
        duration = (finished_at - started_at).total_seconds()

        result = ExternalScoutOutput(
            total_collected=total_collected,
            total_saved=total_saved,
            duplicates_skipped=duplicates_skipped,
            errors=errors,
            by_source=by_source,
            activities=activities,
            confluence_updated=confluence_updated,
            confluence_url=confluence_url,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_seconds=duration,
        )

        self.logger.info(
            "External scout pipeline with DB completed",
            total_collected=total_collected,
            total_saved=total_saved,
            duplicates_skipped=duplicates_skipped,
            duration=duration,
        )

        return result

    async def _sync_to_confluence(
        self,
        activities: list[dict[str, Any]],
        play_id: str,
    ) -> dict[str, Any]:
        """
        Confluence에 수집 결과 동기화

        Args:
            activities: 저장된 Activity 목록
            play_id: Play ID

        Returns:
            dict: 동기화 결과
        """
        from backend.integrations.mcp_confluence.server import ConfluenceMCP

        mcp = ConfluenceMCP()

        try:
            # Action Log에 배치 수집 기록 추가
            action_log_page_id = os.getenv("CONFLUENCE_ACTION_LOG_PAGE_ID", "")
            if not action_log_page_id:
                return {"success": False, "error": "Action Log page ID not configured"}

            # 로그 항목 생성
            now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M KST")
            log_entry = f"""
## 🤖 External Scout 배치 수집 ({now})

**수집 결과**:
- 총 수집: {len(activities)}건
- Play: {play_id}

| Activity ID | 제목 | 날짜 | 소스 |
|-------------|------|------|------|
"""
            for act in activities[:10]:  # 최대 10개만 표시
                log_entry += f"| {act.get('entity_id', '-')} | {act.get('name', '-')[:30]} | {act.get('properties', {}).get('date', '-')} | {act.get('properties', {}).get('source_type', '-')} |\n"

            if len(activities) > 10:
                log_entry += f"\n... 외 {len(activities) - 10}건\n"

            log_entry += "\n---\n"

            await mcp.append_to_page(page_id=action_log_page_id, append_md=log_entry)

            # Play DB 업데이트 (activity_qtd 증가)
            play_db_page_id = os.getenv("CONFLUENCE_PLAY_DB_PAGE_ID", "")
            if play_db_page_id:
                for _ in activities:
                    await mcp.increment_play_activity_count(
                        page_id=play_db_page_id,
                        play_id=play_id,
                    )

            return {
                "success": True,
                "page_url": f"https://your-confluence.atlassian.net/wiki/spaces/AX/pages/{action_log_page_id}",
            }

        except Exception as e:
            self.logger.error("Confluence sync error", error=str(e))
            return {"success": False, "error": str(e)}


# 워크플로 인스턴스 (기본)
external_scout_pipeline = ExternalScoutPipeline()


async def run_external_scout(
    sources: list[str] | None = None,
    keywords: list[str] | None = None,
    categories: list[str] | None = None,
    limit_per_source: int = 50,
    play_id: str = "EXT_Desk_D01_Seminar",
) -> ExternalScoutOutput:
    """
    외부 스카우트 파이프라인 실행 (편의 함수)

    AI/AX 관련 세미나를 자동으로 수집합니다.

    Args:
        sources: 수집 소스 목록 (기본: rss, onoffmix, eventus, devevent, eventbrite)
        keywords: 필터 키워드 (기본: AI/AX 상위 10개 키워드)
        categories: 필터 카테고리
        limit_per_source: 소스당 최대 수집 개수
        play_id: Play ID

    Returns:
        ExternalScoutOutput: 수집 결과
    """
    input_data = ExternalScoutInput(
        sources=sources or ["rss", "onoffmix", "eventus", "devevent", "eventbrite"],
        keywords=keywords or AI_AX_KEYWORDS[:10],
        categories=categories,
        limit_per_source=limit_per_source,
        play_id=play_id,
        save_to_db=False,  # 기본 실행은 DB 저장 안함
    )
    return await external_scout_pipeline.run(input_data)
