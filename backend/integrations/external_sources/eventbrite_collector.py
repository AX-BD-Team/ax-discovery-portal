"""
Eventbrite 수집기

Eventbrite 이벤트 플랫폼에서 세미나/이벤트 정보 수집
"""

import os
from datetime import UTC, datetime

import httpx
import structlog

from .base import BaseSeminarCollector, SeminarInfo

logger = structlog.get_logger()


class EventbriteCollector(BaseSeminarCollector):
    """
    Eventbrite 이벤트 수집기

    Eventbrite API를 통해 글로벌 이벤트 수집
    """

    # Eventbrite API 기본 URL
    BASE_URL = "https://www.eventbriteapi.com/v3"

    # Eventbrite 카테고리 ID 매핑
    # https://www.eventbrite.com/platform/docs/categories
    CATEGORY_IDS = {
        "tech": "102",  # Science & Technology
        "business": "101",  # Business & Professional
        "ai": "102",  # Science & Technology (서브카테고리로 AI 필터)
        "startup": "101",  # Business & Professional
        "networking": "110",  # Community & Culture
        "education": "111",  # Education
    }

    # 서브카테고리 ID
    SUBCATEGORY_IDS = {
        "ai": "2004",  # AI & Machine Learning (예시)
        "data": "2005",  # Data Science (예시)
    }

    def __init__(self, api_token: str | None = None):
        """
        Args:
            api_token: Eventbrite Private Token (환경변수 EVENTBRITE_API_TOKEN 사용 가능)
        """
        super().__init__(name="eventbrite")
        self.api_token = api_token or os.getenv("EVENTBRITE_API_TOKEN")

    async def fetch_seminars(
        self,
        keywords: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> list[SeminarInfo]:
        """
        Eventbrite에서 세미나 정보 수집

        Args:
            keywords: 검색 키워드
            categories: 카테고리 (tech, business, ai, startup 등)
            limit: 최대 수집 개수
            location: 지역 (kwargs, 예: "Seoul", "Korea")
            online_only: 온라인 이벤트만 (kwargs, 기본: False)
            organizer_ids: 특정 주최자 ID 목록 (kwargs)

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        if not self.api_token:
            logger.warning("Eventbrite API 토큰이 설정되지 않았습니다")
            # API 토큰 없이 공개 검색 시도
            return await self._fetch_public_events(keywords, categories, limit, **kwargs)

        all_seminars: list[SeminarInfo] = []
        location = kwargs.get("location", "Korea")
        online_only = kwargs.get("online_only", False)
        organizer_ids = kwargs.get("organizer_ids", [])

        async with httpx.AsyncClient(timeout=30) as client:
            # 특정 주최자 이벤트 수집
            if organizer_ids:
                for org_id in organizer_ids:
                    try:
                        seminars = await self._fetch_by_organizer(client, org_id)
                        all_seminars.extend(seminars)
                    except Exception as e:
                        logger.error(
                            "Eventbrite 주최자 이벤트 수집 실패",
                            organizer_id=org_id,
                            error=str(e),
                        )

            # 키워드/카테고리 검색
            else:
                try:
                    seminars = await self._search_events(
                        client,
                        keywords=keywords,
                        categories=categories,
                        location=location,
                        online_only=online_only,
                    )
                    all_seminars.extend(seminars)
                except Exception as e:
                    logger.error("Eventbrite 이벤트 검색 실패", error=str(e))

        # 날짜 범위 필터링
        if "start_date" in kwargs or "end_date" in kwargs:
            all_seminars = self.filter_by_date_range(
                all_seminars,
                kwargs.get("start_date"),
                kwargs.get("end_date"),
            )

        # 중복 제거
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

    async def _search_events(
        self,
        client: httpx.AsyncClient,
        keywords: list[str] | None = None,
        categories: list[str] | None = None,
        location: str | None = None,
        online_only: bool = False,
    ) -> list[SeminarInfo]:
        """
        Eventbrite 이벤트 검색

        Args:
            client: HTTP 클라이언트
            keywords: 검색 키워드
            categories: 카테고리
            location: 지역
            online_only: 온라인만

        Returns:
            list[SeminarInfo]: 검색된 세미나 목록
        """
        seminars = []

        # API 파라미터 구성
        params = {
            "expand": "venue,organizer,category",
            "status": "live",
        }

        # 키워드
        if keywords:
            params["q"] = " ".join(keywords)

        # 카테고리
        if categories:
            cat_ids = [self.CATEGORY_IDS.get(c) for c in categories if c in self.CATEGORY_IDS]
            if cat_ids:
                params["categories"] = ",".join(filter(None, cat_ids))

        # 위치
        if location:
            params["location.address"] = location
            params["location.within"] = "100km"

        # 온라인 이벤트
        if online_only:
            params["online_events_only"] = "true"

        headers = {
            "Authorization": f"Bearer {self.api_token}",
        }

        try:
            response = await client.get(
                f"{self.BASE_URL}/events/search/",
                params=params,
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])

                for event in events:
                    seminar = self._parse_event(event)
                    if seminar:
                        seminars.append(seminar)

                logger.info(
                    "Eventbrite 검색 완료",
                    count=len(seminars),
                    total=data.get("pagination", {}).get("object_count"),
                )

            elif response.status_code == 401:
                logger.error("Eventbrite API 인증 실패")
            else:
                logger.warning(
                    "Eventbrite API 오류",
                    status=response.status_code,
                    body=response.text[:200],
                )

        except Exception as e:
            logger.error("Eventbrite API 요청 실패", error=str(e))

        return seminars

    async def _fetch_by_organizer(
        self,
        client: httpx.AsyncClient,
        organizer_id: str,
    ) -> list[SeminarInfo]:
        """
        특정 주최자의 이벤트 수집

        Args:
            client: HTTP 클라이언트
            organizer_id: 주최자 ID

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        seminars = []

        headers = {
            "Authorization": f"Bearer {self.api_token}",
        }

        try:
            response = await client.get(
                f"{self.BASE_URL}/organizers/{organizer_id}/events/",
                params={"status": "live", "expand": "venue,category"},
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])

                for event in events:
                    seminar = self._parse_event(event)
                    if seminar:
                        seminars.append(seminar)

                logger.info(
                    "Eventbrite 주최자 이벤트 수집 완료",
                    organizer_id=organizer_id,
                    count=len(seminars),
                )

        except Exception as e:
            logger.error(
                "Eventbrite 주최자 이벤트 수집 실패",
                organizer_id=organizer_id,
                error=str(e),
            )

        return seminars

    async def _fetch_public_events(
        self,
        keywords: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> list[SeminarInfo]:
        """
        API 토큰 없이 공개 이벤트 수집 (웹 스크래핑)

        Args:
            keywords: 검색 키워드
            categories: 카테고리
            limit: 최대 개수

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        seminars = []

        # 검색 키워드 구성
        query = " ".join(keywords) if keywords else "tech conference"
        location = kwargs.get("location", "korea")

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                url = f"https://www.eventbrite.com/d/{location}/{query.replace(' ', '-')}"
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; AXDiscoveryBot/1.0)",
                    },
                )

                if response.status_code == 200:
                    seminars = self._parse_html_events(response.text)
                    logger.info(
                        "Eventbrite 공개 이벤트 수집 완료 (HTML)",
                        count=len(seminars),
                    )

            except Exception as e:
                logger.error("Eventbrite 공개 이벤트 수집 실패", error=str(e))

        return seminars[:limit]

    def _parse_event(self, event: dict) -> SeminarInfo | None:
        """
        Eventbrite API 이벤트 응답 파싱

        Args:
            event: 이벤트 JSON 데이터

        Returns:
            SeminarInfo | None
        """
        try:
            event_id = event.get("id")
            name = event.get("name", {})
            title = name.get("text") or name.get("html", "")

            if not event_id or not title:
                return None

            # 날짜 파싱
            start = event.get("start", {})
            date_str = start.get("local") or start.get("utc")
            date = None
            if date_str:
                try:
                    date = date_str.split("T")[0]
                except Exception:
                    pass

            # 종료 날짜
            end = event.get("end", {})
            end_date_str = end.get("local") or end.get("utc")
            end_date = None
            if end_date_str:
                try:
                    end_date = end_date_str.split("T")[0]
                except Exception:
                    pass

            # 설명
            description = event.get("description", {})
            desc_text = description.get("text") or description.get("html", "")
            if desc_text:
                import re

                desc_text = re.sub(r"<[^>]+>", "", desc_text)[:1000]

            # 장소
            venue = event.get("venue", {})
            location = None
            if venue:
                location = venue.get("name") or venue.get("address", {}).get("city")
            if event.get("online_event"):
                location = "온라인"

            # 주최자
            organizer = event.get("organizer", {})
            organizer_name = organizer.get("name")

            # 카테고리
            category = event.get("category", {})
            category_name = category.get("name")
            categories = [category_name] if category_name else []

            return SeminarInfo(
                title=title,
                url=event.get("url", f"https://www.eventbrite.com/e/{event_id}"),
                source_type="eventbrite",
                date=date,
                end_date=end_date,
                organizer=organizer_name,
                description=desc_text,
                location=location,
                categories=categories,
                external_id=f"eventbrite_{event_id}",
                raw_data={
                    "event_id": event_id,
                    "is_free": event.get("is_free", False),
                    "is_online": event.get("online_event", False),
                    "capacity": event.get("capacity"),
                    "status": event.get("status"),
                },
                fetched_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("Eventbrite 이벤트 파싱 실패", error=str(e))
            return None

    def _parse_html_events(self, html: str) -> list[SeminarInfo]:
        """
        Eventbrite HTML 페이지에서 이벤트 파싱 (API 대안)

        Args:
            html: HTML 내용

        Returns:
            list[SeminarInfo]: 파싱된 세미나 목록
        """
        import re

        seminars = []

        # 이벤트 링크 패턴
        event_pattern = r'href="https://www\.eventbrite\.com/e/([^"]+)-(\d+)"[^>]*>([^<]+)</a>'
        matches = re.findall(event_pattern, html)

        for slug, event_id, title in matches[:20]:  # 최대 20개
            if not title.strip():
                continue

            seminar = SeminarInfo(
                title=title.strip(),
                url=f"https://www.eventbrite.com/e/{slug}-{event_id}",
                source_type="eventbrite",
                external_id=f"eventbrite_{event_id}",
                raw_data={"parsed_from": "html", "slug": slug},
                fetched_at=datetime.now(UTC),
            )
            seminars.append(seminar)

        return seminars

    async def fetch_event_detail(self, event_id: str) -> SeminarInfo | None:
        """
        단일 이벤트 상세 정보 조회

        Args:
            event_id: Eventbrite 이벤트 ID

        Returns:
            SeminarInfo | None
        """
        if not self.api_token:
            logger.warning("Eventbrite API 토큰이 필요합니다")
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/events/{event_id}/",
                    params={"expand": "venue,organizer,category"},
                    headers={"Authorization": f"Bearer {self.api_token}"},
                )

                if response.status_code == 200:
                    event = response.json()
                    return self._parse_event(event)
                else:
                    logger.warning(
                        "Eventbrite 이벤트 조회 실패",
                        event_id=event_id,
                        status=response.status_code,
                    )

            except Exception as e:
                logger.error(
                    "Eventbrite 이벤트 상세 조회 실패",
                    event_id=event_id,
                    error=str(e),
                )

        return None
