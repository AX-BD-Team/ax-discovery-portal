"""
이벤터스 수집기

이벤터스 (event-us.kr) 이벤트 플랫폼에서 세미나/이벤트 정보 수집
"""

import re
from datetime import UTC, datetime

import httpx
import structlog

from .base import BaseSeminarCollector, SeminarInfo
from .keywords import AI_AX_KEYWORDS, EVENTUS_CATEGORIES, filter_excludes

logger = structlog.get_logger()


class EventUsCollector(BaseSeminarCollector):
    """
    이벤터스 이벤트 수집기

    공개 API가 없어 웹 스크래핑 방식으로 수집
    IT/프로그래밍 카테고리 중심
    """

    BASE_URL = "https://event-us.kr"
    API_BASE = "https://api.event-us.kr/api/v1"

    def __init__(self):
        super().__init__(name="eventus")

    async def fetch_seminars(
        self,
        keywords: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> list[SeminarInfo]:
        """
        이벤터스에서 세미나 정보 수집

        Args:
            keywords: 필터링할 키워드 (AI/AX 관련)
            categories: 이벤터스 카테고리 (it, startup, business)
            limit: 최대 수집 개수

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        search_keywords = keywords or AI_AX_KEYWORDS[:5]
        target_categories = categories or ["it"]

        all_seminars: list[SeminarInfo] = []

        async with httpx.AsyncClient(timeout=30) as client:
            # IT/프로그래밍 카테고리 페이지에서 수집
            for category in target_categories:
                category_name = EVENTUS_CATEGORIES.get(category, category)
                try:
                    seminars = await self._fetch_by_category(
                        client,
                        category_name,
                        search_keywords,
                    )
                    all_seminars.extend(seminars)
                    logger.info(
                        "이벤터스 카테고리 수집 완료",
                        category=category_name,
                        count=len(seminars),
                    )
                except Exception as e:
                    logger.error(
                        "이벤터스 카테고리 수집 실패",
                        category=category_name,
                        error=str(e),
                    )

            # 키워드 검색
            for keyword in search_keywords[:3]:
                try:
                    seminars = await self._search_events(client, keyword)
                    all_seminars.extend(seminars)
                except Exception as e:
                    logger.error(
                        "이벤터스 키워드 검색 실패",
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

        # 키워드 필터링
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
        category_name: str,
        keywords: list[str],
    ) -> list[SeminarInfo]:
        """
        카테고리별 이벤트 수집

        Args:
            client: HTTP 클라이언트
            category_name: 카테고리 이름 (URL 인코딩됨)
            keywords: 필터 키워드

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        seminars = []

        # IT/프로그래밍 카테고리 URL
        from urllib.parse import quote

        encoded_category = quote(category_name)
        url = f"{self.BASE_URL}/search"
        params = {
            "category": encoded_category,
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
                "이벤터스 HTTP 오류",
                status=e.response.status_code,
                category=category_name,
            )

        return seminars

    async def _search_events(
        self,
        client: httpx.AsyncClient,
        keyword: str,
    ) -> list[SeminarInfo]:
        """
        키워드로 이벤트 검색 (suggest API 사용)

        Args:
            client: HTTP 클라이언트
            keyword: 검색 키워드

        Returns:
            list[SeminarInfo]: 검색된 세미나 목록
        """
        seminars = []

        # 검색 suggest API 사용 (2025년 현재 작동하는 엔드포인트)
        try:
            response = await client.get(
                f"{self.API_BASE}/engine/suggest",
                params={"query": keyword},  # 'keyword' 대신 'query' 사용
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Origin": self.BASE_URL,
                    "Referer": f"{self.BASE_URL}/",
                },
            )

            if response.status_code == 200:
                data = response.json()
                # API 응답 구조: {"meta": {...}, "results": [...]}
                results = data.get("results", [])

                for event in results:
                    seminar = self._parse_suggest_api_event(event)
                    if seminar:
                        seminars.append(seminar)

                logger.info(
                    "이벤터스 suggest API 검색 완료",
                    keyword=keyword,
                    count=len(seminars),
                    total_results=data.get("meta", {}).get("page", {}).get("total_results", 0),
                )
                return seminars

        except Exception as e:
            logger.debug("이벤터스 suggest API 검색 실패", error=str(e))

        # 기존 API 폴백 시도
        try:
            response = await client.get(
                f"{self.API_BASE}/engine/suggest",
                params={"keyword": keyword},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Referer": self.BASE_URL,
                },
            )

            if response.status_code == 200:
                data = response.json()
                events = data.get("events", data.get("results", []))
                for event in events:
                    seminar = self._parse_api_event(event)
                    if seminar:
                        seminars.append(seminar)

                logger.info(
                    "이벤터스 API 검색 완료",
                    keyword=keyword,
                    count=len(seminars),
                )
                return seminars

        except Exception as e:
            logger.debug("이벤터스 API 검색 실패, HTML 폴백", error=str(e))

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

        # 이벤트 링크 패턴 (event-us.kr/events/{event_id})
        # 다양한 패턴 시도
        patterns = [
            r'href="(https?://event-us\.kr/[^/]+/events/(\d+))"[^>]*>.*?<[^>]*>([^<]+)',
            r'/events/(\d+)[^>]*>.*?class="[^"]*title[^"]*"[^>]*>([^<]+)',
            r'data-event-id="(\d+)"[^>]*>.*?<[^>]*class="[^"]*name[^"]*"[^>]*>([^<]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

            if matches:
                for match in matches[:30]:
                    # 패턴에 따라 그룹 수가 다름
                    if len(match) == 3:
                        url, event_id, title = match
                    elif len(match) == 2:
                        event_id, title = match
                        url = f"{self.BASE_URL}/events/{event_id}"
                    else:
                        continue

                    title = self._clean_title(title)
                    if not title:
                        continue

                    # AI/AX 키워드 필터
                    keywords_lower = [k.lower() for k in keywords]
                    title_lower = title.lower()

                    if keywords and not any(kw in title_lower for kw in keywords_lower):
                        continue

                    seminar = SeminarInfo(
                        title=title,
                        url=url if url.startswith("http") else f"{self.BASE_URL}/events/{event_id}",
                        source_type="eventus",
                        categories=["IT/프로그래밍"],
                        external_id=f"eventus_{event_id}",
                        raw_data={"event_id": event_id},
                        fetched_at=datetime.now(UTC),
                    )
                    seminars.append(seminar)

                if seminars:
                    break

        # JSON-LD 폴백
        if not seminars:
            seminars = self._parse_json_ld(html)

        return seminars

    def _parse_suggest_api_event(self, event: dict) -> SeminarInfo | None:
        """
        suggest API 응답에서 이벤트 파싱

        Args:
            event: suggest API 이벤트 데이터
                   구조: {"title": {"raw": "..."}, "id": {"raw": "..."}}

        Returns:
            SeminarInfo | None
        """
        try:
            # suggest API 응답 구조에서 값 추출
            title_obj = event.get("title", {})
            id_obj = event.get("id", {})

            title = title_obj.get("raw", "") if isinstance(title_obj, dict) else str(title_obj)
            event_id = id_obj.get("raw", "") if isinstance(id_obj, dict) else str(id_obj)

            if not event_id or not title:
                return None

            # URL 구성 (event-us.kr/m/[channel]/events/[id] 형식)
            url = f"{self.BASE_URL}/events/{event_id}"

            return SeminarInfo(
                title=title,
                url=url,
                source_type="eventus",
                date=None,  # suggest API에는 날짜 정보 없음
                categories=["IT/프로그래밍"],
                external_id=f"eventus_{event_id}",
                raw_data=event,
                fetched_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("이벤터스 suggest API 이벤트 파싱 실패", error=str(e))
            return None

    def _parse_api_event(self, event: dict) -> SeminarInfo | None:
        """
        API 응답에서 이벤트 파싱

        Args:
            event: 이벤트 JSON 데이터

        Returns:
            SeminarInfo | None
        """
        try:
            event_id = str(event.get("id") or event.get("event_id", ""))
            title = event.get("name") or event.get("title", "")

            if not event_id or not title:
                return None

            # 날짜 파싱
            date_str = event.get("start_at") or event.get("event_date")
            date = None
            if date_str:
                try:
                    date = date_str.split("T")[0] if "T" in date_str else date_str[:10]
                except Exception:
                    pass

            # URL 구성
            channel = event.get("channel", {})
            channel_name = channel.get("name", "") if isinstance(channel, dict) else ""
            url = (
                f"{self.BASE_URL}/{channel_name}/events/{event_id}"
                if channel_name
                else f"{self.BASE_URL}/events/{event_id}"
            )

            return SeminarInfo(
                title=title,
                url=url,
                source_type="eventus",
                date=date,
                organizer=event.get("organizer", {}).get("name")
                if isinstance(event.get("organizer"), dict)
                else None,
                description=event.get("summary", "")[:1000],
                location=event.get("location") or ("온라인" if event.get("is_online") else None),
                categories=["IT/프로그래밍"],
                external_id=f"eventus_{event_id}",
                raw_data=event,
                fetched_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("이벤터스 API 이벤트 파싱 실패", error=str(e))
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

        json_ld_pattern = r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>'
        matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)

        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "Event":
                            seminar = self._parse_json_ld_event(item)
                            if seminar:
                                seminars.append(seminar)
                elif isinstance(data, dict) and data.get("@type") == "Event":
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
        title = data.get("name")
        url = data.get("url")

        if not title or not url:
            return None

        # 이벤트 ID 추출
        event_id = url.split("/")[-1] if url else ""

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
        location_name = None
        if isinstance(location, dict):
            location_name = location.get("name") or location.get("address")
        elif isinstance(location, str):
            location_name = location

        # 주최자
        organizer = data.get("organizer", {})
        organizer_name = organizer.get("name") if isinstance(organizer, dict) else None

        return SeminarInfo(
            title=title,
            url=url,
            source_type="eventus",
            date=date,
            organizer=organizer_name,
            description=data.get("description", "")[:1000],
            location=location_name,
            external_id=f"eventus_{event_id}",
            raw_data=data,
            fetched_at=datetime.now(UTC),
        )

    def _clean_title(self, title: str) -> str:
        """
        제목 정리

        Args:
            title: 원본 제목

        Returns:
            str: 정리된 제목
        """
        if not title:
            return ""

        # HTML 엔티티 디코딩
        import html

        title = html.unescape(title)

        # 태그 제거
        title = re.sub(r"<[^>]+>", "", title)

        # 공백 정리
        title = " ".join(title.split())

        return title.strip()

    async def fetch_event_detail(self, event_id: str) -> SeminarInfo | None:
        """
        단일 이벤트 상세 정보 조회

        Args:
            event_id: 이벤터스 이벤트 ID

        Returns:
            SeminarInfo | None
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                url = f"{self.BASE_URL}/events/{event_id}"
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    },
                )

                if response.status_code == 200:
                    # JSON-LD 우선 파싱
                    seminars = self._parse_json_ld(response.text)
                    if seminars:
                        return seminars[0]

                    # HTML 폴백
                    return self._parse_event_detail_html(response.text, event_id)

            except Exception as e:
                logger.error(
                    "이벤터스 이벤트 상세 조회 실패",
                    event_id=event_id,
                    error=str(e),
                )

        return None

    def _parse_event_detail_html(self, html: str, event_id: str) -> SeminarInfo | None:
        """
        이벤트 상세 페이지 HTML 파싱

        Args:
            html: HTML 내용
            event_id: 이벤트 ID

        Returns:
            SeminarInfo | None
        """
        # 제목 추출
        title_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        title = self._clean_title(title_match.group(1)) if title_match else None

        if not title:
            og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
            title = og_title.group(1) if og_title else "Unknown"

        # 설명 추출
        desc_match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html)
        description = desc_match.group(1) if desc_match else None

        # 날짜 추출
        date_patterns = [
            r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})",
            r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일",
        ]

        date = None
        for pattern in date_patterns:
            matches = re.findall(pattern, html)
            if matches:
                year, month, day = matches[0]
                try:
                    date = f"{year}-{int(month):02d}-{int(day):02d}"
                    break
                except ValueError:
                    continue

        return SeminarInfo(
            title=title,
            url=f"{self.BASE_URL}/events/{event_id}",
            source_type="eventus",
            date=date,
            description=description,
            categories=["IT/프로그래밍"],
            external_id=f"eventus_{event_id}",
            fetched_at=datetime.now(UTC),
        )
