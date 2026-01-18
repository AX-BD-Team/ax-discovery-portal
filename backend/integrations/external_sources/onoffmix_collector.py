"""
온오프믹스 수집기

온오프믹스 (onoffmix.com) 이벤트 플랫폼에서 세미나/이벤트 정보 수집
"""

import re
from datetime import UTC, datetime

import httpx
import structlog

from .base import BaseSeminarCollector, SeminarInfo
from .keywords import AI_AX_KEYWORDS, ONOFFMIX_CATEGORIES, filter_excludes

logger = structlog.get_logger()


class OnOffMixCollector(BaseSeminarCollector):
    """
    온오프믹스 이벤트 수집기

    공개 API가 없어 웹 스크래핑 방식으로 수집
    """

    BASE_URL = "https://onoffmix.com"

    # 이벤트 타입
    EVENT_TYPES = {
        "seminar": "강연/세미나",
        "conference": "컨퍼런스/포럼",
        "workshop": "워크숍",
        "networking": "네트워킹/파티",
    }

    def __init__(self):
        super().__init__(name="onoffmix")

    async def fetch_seminars(
        self,
        keywords: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> list[SeminarInfo]:
        """
        온오프믹스에서 세미나 정보 수집

        Args:
            keywords: 필터링할 키워드 (AI/AX 관련)
            categories: 온오프믹스 카테고리 (it, startup, education)
            limit: 최대 수집 개수
            event_type: 이벤트 타입 (kwargs, seminar/conference/workshop)
            location: 지역 필터 (kwargs, 예: "서울", "온라인")

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        # 기본 키워드 설정 (AI/AX 관련)
        search_keywords = keywords or AI_AX_KEYWORDS[:5]
        target_categories = categories or ["it"]

        all_seminars: list[SeminarInfo] = []

        async with httpx.AsyncClient(timeout=30) as client:
            # 카테고리별 수집
            for category in target_categories:
                category_id = ONOFFMIX_CATEGORIES.get(category, category)
                try:
                    seminars = await self._fetch_by_category(
                        client,
                        category_id,
                        search_keywords,
                    )
                    all_seminars.extend(seminars)
                    logger.info(
                        "온오프믹스 카테고리 수집 완료",
                        category=category,
                        count=len(seminars),
                    )
                except Exception as e:
                    logger.error(
                        "온오프믹스 카테고리 수집 실패",
                        category=category,
                        error=str(e),
                    )

            # 키워드 검색으로 추가 수집
            for keyword in search_keywords[:3]:  # 상위 3개 키워드만
                try:
                    seminars = await self._search_events(client, keyword)
                    all_seminars.extend(seminars)
                except Exception as e:
                    logger.error(
                        "온오프믹스 키워드 검색 실패",
                        keyword=keyword,
                        error=str(e),
                    )

        # 중복 제거 (URL 기준)
        seen_urls = set()
        unique_seminars = []
        for seminar in all_seminars:
            if seminar.url not in seen_urls:
                seen_urls.add(seminar.url)
                # 제외 키워드 필터링
                if not filter_excludes(f"{seminar.title} {seminar.description or ''}"):
                    unique_seminars.append(seminar)

        # 키워드 필터링 (AI/AX 관련만)
        if keywords:
            unique_seminars = self.filter_by_keywords(unique_seminars, keywords)

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

    async def _fetch_by_category(
        self,
        client: httpx.AsyncClient,
        category_id: str,
        keywords: list[str],
    ) -> list[SeminarInfo]:
        """
        카테고리별 이벤트 수집

        Args:
            client: HTTP 클라이언트
            category_id: 카테고리 ID (interest 파라미터, 예: A0103)
            keywords: 필터 키워드

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        seminars = []

        # 2025년 이후 새 URL 구조: /event/main/?interest=A0103
        url = f"{self.BASE_URL}/event/main/"
        params = {
            "interest": category_id,  # A0103 (과학/IT/AI) 등
        }

        try:
            response = await client.get(
                url,
                params=params,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "ko-KR,ko;q=0.9",
                },
            )

            if response.status_code == 200:
                seminars = self._parse_event_list(response.text, keywords)

        except httpx.HTTPStatusError as e:
            logger.warning(
                "온오프믹스 HTTP 오류",
                status=e.response.status_code,
                category=category_id,
            )

        return seminars

    async def _search_events(
        self,
        client: httpx.AsyncClient,
        keyword: str,
    ) -> list[SeminarInfo]:
        """
        키워드로 이벤트 검색

        Args:
            client: HTTP 클라이언트
            keyword: 검색 키워드

        Returns:
            list[SeminarInfo]: 검색된 세미나 목록
        """
        seminars = []

        url = f"{self.BASE_URL}/event"
        params = {
            "q": keyword,
            "s": "1",  # 진행중
        }

        try:
            response = await client.get(
                url,
                params=params,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "ko-KR,ko;q=0.9",
                },
            )

            if response.status_code == 200:
                seminars = self._parse_event_list(response.text, [keyword])
                logger.info(
                    "온오프믹스 키워드 검색 완료",
                    keyword=keyword,
                    count=len(seminars),
                )

        except Exception as e:
            logger.error("온오프믹스 검색 실패", keyword=keyword, error=str(e))

        return seminars

    def _parse_event_list(
        self,
        html: str,
        keywords: list[str],
    ) -> list[SeminarInfo]:
        """
        이벤트 목록 HTML 파싱

        Args:
            html: HTML 내용
            keywords: 필터 키워드

        Returns:
            list[SeminarInfo]: 파싱된 세미나 목록
        """
        seminars = []

        # 2025년 온오프믹스 HTML 구조:
        # <article class="event_area">
        #   <a href="/event/{id}" ...>
        #     <h5 class="title ellipsis" title="이벤트 제목">이벤트 제목</h5>
        #   </a>
        # </article>

        # event_area 아티클 단위로 파싱
        article_pattern = r'<article class="event_area[^"]*">(.*?)</article>'
        articles = re.findall(article_pattern, html, re.DOTALL | re.IGNORECASE)

        for article in articles:
            # 이벤트 ID 추출
            id_match = re.search(r'href="/event/(\d+)"', article, re.IGNORECASE)
            if not id_match:
                continue
            event_id = id_match.group(1)

            # 제목 추출 (h5 태그의 title 속성 또는 텍스트 내용)
            title = None

            # 방법 1: h5 태그의 title 속성
            title_attr_match = re.search(
                r'<h5[^>]*class="[^"]*title[^"]*"[^>]*title="([^"]+)"',
                article,
                re.IGNORECASE,
            )
            if title_attr_match:
                title = title_attr_match.group(1).strip()

            # 방법 2: h5 태그의 텍스트 내용
            if not title:
                title_text_match = re.search(
                    r'<h5[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h5>',
                    article,
                    re.IGNORECASE,
                )
                if title_text_match:
                    title = title_text_match.group(1).strip()

            # 방법 3: img alt 속성 (폴백)
            if not title:
                img_alt_match = re.search(r'<img[^>]*alt="([^"]+)"', article, re.IGNORECASE)
                if img_alt_match:
                    title = img_alt_match.group(1).strip()

            if not title or len(title) < 5:
                continue

            # 날짜 추출 (div.date)
            date = None
            date_match = re.search(r'<div class="date">([^<]+)</div>', article, re.IGNORECASE)
            if date_match:
                date_text = date_match.group(1).strip()
                # "1.21 (화)" 형식 파싱
                date = self._parse_korean_date(date_text)

            # AI/AX 키워드 필터 (선택적)
            if keywords:
                keywords_lower = [k.lower() for k in keywords]
                title_lower = title.lower()
                if not any(kw in title_lower for kw in keywords_lower):
                    continue

            seminar = SeminarInfo(
                title=title,
                url=f"{self.BASE_URL}/event/{event_id}",
                source_type="onoffmix",
                date=date,
                categories=["IT/인터넷"],
                external_id=f"onoffmix_{event_id}",
                raw_data={"event_id": event_id},
                fetched_at=datetime.now(UTC),
            )
            seminars.append(seminar)

            if len(seminars) >= 30:
                break

        # 대체 패턴 (JSON-LD 또는 구조화된 데이터)
        if not seminars:
            seminars = self._parse_json_ld(html)

        return seminars

    def _parse_korean_date(self, date_text: str) -> str | None:
        """
        한국어 날짜 형식 파싱

        Args:
            date_text: "1.21 (화)" 또는 "1월 21일" 형식

        Returns:
            str | None: YYYY-MM-DD 형식
        """
        from datetime import date as dt_date

        try:
            # "1.21" 또는 "01.21" 형식
            match = re.match(r"(\d{1,2})\.(\d{1,2})", date_text)
            if match:
                month, day = int(match.group(1)), int(match.group(2))
                year = dt_date.today().year
                # 지난 달이면 내년으로 추정
                if month < dt_date.today().month:
                    year += 1
                return f"{year}-{month:02d}-{day:02d}"
        except Exception:
            pass

        return None

    def _parse_json_ld(self, html: str) -> list[SeminarInfo]:
        """
        JSON-LD 구조화 데이터에서 이벤트 파싱

        Args:
            html: HTML 내용

        Returns:
            list[SeminarInfo]: 파싱된 세미나 목록
        """
        import json

        seminars = []

        # JSON-LD 스크립트 태그 찾기
        json_ld_pattern = r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>'
        matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)

        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list):
                    for item in data:
                        seminar = self._parse_json_ld_event(item)
                        if seminar:
                            seminars.append(seminar)
                elif isinstance(data, dict):
                    seminar = self._parse_json_ld_event(data)
                    if seminar:
                        seminars.append(seminar)
            except json.JSONDecodeError:
                continue

        return seminars

    def _parse_json_ld_event(self, data: dict) -> SeminarInfo | None:
        """
        단일 JSON-LD 이벤트 데이터 파싱

        Args:
            data: JSON-LD 데이터

        Returns:
            SeminarInfo | None
        """
        if data.get("@type") != "Event":
            return None

        title = data.get("name")
        url = data.get("url")

        if not title or not url:
            return None

        # 날짜 파싱
        start_date = data.get("startDate")
        date = None
        if start_date:
            try:
                date = start_date.split("T")[0]
            except Exception:
                pass

        # 장소
        location = data.get("location", {})
        if isinstance(location, dict):
            location_name = location.get("name") or location.get("address")
        else:
            location_name = str(location) if location else None

        # 주최자
        organizer = data.get("organizer", {})
        organizer_name = None
        if isinstance(organizer, dict):
            organizer_name = organizer.get("name")

        return SeminarInfo(
            title=title,
            url=url,
            source_type="onoffmix",
            date=date,
            organizer=organizer_name,
            description=data.get("description", "")[:1000],
            location=location_name,
            external_id=f"onoffmix_{url.split('/')[-1]}",
            raw_data=data,
            fetched_at=datetime.now(UTC),
        )

    def _extract_date_from_html(self, html: str, event_id: str) -> str | None:
        """
        HTML에서 특정 이벤트의 날짜 추출

        Args:
            html: HTML 내용
            event_id: 이벤트 ID

        Returns:
            str | None: YYYY-MM-DD 형식 날짜
        """
        # 날짜 패턴 찾기 (이벤트 ID 근처)
        patterns = [
            r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})",
            r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                year, month, day = matches[0]
                try:
                    return f"{year}-{int(month):02d}-{int(day):02d}"
                except ValueError:
                    continue

        return None

    async def fetch_event_detail(self, event_id: str) -> SeminarInfo | None:
        """
        단일 이벤트 상세 정보 조회

        Args:
            event_id: 온오프믹스 이벤트 ID

        Returns:
            SeminarInfo | None
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                url = f"{self.BASE_URL}/event/{event_id}"
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    },
                )

                if response.status_code == 200:
                    return self._parse_event_detail(response.text, event_id)

            except Exception as e:
                logger.error(
                    "온오프믹스 이벤트 상세 조회 실패",
                    event_id=event_id,
                    error=str(e),
                )

        return None

    def _parse_event_detail(self, html: str, event_id: str) -> SeminarInfo | None:
        """
        이벤트 상세 페이지 파싱

        Args:
            html: HTML 내용
            event_id: 이벤트 ID

        Returns:
            SeminarInfo | None
        """
        # 제목 추출
        title_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        title = title_match.group(1).strip() if title_match else None

        if not title:
            # og:title 메타 태그
            og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
            title = og_title.group(1) if og_title else "Unknown"

        # 설명 추출
        desc_match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html)
        description = desc_match.group(1) if desc_match else None

        # 날짜 추출
        date = self._extract_date_from_html(html, event_id)

        # 주최자 추출
        organizer_match = re.search(r"주최[:\s]*([^<\n]+)", html)
        organizer = organizer_match.group(1).strip()[:100] if organizer_match else None

        # 장소 추출
        location_match = re.search(r"장소[:\s]*([^<\n]+)", html)
        location = location_match.group(1).strip()[:200] if location_match else None

        return SeminarInfo(
            title=title,
            url=f"{self.BASE_URL}/event/{event_id}",
            source_type="onoffmix",
            date=date,
            organizer=organizer,
            description=description,
            location=location,
            external_id=f"onoffmix_{event_id}",
            fetched_at=datetime.now(UTC),
        )
