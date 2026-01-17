"""
Festa 수집기

Festa (festa.io) 이벤트 플랫폼에서 세미나/이벤트 정보 수집
"""

import os
from datetime import UTC, datetime

import httpx
import structlog

from .base import BaseSeminarCollector, SeminarInfo

logger = structlog.get_logger()


class FestaCollector(BaseSeminarCollector):
    """
    Festa 이벤트 수집기

    Festa API를 통해 IT/스타트업 이벤트 수집
    """

    # Festa API 기본 URL
    BASE_URL = "https://festa.io/api/v1"

    # Festa 카테고리 매핑
    CATEGORY_MAP = {
        "tech": "기술/개발",
        "ai": "AI/ML",
        "startup": "스타트업",
        "design": "디자인",
        "marketing": "마케팅",
        "business": "비즈니스",
        "network": "네트워킹",
        "education": "교육",
    }

    def __init__(self, api_key: str | None = None):
        """
        Args:
            api_key: Festa API 키 (환경변수 FESTA_API_KEY 사용 가능)
        """
        super().__init__(name="festa")
        self.api_key = api_key or os.getenv("FESTA_API_KEY")

    async def fetch_seminars(
        self,
        keywords: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> list[SeminarInfo]:
        """
        Festa에서 세미나 정보 수집

        Args:
            keywords: 필터링할 키워드
            categories: Festa 카테고리 (tech, ai, startup 등)
            limit: 최대 수집 개수
            location: 지역 필터 (kwargs, 예: "서울", "온라인")
            include_past: 지난 이벤트 포함 여부 (kwargs, 기본: False)

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        location = kwargs.get("location")
        include_past = kwargs.get("include_past", False)

        all_seminars: list[SeminarInfo] = []

        async with httpx.AsyncClient(timeout=30) as client:
            # 카테고리별로 수집 (카테고리가 없으면 전체)
            cats_to_fetch = categories if categories else list(self.CATEGORY_MAP.keys())

            for category in cats_to_fetch:
                try:
                    seminars = await self._fetch_by_category(
                        client,
                        category,
                        location=location,
                        include_past=include_past,
                    )
                    all_seminars.extend(seminars)
                    logger.info(
                        "Festa 카테고리 수집 완료",
                        category=category,
                        count=len(seminars),
                    )
                except Exception as e:
                    logger.error(
                        "Festa 카테고리 수집 실패",
                        category=category,
                        error=str(e),
                    )

        # 키워드 필터링
        if keywords:
            all_seminars = self.filter_by_keywords(all_seminars, keywords)

        # 날짜 범위 필터링
        if "start_date" in kwargs or "end_date" in kwargs:
            all_seminars = self.filter_by_date_range(
                all_seminars,
                kwargs.get("start_date"),
                kwargs.get("end_date"),
            )

        # 중복 제거 (event_id 기준)
        seen_ids = set()
        unique_seminars = []
        for seminar in all_seminars:
            if seminar.external_id not in seen_ids:
                seen_ids.add(seminar.external_id)
                unique_seminars.append(seminar)

        # 최신순 정렬
        unique_seminars.sort(
            key=lambda x: x.date or "9999-99-99",
            reverse=True,
        )

        return unique_seminars[:limit]

    async def _fetch_by_category(
        self,
        client: httpx.AsyncClient,
        category: str,
        location: str | None = None,
        include_past: bool = False,
    ) -> list[SeminarInfo]:
        """
        카테고리별 이벤트 수집

        Args:
            client: HTTP 클라이언트
            category: Festa 카테고리
            location: 지역 필터
            include_past: 지난 이벤트 포함

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        seminars = []

        # Festa API는 공개 API 제한적으로 페이지 크롤링 방식 사용
        # 실제 API가 있다면 해당 엔드포인트로 변경
        url = f"https://festa.io/events?category={category}"

        try:
            # HTML 페이지 요청 (API 대안)
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AXDiscoveryBot/1.0)",
                },
            )

            if response.status_code == 200:
                # JSON API 응답 파싱 시도 (실제 API 형태에 맞게 조정 필요)
                try:
                    events = response.json()
                    if isinstance(events, list):
                        for event in events:
                            seminar = self._parse_event(event, category)
                            if seminar:
                                seminars.append(seminar)
                except Exception:
                    # JSON 파싱 실패 시 HTML 파싱 시도
                    seminars = self._parse_html_events(response.text, category)

        except httpx.HTTPStatusError as e:
            logger.warning(
                "Festa HTTP 오류",
                status=e.response.status_code,
                category=category,
            )

        # 지난 이벤트 필터링
        if not include_past:
            today = datetime.now().strftime("%Y-%m-%d")
            seminars = [s for s in seminars if (s.date or "9999") >= today]

        # 지역 필터링
        if location:
            location_lower = location.lower()
            seminars = [
                s
                for s in seminars
                if s.location and location_lower in s.location.lower()
            ]

        return seminars

    def _parse_event(self, event: dict, category: str) -> SeminarInfo | None:
        """
        Festa 이벤트 JSON 파싱

        Args:
            event: 이벤트 JSON 데이터
            category: 카테고리

        Returns:
            SeminarInfo | None
        """
        try:
            event_id = str(event.get("id") or event.get("event_id", ""))
            title = event.get("title") or event.get("name", "")

            if not event_id or not title:
                return None

            # 날짜 파싱
            date_str = event.get("start_time") or event.get("date")
            date = None
            if date_str:
                try:
                    date = date_str.split("T")[0] if "T" in date_str else date_str[:10]
                except Exception:
                    pass

            # 장소 파싱
            location = event.get("location") or event.get("venue")
            if isinstance(location, dict):
                location = location.get("name") or location.get("address")
            if event.get("is_online"):
                location = "온라인"

            return SeminarInfo(
                title=title,
                url=f"https://festa.io/events/{event_id}",
                source_type="festa",
                date=date,
                organizer=event.get("organizer", {}).get("name"),
                description=event.get("description", "")[:1000],
                location=location,
                categories=[self.CATEGORY_MAP.get(category, category)],
                external_id=f"festa_{event_id}",
                raw_data={
                    "event_id": event_id,
                    "category": category,
                    "is_online": event.get("is_online", False),
                    "ticket_price": event.get("ticket_price"),
                },
                fetched_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("Festa 이벤트 파싱 실패", error=str(e))
            return None

    def _parse_html_events(self, html: str, category: str) -> list[SeminarInfo]:
        """
        Festa HTML 페이지에서 이벤트 파싱 (API 대안)

        실제 구현 시 BeautifulSoup 등 사용 권장

        Args:
            html: HTML 내용
            category: 카테고리

        Returns:
            list[SeminarInfo]: 파싱된 세미나 목록
        """
        import re

        seminars = []

        # 간단한 정규식 파싱 (실제로는 BeautifulSoup 권장)
        # Festa의 이벤트 카드 패턴 찾기
        event_pattern = r'/events/(\d+)"[^>]*>([^<]+)</a>'
        matches = re.findall(event_pattern, html)

        for event_id, title in matches[:20]:  # 최대 20개
            seminar = SeminarInfo(
                title=title.strip(),
                url=f"https://festa.io/events/{event_id}",
                source_type="festa",
                categories=[self.CATEGORY_MAP.get(category, category)],
                external_id=f"festa_{event_id}",
                raw_data={"category": category, "parsed_from": "html"},
                fetched_at=datetime.now(UTC),
            )
            seminars.append(seminar)

        return seminars

    async def fetch_event_detail(self, event_id: str) -> SeminarInfo | None:
        """
        단일 이벤트 상세 정보 조회

        Args:
            event_id: Festa 이벤트 ID

        Returns:
            SeminarInfo | None
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                url = f"https://festa.io/events/{event_id}"
                response = await client.get(url)
                response.raise_for_status()

                # 상세 페이지 파싱 로직 구현 필요
                # 실제 구현 시 BeautifulSoup 등 사용

                return None  # TODO: 상세 파싱 구현

            except Exception as e:
                logger.error(
                    "Festa 이벤트 상세 조회 실패",
                    event_id=event_id,
                    error=str(e),
                )
                return None
