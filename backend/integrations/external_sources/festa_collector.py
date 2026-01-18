"""
Festa 수집기 (DEPRECATED)

Festa (festa.io) 이벤트 플랫폼에서 세미나/이벤트 정보 수집

⚠️ DEPRECATED: Festa.io 서비스가 2025년 1월 31일 종료되었습니다.
이 모듈은 하위 호환성을 위해 유지되지만, 실제 데이터를 수집하지 않습니다.
대안으로 OnOffMixCollector, EventUsCollector, DevEventCollector를 사용하세요.
"""

import warnings
from datetime import UTC, datetime

import httpx
import structlog

from .base import BaseSeminarCollector, SeminarInfo

logger = structlog.get_logger()


class FestaCollector(BaseSeminarCollector):
    """
    Festa 이벤트 수집기 (DEPRECATED)

    ⚠️ Festa.io 서비스가 2025년 1월 31일 종료되었습니다.
    이 클래스는 하위 호환성을 위해 유지되며, 빈 결과를 반환합니다.
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
            api_key: Festa API 키 (미사용 - 서비스 종료)
        """
        super().__init__(name="festa")
        self.api_key = api_key
        self._warned = False

    async def fetch_seminars(
        self,
        keywords: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> list[SeminarInfo]:
        """
        Festa에서 세미나 정보 수집 (DEPRECATED - 빈 결과 반환)

        ⚠️ Festa.io 서비스가 2025년 1월 31일 종료되었습니다.
        이 메서드는 항상 빈 목록을 반환합니다.

        대안:
        - OnOffMixCollector: 온오프믹스
        - EventUsCollector: 이벤터스
        - DevEventCollector: GitHub Dev-Event

        Args:
            keywords: 미사용
            categories: 미사용
            limit: 미사용
            **kwargs: 미사용

        Returns:
            list[SeminarInfo]: 항상 빈 목록
        """
        if not self._warned:
            warnings.warn(
                "FestaCollector는 더 이상 사용되지 않습니다. "
                "Festa.io 서비스가 2025년 1월 31일 종료되었습니다. "
                "OnOffMixCollector, EventUsCollector, DevEventCollector를 사용하세요.",
                DeprecationWarning,
                stacklevel=2,
            )
            self._warned = True

        logger.warning(
            "Festa.io 서비스가 종료되어 데이터를 수집할 수 없습니다",
            service_ended="2025-01-31",
            alternatives=["onoffmix", "eventus", "devevent"],
        )

        return []

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
            seminars = [s for s in seminars if s.location and location_lower in s.location.lower()]

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
