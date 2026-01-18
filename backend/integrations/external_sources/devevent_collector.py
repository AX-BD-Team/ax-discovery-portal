"""
Dev-Event 수집기

GitHub brave-people/Dev-Event 저장소에서 개발자 이벤트 정보 수집
마크다운 기반 정적 파일 파싱
"""

import re
from datetime import UTC, datetime

import httpx
import structlog

from .base import BaseSeminarCollector, SeminarInfo
from .keywords import AI_AX_KEYWORDS, filter_by_ai_keywords, filter_excludes

logger = structlog.get_logger()


class DevEventCollector(BaseSeminarCollector):
    """
    Dev-Event (GitHub) 수집기

    brave-people/Dev-Event 저장소의 마크다운 파일에서
    개발자 이벤트 정보 수집
    """

    # GitHub Raw 파일 URL
    RAW_BASE_URL = "https://raw.githubusercontent.com/brave-people/Dev-Event/master"

    # GitHub API URL
    API_BASE_URL = "https://api.github.com/repos/brave-people/Dev-Event"

    def __init__(self):
        super().__init__(name="devevent")

    async def fetch_seminars(
        self,
        keywords: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> list[SeminarInfo]:
        """
        Dev-Event에서 세미나 정보 수집

        Args:
            keywords: 필터링할 키워드 (AI/AX 관련)
            categories: 미사용 (마크다운 기반이라 카테고리 구분 없음)
            limit: 최대 수집 개수
            months_back: 몇 개월 전까지 수집할지 (kwargs, 기본: 2)

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        search_keywords = keywords or AI_AX_KEYWORDS[:10]
        months_back = kwargs.get("months_back", 2)

        all_seminars: list[SeminarInfo] = []

        async with httpx.AsyncClient(timeout=30) as client:
            # 현재 월 + 이전 월 마크다운 파일 수집
            now = datetime.now()
            for month_offset in range(months_back + 1):
                year = now.year
                month = now.month - month_offset

                # 월 조정
                while month <= 0:
                    month += 12
                    year -= 1

                try:
                    seminars = await self._fetch_monthly_events(
                        client,
                        year,
                        month,
                        search_keywords,
                    )
                    all_seminars.extend(seminars)
                    logger.info(
                        "Dev-Event 월별 수집 완료",
                        year=year,
                        month=month,
                        count=len(seminars),
                    )
                except Exception as e:
                    logger.warning(
                        "Dev-Event 월별 수집 실패",
                        year=year,
                        month=month,
                        error=str(e),
                    )

            # README.md에서 현재 진행중 이벤트 추가 수집
            try:
                readme_seminars = await self._fetch_from_readme(client, search_keywords)
                all_seminars.extend(readme_seminars)
                logger.info(
                    "Dev-Event README 수집 완료",
                    count=len(readme_seminars),
                )
            except Exception as e:
                logger.warning("Dev-Event README 수집 실패", error=str(e))

        # 중복 제거 (URL 기준)
        seen_urls = set()
        unique_seminars = []
        for seminar in all_seminars:
            if seminar.url not in seen_urls:
                seen_urls.add(seminar.url)
                # 제외 키워드 필터링
                if not filter_excludes(f"{seminar.title} {seminar.description or ''}"):
                    unique_seminars.append(seminar)

        # AI/AX 키워드 필터링
        if keywords:
            unique_seminars = self.filter_by_keywords(unique_seminars, keywords)
        else:
            # 기본 AI/AX 필터
            unique_seminars = [
                s
                for s in unique_seminars
                if filter_by_ai_keywords(f"{s.title} {s.description or ''}", min_matches=1)
            ]

        # 날짜 범위 필터링
        if "start_date" in kwargs or "end_date" in kwargs:
            unique_seminars = self.filter_by_date_range(
                unique_seminars,
                kwargs.get("start_date"),
                kwargs.get("end_date"),
            )

        # 최신순 정렬
        unique_seminars.sort(
            key=lambda x: x.date or "9999-99-99",
            reverse=True,
        )

        return unique_seminars[:limit]

    async def _fetch_monthly_events(
        self,
        client: httpx.AsyncClient,
        year: int,
        month: int,
        keywords: list[str],
    ) -> list[SeminarInfo]:
        """
        월별 마크다운 파일에서 이벤트 수집

        Args:
            client: HTTP 클라이언트
            year: 연도
            month: 월
            keywords: 필터 키워드

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        seminars = []

        # 파일명 형식: {year}/{yy}_{mm}.md
        yy = str(year)[-2:]
        mm = f"{month:02d}"
        file_path = f"{year}/{yy}_{mm}.md"

        url = f"{self.RAW_BASE_URL}/{file_path}"

        try:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AXDiscoveryBot/1.0)",
                },
            )

            if response.status_code == 200:
                seminars = self._parse_markdown(
                    response.text,
                    keywords,
                    year,
                    month,
                )

        except Exception as e:
            logger.debug(
                "Dev-Event 월별 파일 요청 실패",
                file_path=file_path,
                error=str(e),
            )

        return seminars

    async def _fetch_from_readme(
        self,
        client: httpx.AsyncClient,
        keywords: list[str],
    ) -> list[SeminarInfo]:
        """
        README.md에서 현재 이벤트 수집

        Args:
            client: HTTP 클라이언트
            keywords: 필터 키워드

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        seminars = []

        url = f"{self.RAW_BASE_URL}/README.md"

        try:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AXDiscoveryBot/1.0)",
                },
            )

            if response.status_code == 200:
                now = datetime.now()
                seminars = self._parse_markdown(
                    response.text,
                    keywords,
                    now.year,
                    now.month,
                )

        except Exception as e:
            logger.warning("Dev-Event README 요청 실패", error=str(e))

        return seminars

    def _parse_markdown(
        self,
        content: str,
        keywords: list[str],
        year: int,
        month: int,
    ) -> list[SeminarInfo]:
        """
        마크다운 내용에서 이벤트 파싱

        Dev-Event 마크다운 형식:
        - __[이벤트명](URL)__
          - 분류: `온라인`, `무료`, `AI`

        Args:
            content: 마크다운 내용
            keywords: 필터 키워드
            year: 기준 연도
            month: 기준 월

        Returns:
            list[SeminarInfo]: 파싱된 세미나 목록
        """
        import hashlib

        seminars = []
        keywords_lower = [k.lower() for k in keywords]

        # 이벤트 링크 패턴: - __[제목](URL)__ 또는 - [제목](URL)
        event_pattern = r"[-*]\s*(?:__)?(?:\*\*)?\[([^\]]+)\]\(([^)]+)\)(?:__)?(?:\*\*)?"

        # 분류 정보 패턴
        info_pattern = r"분류:\s*([^\n]+)"

        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # 이벤트 링크 찾기
            match = re.search(event_pattern, line)
            if match:
                title = match.group(1).strip()
                url = match.group(2).strip()

                # 이미지 링크, GitHub 내부 링크 등 제외
                if url.startswith("#") or "github.com/brave-people" in url:
                    i += 1
                    continue
                if title.startswith("!") or title == "img":
                    i += 1
                    continue

                # 다음 줄에서 분류 정보 찾기
                next_line = ""
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                # 두 번째 다음 줄도 확인 (간격이 있을 수 있음)
                second_next = ""
                if i + 2 < len(lines):
                    second_next = lines[i + 2]

                combined_info = f"{next_line} {second_next}"
                combined_text = f"{title} {combined_info}".lower()

                # 키워드 매칭 여부 확인
                has_keyword = any(kw in combined_text for kw in keywords_lower)

                # 태그에서 AI 관련 태그 확인
                tags = re.findall(r"`([^`]+)`", combined_info)
                ai_tags = [
                    "ai",
                    "ml",
                    "딥러닝",
                    "머신러닝",
                    "인공지능",
                    "gpt",
                    "llm",
                    "생성형",
                    "data",
                    "데이터",
                ]
                has_ai_tag = any(any(ai in tag.lower() for ai in ai_tags) for tag in tags)

                if has_keyword or has_ai_tag:
                    # 분류 정보 추출
                    categories = []
                    info_match = re.search(info_pattern, combined_info)
                    if info_match:
                        info_text = info_match.group(1)
                        # 백틱으로 구분된 태그 추출
                        categories = re.findall(r"`([^`]+)`", info_text)

                    # 온라인/오프라인 확인
                    location = None
                    if "온라인" in combined_info:
                        location = "온라인"
                    elif "오프라인" in combined_info:
                        location = "오프라인"

                    # external_id 생성 (URL 해시)
                    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                    external_id = f"devevent_{url_hash}"

                    seminar = SeminarInfo(
                        title=title,
                        url=url,
                        source_type="devevent",
                        date=None,  # Dev-Event는 접수 기간만 표시
                        organizer=None,
                        location=location,
                        categories=categories if categories else ["개발자 이벤트"],
                        tags=[tag.strip() for tag in tags],
                        external_id=external_id,
                        raw_data={
                            "year": year,
                            "month": month,
                            "info_line": combined_info.strip()[:200],
                        },
                        fetched_at=datetime.now(UTC),
                    )
                    seminars.append(seminar)

            i += 1

        return seminars

    async def fetch_event_detail(self, external_id: str) -> SeminarInfo | None:
        """
        단일 이벤트 상세 정보 조회

        Dev-Event는 외부 URL 링크만 제공하므로 상세 조회 미지원

        Args:
            external_id: 이벤트 ID

        Returns:
            None (상세 조회 미지원)
        """
        logger.info(
            "Dev-Event는 외부 링크 기반이므로 상세 조회를 지원하지 않습니다",
            external_id=external_id,
        )
        return None

    async def get_repository_info(self) -> dict | None:
        """
        Dev-Event 저장소 정보 조회

        Returns:
            dict | None: 저장소 정보 (stars, forks, last_updated 등)
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    self.API_BASE_URL,
                    headers={
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "AXDiscoveryBot/1.0",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "name": data.get("full_name"),
                        "description": data.get("description"),
                        "stars": data.get("stargazers_count"),
                        "forks": data.get("forks_count"),
                        "last_updated": data.get("updated_at"),
                        "url": data.get("html_url"),
                    }

            except Exception as e:
                logger.error("Dev-Event 저장소 정보 조회 실패", error=str(e))

        return None
