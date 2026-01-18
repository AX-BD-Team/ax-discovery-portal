"""
RSS 피드 수집기

다양한 RSS 피드에서 세미나/이벤트 정보 수집
"""

import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx
import structlog

from .base import BaseSeminarCollector, SeminarInfo
from .keywords import RSS_FEED_URLS

logger = structlog.get_logger()


class RSSCollector(BaseSeminarCollector):
    """
    RSS 피드 수집기

    feedparser 라이브러리 없이 직접 XML 파싱
    """

    def __init__(self, feed_urls: list[str] | None = None):
        """
        Args:
            feed_urls: RSS 피드 URL 목록 (None이면 기본 피드 사용)
        """
        super().__init__(name="rss")
        # 기본 피드 URL 사용 (keywords.py에 정의됨)
        self.feed_urls = feed_urls if feed_urls is not None else RSS_FEED_URLS

    async def fetch_seminars(
        self,
        keywords: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> list[SeminarInfo]:
        """
        RSS 피드에서 세미나 정보 수집

        Args:
            keywords: 필터링할 키워드 (제목/설명에 포함)
            categories: 미사용 (RSS는 카테고리 정보 제한적)
            limit: 최대 수집 개수
            feed_urls: 추가 피드 URL (kwargs)

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        # 피드 URL 목록 (인스턴스 기본값 + kwargs)
        feed_urls = list(self.feed_urls)
        if "feed_urls" in kwargs:
            feed_urls.extend(kwargs["feed_urls"])

        if not feed_urls:
            logger.warning("RSS 피드 URL이 설정되지 않았습니다")
            return []

        all_seminars: list[SeminarInfo] = []

        async with httpx.AsyncClient(timeout=30) as client:
            for url in feed_urls:
                try:
                    seminars = await self._fetch_from_feed(client, url)
                    all_seminars.extend(seminars)
                    logger.info(
                        "RSS 피드 수집 완료",
                        url=url,
                        count=len(seminars),
                    )
                except Exception as e:
                    logger.error(
                        "RSS 피드 수집 실패",
                        url=url,
                        error=str(e),
                    )

        # 키워드 필터링
        if keywords:
            all_seminars = self.filter_by_keywords(all_seminars, keywords)

        # 날짜 범위 필터링 (kwargs에서)
        if "start_date" in kwargs or "end_date" in kwargs:
            all_seminars = self.filter_by_date_range(
                all_seminars,
                kwargs.get("start_date"),
                kwargs.get("end_date"),
            )

        # 중복 제거 (URL 기준)
        seen_urls = set()
        unique_seminars = []
        for seminar in all_seminars:
            if seminar.url not in seen_urls:
                seen_urls.add(seminar.url)
                unique_seminars.append(seminar)

        # 최신순 정렬 및 제한
        unique_seminars.sort(
            key=lambda x: x.date or "9999-99-99",
            reverse=True,
        )

        return unique_seminars[:limit]

    async def _fetch_from_feed(
        self,
        client: httpx.AsyncClient,
        feed_url: str,
    ) -> list[SeminarInfo]:
        """
        단일 RSS 피드에서 항목 수집

        Args:
            client: HTTP 클라이언트
            feed_url: RSS 피드 URL

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        response = await client.get(feed_url)
        response.raise_for_status()

        xml_content = response.text
        seminars = self._parse_rss(xml_content, feed_url)

        return seminars

    def _parse_rss(self, xml_content: str, feed_url: str) -> list[SeminarInfo]:
        """
        RSS XML 파싱

        feedparser 없이 직접 정규식으로 파싱

        Args:
            xml_content: RSS XML 문자열
            feed_url: 피드 URL (소스 정보)

        Returns:
            list[SeminarInfo]: 파싱된 세미나 목록
        """
        seminars = []

        # <item> 또는 <entry> 블록 추출 (RSS 2.0 vs Atom)
        item_pattern = r"<item[^>]*>(.*?)</item>|<entry[^>]*>(.*?)</entry>"
        items = re.findall(item_pattern, xml_content, re.DOTALL | re.IGNORECASE)

        for item_match in items:
            item_content = item_match[0] or item_match[1]

            try:
                seminar = self._parse_item(item_content, feed_url)
                if seminar:
                    seminars.append(seminar)
            except Exception as e:
                logger.warning("RSS 항목 파싱 실패", error=str(e))

        return seminars

    def _parse_item(self, item_content: str, feed_url: str) -> SeminarInfo | None:
        """
        단일 RSS 항목 파싱

        Args:
            item_content: 항목 XML 내용
            feed_url: 피드 URL

        Returns:
            SeminarInfo | None
        """
        # 제목 추출
        title = self._extract_tag(item_content, "title")
        if not title:
            return None

        # URL 추출
        url = self._extract_tag(item_content, "link")
        if not url:
            # Atom 형식 링크
            link_match = re.search(r'<link[^>]+href="([^"]+)"', item_content)
            if link_match:
                url = link_match.group(1)

        if not url:
            return None

        # 설명 추출
        description = self._extract_tag(item_content, "description")
        if not description:
            description = self._extract_tag(item_content, "content")
            if not description:
                description = self._extract_tag(item_content, "summary")

        # HTML 태그 제거
        if description:
            description = re.sub(r"<[^>]+>", "", description)
            description = description.strip()[:1000]  # 최대 1000자

        # 날짜 추출
        date_str = self._extract_tag(item_content, "pubDate")
        if not date_str:
            date_str = self._extract_tag(item_content, "published")
            if not date_str:
                date_str = self._extract_tag(item_content, "updated")

        date = self._parse_date(date_str) if date_str else None

        # GUID 추출 (중복 체크용)
        guid = self._extract_tag(item_content, "guid")
        if not guid:
            guid = self._extract_tag(item_content, "id")

        # 카테고리 추출
        categories = re.findall(r"<category[^>]*>([^<]+)</category>", item_content)

        # 작성자/주최자 추출
        organizer = self._extract_tag(item_content, "author")
        if not organizer:
            organizer = self._extract_tag(item_content, "dc:creator")

        return SeminarInfo(
            title=title,
            url=url,
            source_type="rss",
            date=date,
            organizer=organizer,
            description=description,
            categories=categories,
            external_id=guid or url,
            raw_data={
                "feed_url": feed_url,
                "guid": guid,
            },
            fetched_at=datetime.now(UTC),
        )

    def _extract_tag(self, content: str, tag_name: str) -> str | None:
        """
        XML 태그 내용 추출

        Args:
            content: XML 내용
            tag_name: 태그 이름

        Returns:
            str | None: 태그 내용
        """
        # CDATA 지원
        pattern = rf"<{tag_name}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag_name}>"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _parse_date(self, date_str: str) -> str | None:
        """
        날짜 문자열 파싱

        다양한 형식 지원:
        - RFC 2822: Mon, 01 Jan 2025 12:00:00 +0000
        - ISO 8601: 2025-01-01T12:00:00Z
        - 기타 형식

        Args:
            date_str: 날짜 문자열

        Returns:
            str | None: YYYY-MM-DD 형식 날짜
        """
        try:
            # RFC 2822 형식 (pubDate)
            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass

        # ISO 8601 형식
        try:
            # Z를 +00:00으로 변환
            date_str_normalized = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(date_str_normalized)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # YYYY-MM-DD 형식 추출 시도
        match = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
        if match:
            return match.group(1)

        return None
