"""
외부 세미나 수집기 단위 테스트

RSS, OnOffMix, EventUs, DevEvent, Eventbrite 수집기 테스트
Festa는 2025.01.31 서비스 종료로 DEPRECATED
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.integrations.external_sources import (
    AI_AX_KEYWORDS,
    filter_by_ai_keywords,
    filter_excludes,
)
from backend.integrations.external_sources.base import SeminarInfo
from backend.integrations.external_sources.devevent_collector import DevEventCollector
from backend.integrations.external_sources.eventbrite_collector import EventbriteCollector
from backend.integrations.external_sources.eventus_collector import EventUsCollector
from backend.integrations.external_sources.festa_collector import FestaCollector
from backend.integrations.external_sources.health_check import (
    CollectorHealthChecker,
    HealthCheckResult,
    HealthStatus,
    run_health_check,
)
from backend.integrations.external_sources.onoffmix_collector import OnOffMixCollector
from backend.integrations.external_sources.rss_collector import RSSCollector

# ============================================================
# SeminarInfo 테스트
# ============================================================


class TestSeminarInfo:
    """SeminarInfo 데이터 모델 테스트"""

    def test_basic_creation(self):
        """기본 SeminarInfo 생성"""
        info = SeminarInfo(
            title="테스트 세미나",
            url="https://example.com/test",
            source_type="rss",
        )

        assert info.title == "테스트 세미나"
        assert info.url == "https://example.com/test"
        assert info.source_type == "rss"
        assert info.date is None
        assert info.categories == []

    def test_full_creation(self):
        """전체 필드가 있는 SeminarInfo 생성"""
        info = SeminarInfo(
            title="AI 컨퍼런스",
            url="https://example.com/ai-conf",
            source_type="festa",
            date="2026-05-15",
            end_date="2026-05-16",
            organizer="Tech Corp",
            description="AI 기술 발표",
            location="서울 코엑스",
            categories=["AI", "ML"],
            tags=["인공지능", "머신러닝"],
            external_id="festa_12345",
            raw_data={"original": "data"},
            fetched_at=datetime.now(UTC),
        )

        assert info.organizer == "Tech Corp"
        assert info.location == "서울 코엑스"
        assert len(info.categories) == 2
        assert info.external_id == "festa_12345"

    def test_to_activity_data(self):
        """Activity 데이터로 변환"""
        info = SeminarInfo(
            title="변환 테스트",
            url="https://example.com/convert",
            source_type="eventbrite",
            date="2026-06-01",
            organizer="Event Org",
            description="테스트 설명",
            categories=["Tech"],
            tags=["tag1", "tag2"],
            external_id="eb_99999",
        )

        activity_data = info.to_activity_data()

        assert activity_data["title"] == "변환 테스트"
        assert activity_data["url"] == "https://example.com/convert"
        assert activity_data["source_type"] == "eventbrite"
        assert activity_data["source"] == "대외"
        assert activity_data["channel"] == "데스크리서치"
        assert activity_data["themes"] == ["tag1", "tag2"]


# ============================================================
# RSS Collector 테스트
# ============================================================


class TestRSSCollector:
    """RSS 수집기 테스트"""

    def test_initialization(self):
        """RSS 수집기 초기화"""
        collector = RSSCollector(feed_urls=["https://example.com/feed.rss"])

        assert collector.name == "rss"
        assert len(collector.feed_urls) == 1

    def test_parse_date_rfc2822(self):
        """RFC 2822 형식 날짜 파싱"""
        collector = RSSCollector()

        # RFC 2822 형식
        date = collector._parse_date("Mon, 15 Jan 2026 12:00:00 +0000")
        assert date == "2026-01-15"

    def test_parse_date_iso8601(self):
        """ISO 8601 형식 날짜 파싱"""
        collector = RSSCollector()

        # ISO 8601 형식
        date = collector._parse_date("2026-03-20T10:30:00Z")
        assert date == "2026-03-20"

    def test_parse_date_simple(self):
        """단순 형식 날짜 파싱"""
        collector = RSSCollector()

        date = collector._parse_date("2026-12-25")
        assert date == "2026-12-25"

    def test_extract_tag(self):
        """XML 태그 추출"""
        collector = RSSCollector()
        content = "<description>테스트 설명입니다</description>"

        desc = collector._extract_tag(content, "description")
        assert desc == "테스트 설명입니다"

    def test_extract_tag_cdata(self):
        """CDATA가 포함된 태그 추출"""
        collector = RSSCollector()
        content = "<description><![CDATA[CDATA 내용]]></description>"

        desc = collector._extract_tag(content, "description")
        assert desc == "CDATA 내용"

    def test_parse_rss_item(self):
        """RSS 항목 파싱"""
        collector = RSSCollector()
        item_content = """
        <title>테스트 이벤트</title>
        <link>https://example.com/event</link>
        <description>이벤트 설명</description>
        <pubDate>Mon, 20 Jan 2026 10:00:00 +0000</pubDate>
        <guid>unique-id-123</guid>
        <category>Tech</category>
        """

        seminar = collector._parse_item(item_content, "https://example.com/feed.rss")

        assert seminar is not None
        assert seminar.title == "테스트 이벤트"
        assert seminar.url == "https://example.com/event"
        assert seminar.date == "2026-01-20"
        assert seminar.external_id == "unique-id-123"
        assert "Tech" in seminar.categories

    @pytest.mark.asyncio
    async def test_fetch_seminars_no_feeds(self):
        """피드 URL 없이 수집 시도"""
        collector = RSSCollector(feed_urls=[])  # 빈 목록으로 초기화

        result = await collector.fetch_seminars()

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_seminars_with_mock(self):
        """Mock HTTP로 RSS 수집"""
        collector = RSSCollector(feed_urls=["https://example.com/feed.rss"])

        mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
            <title>Test Feed</title>
            <item>
                <title>세미나 1</title>
                <link>https://example.com/seminar1</link>
                <pubDate>Mon, 20 Jan 2026 10:00:00 +0000</pubDate>
            </item>
            <item>
                <title>세미나 2</title>
                <link>https://example.com/seminar2</link>
                <pubDate>Tue, 21 Jan 2026 10:00:00 +0000</pubDate>
            </item>
        </channel>
        </rss>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = mock_rss
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await collector.fetch_seminars(limit=10)

        assert len(result) == 2
        assert result[0].source_type == "rss"

    def test_filter_by_keywords(self):
        """키워드 필터링"""
        collector = RSSCollector()
        seminars = [
            SeminarInfo(title="AI 컨퍼런스", url="https://a.com", source_type="rss"),
            SeminarInfo(title="웹 개발 세미나", url="https://b.com", source_type="rss"),
            SeminarInfo(title="AI/ML 워크샵", url="https://c.com", source_type="rss"),
        ]

        filtered = collector.filter_by_keywords(seminars, ["AI"])

        assert len(filtered) == 2
        assert all("AI" in s.title for s in filtered)

    def test_filter_by_date_range(self):
        """날짜 범위 필터링"""
        collector = RSSCollector()
        seminars = [
            SeminarInfo(
                title="과거 이벤트", url="https://a.com", source_type="rss", date="2025-01-01"
            ),
            SeminarInfo(
                title="현재 이벤트", url="https://b.com", source_type="rss", date="2026-06-15"
            ),
            SeminarInfo(
                title="미래 이벤트", url="https://c.com", source_type="rss", date="2027-12-01"
            ),
        ]

        filtered = collector.filter_by_date_range(
            seminars,
            start_date="2026-01-01",
            end_date="2026-12-31",
        )

        assert len(filtered) == 1
        assert filtered[0].title == "현재 이벤트"


# ============================================================
# Festa Collector 테스트 (DEPRECATED)
# ============================================================


class TestFestaCollector:
    """Festa 수집기 테스트 (DEPRECATED - 2025.01.31 서비스 종료)"""

    def test_initialization(self):
        """Festa 수집기 초기화"""
        collector = FestaCollector(api_key="test-key")

        assert collector.name == "festa"

    def test_category_mapping(self):
        """카테고리 매핑 확인"""
        assert "tech" in FestaCollector.CATEGORY_MAP
        assert "ai" in FestaCollector.CATEGORY_MAP
        assert "startup" in FestaCollector.CATEGORY_MAP

    @pytest.mark.asyncio
    async def test_fetch_seminars_returns_empty(self):
        """DEPRECATED: fetch_seminars는 항상 빈 목록 반환"""
        collector = FestaCollector()

        # 서비스 종료로 항상 빈 결과 반환
        result = await collector.fetch_seminars(categories=["tech"], limit=10)

        assert result == []

    def test_parse_event(self):
        """Festa 이벤트 JSON 파싱 (레거시 호환성)"""
        collector = FestaCollector()
        event = {
            "id": "12345",
            "title": "테스트 이벤트",
            "start_time": "2026-05-20T14:00:00",
            "description": "이벤트 설명",
            "organizer": {"name": "주최자"},
            "location": {"name": "서울"},
            "is_online": False,
        }

        seminar = collector._parse_event(event, "tech")

        assert seminar is not None
        assert seminar.title == "테스트 이벤트"
        assert seminar.external_id == "festa_12345"


# ============================================================
# OnOffMix Collector 테스트
# ============================================================


class TestOnOffMixCollector:
    """온오프믹스 수집기 테스트"""

    def test_initialization(self):
        """OnOffMix 수집기 초기화"""
        collector = OnOffMixCollector()

        assert collector.name == "onoffmix"
        assert collector.BASE_URL == "https://onoffmix.com"

    def test_parse_json_ld_event(self):
        """JSON-LD 이벤트 데이터 파싱"""
        collector = OnOffMixCollector()
        data = {
            "@type": "Event",
            "name": "AI 세미나",
            "url": "https://onoffmix.com/event/12345",
            "startDate": "2026-06-15T14:00:00",
            "location": {"name": "서울 강남"},
            "organizer": {"name": "Tech Corp"},
            "description": "AI 기술 세미나",
        }

        seminar = collector._parse_json_ld_event(data)

        assert seminar is not None
        assert seminar.title == "AI 세미나"
        assert seminar.date == "2026-06-15"
        assert seminar.source_type == "onoffmix"
        assert seminar.location == "서울 강남"

    def test_parse_json_ld_event_invalid(self):
        """유효하지 않은 JSON-LD 이벤트"""
        collector = OnOffMixCollector()

        # @type이 Event가 아닌 경우
        result = collector._parse_json_ld_event({"@type": "Organization"})
        assert result is None

        # 필수 필드 누락
        result = collector._parse_json_ld_event({"@type": "Event"})
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_seminars_with_mock(self):
        """Mock HTTP로 온오프믹스 수집"""
        collector = OnOffMixCollector()

        mock_html = """
        <html>
        <script type="application/ld+json">
        {"@type": "Event", "name": "AI 컨퍼런스", "url": "https://onoffmix.com/event/123", "startDate": "2026-07-01T10:00:00"}
        </script>
        </html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_html

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await collector.fetch_seminars(keywords=["AI"], limit=10)

        assert isinstance(result, list)


# ============================================================
# EventUs Collector 테스트
# ============================================================


class TestEventUsCollector:
    """이벤터스 수집기 테스트"""

    def test_initialization(self):
        """EventUs 수집기 초기화"""
        collector = EventUsCollector()

        assert collector.name == "eventus"
        assert collector.BASE_URL == "https://event-us.kr"

    def test_clean_title(self):
        """제목 정리"""
        collector = EventUsCollector()

        # HTML 태그 제거
        assert collector._clean_title("<b>테스트</b>") == "테스트"

        # 공백 정리
        assert collector._clean_title("  여러   공백  ") == "여러 공백"

        # HTML 엔티티
        assert collector._clean_title("A &amp; B") == "A & B"

    def test_parse_json_ld_event(self):
        """JSON-LD 이벤트 데이터 파싱"""
        collector = EventUsCollector()
        data = {
            "@type": "Event",
            "name": "LLM 워크샵",
            "url": "https://event-us.kr/channel/events/456",
            "startDate": "2026-08-20T09:00:00",
            "location": "온라인",
            "organizer": {"name": "AI Lab"},
            "description": "LLM 실습 워크샵",
        }

        seminar = collector._parse_json_ld_event(data)

        assert seminar is not None
        assert seminar.title == "LLM 워크샵"
        assert seminar.date == "2026-08-20"
        assert seminar.source_type == "eventus"

    @pytest.mark.asyncio
    async def test_fetch_seminars_with_mock(self):
        """Mock HTTP로 이벤터스 수집"""
        collector = EventUsCollector()

        mock_html = """
        <html>
        <script type="application/ld+json">
        {"@type": "Event", "name": "생성형AI 세미나", "url": "https://event-us.kr/events/789", "startDate": "2026-09-15T14:00:00"}
        </script>
        </html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_html

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await collector.fetch_seminars(keywords=["AI"], limit=10)

        assert isinstance(result, list)


# ============================================================
# DevEvent Collector 테스트
# ============================================================


class TestDevEventCollector:
    """Dev-Event (GitHub) 수집기 테스트"""

    def test_initialization(self):
        """DevEvent 수집기 초기화"""
        collector = DevEventCollector()

        assert collector.name == "devevent"
        assert "github" in collector.RAW_BASE_URL.lower()

    def test_parse_markdown(self):
        """마크다운 이벤트 파싱"""
        collector = DevEventCollector()
        markdown = """
# 2026년 1월

- [AI 컨퍼런스 2026](https://example.com/ai-conf)
  - 분류: `온라인`, `무료`, `AI` | 주최: Tech Corp | 접수: 01.15 ~ 01.20

- [LLM 해커톤](https://example.com/llm-hackathon)
  - 분류: `오프라인`, `유료`, `LLM` | 주최: AI Lab | 접수: 01.25 ~ 01.30
"""

        seminars = collector._parse_markdown(markdown, ["AI", "LLM"], 2026, 1)

        assert len(seminars) == 2
        assert seminars[0].title == "AI 컨퍼런스 2026"
        assert seminars[0].source_type == "devevent"
        assert "AI" in seminars[0].tags or any("AI" in c for c in seminars[0].categories)

    def test_parse_markdown_no_match(self):
        """키워드 미매칭 마크다운"""
        collector = DevEventCollector()
        markdown = """
- [웹 개발 세미나](https://example.com/web)
  - 분류: `온라인`, `무료` | 주최: Web Corp
"""

        seminars = collector._parse_markdown(markdown, ["AI", "LLM"], 2026, 1)

        # AI/LLM 키워드 없으면 빈 결과
        assert len(seminars) == 0

    @pytest.mark.asyncio
    async def test_fetch_seminars_with_mock(self):
        """Mock HTTP로 DevEvent 수집"""
        collector = DevEventCollector()

        mock_markdown = """
# 이벤트

- [GPT 워크샵](https://example.com/gpt)
  - 분류: `온라인`, `무료`, `GPT` | 주최: OpenAI KR | 접수: 01.10 ~ 01.15
"""

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_markdown

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await collector.fetch_seminars(keywords=["GPT"], limit=10)

        assert isinstance(result, list)


# ============================================================
# Keywords 유틸리티 테스트
# ============================================================


class TestKeywordsUtility:
    """AI/AX 키워드 유틸리티 테스트"""

    def test_ai_ax_keywords_exists(self):
        """AI_AX_KEYWORDS 상수 확인"""
        assert len(AI_AX_KEYWORDS) > 0
        assert "AI" in AI_AX_KEYWORDS
        assert "LLM" in AI_AX_KEYWORDS
        assert "인공지능" in AI_AX_KEYWORDS

    def test_filter_by_ai_keywords(self):
        """AI 키워드 필터링"""
        assert filter_by_ai_keywords("AI 기반 솔루션") is True
        assert filter_by_ai_keywords("인공지능 서비스") is True
        assert filter_by_ai_keywords("LLM 활용 사례") is True
        assert filter_by_ai_keywords("일반 웹 개발") is False

    def test_filter_by_ai_keywords_min_matches(self):
        """최소 매칭 개수 필터링"""
        # 여러 키워드 매칭
        assert filter_by_ai_keywords("AI와 LLM 기반 자동화", min_matches=2) is True
        # 하나만 매칭 (키워드가 하나만 있는 텍스트)
        assert filter_by_ai_keywords("데이터베이스 설계", min_matches=2) is False

    def test_filter_excludes(self):
        """제외 키워드 필터링"""
        assert filter_excludes("AI 개발자 채용") is True
        assert filter_excludes("인턴 모집") is True
        assert filter_excludes("AI 기술 세미나") is False


# ============================================================
# Eventbrite Collector 테스트
# ============================================================


class TestEventbriteCollector:
    """Eventbrite 수집기 테스트"""

    def test_initialization(self):
        """Eventbrite 수집기 초기화"""
        collector = EventbriteCollector(api_token="test-token")

        assert collector.name == "eventbrite"
        assert collector.api_token == "test-token"

    def test_category_ids(self):
        """카테고리 ID 매핑 확인"""
        assert "tech" in EventbriteCollector.CATEGORY_IDS
        assert "business" in EventbriteCollector.CATEGORY_IDS

    def test_parse_event(self):
        """Eventbrite 이벤트 JSON 파싱"""
        collector = EventbriteCollector()
        event = {
            "id": "999888777",
            "name": {"text": "글로벌 테크 서밋"},
            "url": "https://eventbrite.com/e/999888777",
            "start": {"local": "2026-07-15T09:00:00"},
            "end": {"local": "2026-07-15T18:00:00"},
            "description": {"text": "기술 컨퍼런스"},
            "venue": {"name": "컨벤션 센터"},
            "organizer": {"name": "Tech Events"},
            "category": {"name": "Technology"},
            "online_event": False,
            "is_free": True,
        }

        seminar = collector._parse_event(event)

        assert seminar is not None
        assert seminar.title == "글로벌 테크 서밋"
        assert seminar.date == "2026-07-15"
        assert seminar.external_id == "eventbrite_999888777"
        assert seminar.source_type == "eventbrite"
        assert seminar.location == "컨벤션 센터"

    def test_parse_event_online(self):
        """온라인 Eventbrite 이벤트 파싱"""
        collector = EventbriteCollector()
        event = {
            "id": "111222333",
            "name": {"text": "온라인 워크샵"},
            "url": "https://eventbrite.com/e/111222333",
            "start": {"local": "2026-08-01T14:00:00"},
            "online_event": True,
        }

        seminar = collector._parse_event(event)

        assert seminar is not None
        assert seminar.location == "온라인"

    def test_parse_event_invalid(self):
        """유효하지 않은 이벤트 파싱"""
        collector = EventbriteCollector()
        event = {}  # 필수 필드 없음

        seminar = collector._parse_event(event)

        assert seminar is None

    def test_parse_html_events(self):
        """HTML에서 이벤트 파싱"""
        collector = EventbriteCollector()
        html = """
        <a href="https://www.eventbrite.com/e/tech-summit-123456">Tech Summit</a>
        <a href="https://www.eventbrite.com/e/ai-workshop-789012">AI Workshop</a>
        """

        seminars = collector._parse_html_events(html)

        assert len(seminars) == 2
        assert seminars[0].external_id == "eventbrite_123456"

    @pytest.mark.asyncio
    async def test_fetch_seminars_no_token(self):
        """API 토큰 없이 수집 (공개 검색)"""
        collector = EventbriteCollector()  # 토큰 없음

        # 공개 검색을 시도하지만 실제 HTTP 요청은 Mock
        with patch.object(collector, "_fetch_public_events", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            seminars = await collector.fetch_seminars(keywords=["tech"], limit=5)

            mock_fetch.assert_called_once()
            assert seminars == []

    @pytest.mark.asyncio
    async def test_fetch_seminars_with_token_mock(self):
        """API 토큰으로 수집 (Mock)"""
        collector = EventbriteCollector(api_token="test-token")

        mock_events = {
            "events": [
                {
                    "id": "111",
                    "name": {"text": "이벤트 1"},
                    "url": "https://eventbrite.com/e/111",
                    "start": {"local": "2026-09-01T10:00:00"},
                },
            ],
            "pagination": {"object_count": 1},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value=mock_events)

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await collector.fetch_seminars(keywords=["tech"], limit=10)

        assert isinstance(result, list)


# ============================================================
# 공통 필터링 테스트
# ============================================================


class TestCollectorFiltering:
    """수집기 공통 필터링 기능 테스트"""

    def test_filter_by_keywords_case_insensitive(self):
        """대소문자 구분 없이 키워드 필터링"""
        collector = RSSCollector()
        seminars = [
            SeminarInfo(title="ai conference", url="https://a.com", source_type="rss"),
            SeminarInfo(title="AI Workshop", url="https://b.com", source_type="rss"),
            SeminarInfo(title="Machine Learning", url="https://c.com", source_type="rss"),
        ]

        filtered = collector.filter_by_keywords(seminars, ["AI"])

        assert len(filtered) == 2

    def test_filter_by_keywords_in_description(self):
        """설명에서 키워드 필터링"""
        collector = RSSCollector()
        seminars = [
            SeminarInfo(
                title="일반 세미나",
                url="https://a.com",
                source_type="rss",
                description="AI와 ML에 대해 다룹니다",
            ),
            SeminarInfo(
                title="다른 주제",
                url="https://b.com",
                source_type="rss",
                description="웹 개발",
            ),
        ]

        filtered = collector.filter_by_keywords(seminars, ["AI"])

        assert len(filtered) == 1
        assert filtered[0].title == "일반 세미나"

    def test_filter_by_date_range_start_only(self):
        """시작일만 지정하여 필터링"""
        collector = RSSCollector()
        seminars = [
            SeminarInfo(title="과거", url="https://a.com", source_type="rss", date="2025-06-01"),
            SeminarInfo(title="미래", url="https://b.com", source_type="rss", date="2027-06-01"),
        ]

        filtered = collector.filter_by_date_range(seminars, start_date="2026-01-01")

        assert len(filtered) == 1
        assert filtered[0].title == "미래"

    def test_filter_by_date_range_end_only(self):
        """종료일만 지정하여 필터링"""
        collector = RSSCollector()
        seminars = [
            SeminarInfo(title="과거", url="https://a.com", source_type="rss", date="2025-06-01"),
            SeminarInfo(title="미래", url="https://b.com", source_type="rss", date="2027-06-01"),
        ]

        filtered = collector.filter_by_date_range(seminars, end_date="2026-12-31")

        assert len(filtered) == 1
        assert filtered[0].title == "과거"

    def test_filter_empty_keywords(self):
        """빈 키워드로 필터링 (전체 반환)"""
        collector = RSSCollector()
        seminars = [
            SeminarInfo(title="세미나 1", url="https://a.com", source_type="rss"),
            SeminarInfo(title="세미나 2", url="https://b.com", source_type="rss"),
        ]

        filtered = collector.filter_by_keywords(seminars, [])

        assert len(filtered) == 2

    def test_filter_no_date(self):
        """날짜 없는 항목은 날짜 필터에서 제외"""
        collector = RSSCollector()
        seminars = [
            SeminarInfo(title="날짜 없음", url="https://a.com", source_type="rss", date=None),
            SeminarInfo(
                title="날짜 있음", url="https://b.com", source_type="rss", date="2026-06-01"
            ),
        ]

        filtered = collector.filter_by_date_range(seminars, start_date="2026-01-01")

        assert len(filtered) == 1
        assert filtered[0].title == "날짜 있음"


# ============================================================
# Collector Health Check 테스트
# ============================================================


class TestCollectorHealthCheck:
    """수집기 헬스체크 테스트"""

    def test_health_status_enum(self):
        """HealthStatus Enum 확인"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_health_check_result_creation(self):
        """HealthCheckResult 생성"""
        result = HealthCheckResult(
            collector_name="onoffmix",
            status=HealthStatus.HEALTHY,
            sample_count=5,
        )

        assert result.collector_name == "onoffmix"
        assert result.status == HealthStatus.HEALTHY
        assert result.sample_count == 5
        assert result.error_message is None
        assert result.checked_at is not None

    def test_health_check_result_to_dict(self):
        """HealthCheckResult 딕셔너리 변환"""
        result = HealthCheckResult(
            collector_name="eventus",
            status=HealthStatus.DEGRADED,
            sample_count=0,
            error_message="수집 결과 없음",
            response_time_ms=1234.56,
        )

        data = result.to_dict()

        assert data["collector_name"] == "eventus"
        assert data["status"] == "degraded"
        assert data["sample_count"] == 0
        assert data["error_message"] == "수집 결과 없음"
        assert data["response_time_ms"] == 1234.56
        assert "checked_at" in data

    def test_collector_health_checker_initialization(self):
        """CollectorHealthChecker 초기화"""
        checker = CollectorHealthChecker()

        assert checker.onoffmix is not None
        assert checker.eventus is not None
        assert checker.onoffmix.name == "onoffmix"
        assert checker.eventus.name == "eventus"

    @pytest.mark.asyncio
    async def test_check_onoffmix_healthy(self):
        """OnOffMix 헬스체크 - 정상"""
        checker = CollectorHealthChecker()

        mock_seminars = [
            SeminarInfo(title="AI 세미나", url="https://test.com", source_type="onoffmix"),
        ]

        with patch.object(checker.onoffmix, "fetch_seminars", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_seminars

            result = await checker.check_onoffmix()

            assert result.status == HealthStatus.HEALTHY
            assert result.sample_count == 1
            assert result.error_message is None

    @pytest.mark.asyncio
    async def test_check_onoffmix_degraded(self):
        """OnOffMix 헬스체크 - 저하 (0건 수집)"""
        checker = CollectorHealthChecker()

        with patch.object(checker.onoffmix, "fetch_seminars", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []  # 빈 결과

            result = await checker.check_onoffmix()

            assert result.status == HealthStatus.DEGRADED
            assert result.sample_count == 0
            assert "HTML 구조 변경" in result.error_message

    @pytest.mark.asyncio
    async def test_check_onoffmix_unhealthy(self):
        """OnOffMix 헬스체크 - 비정상 (예외 발생)"""
        checker = CollectorHealthChecker()

        with patch.object(checker.onoffmix, "fetch_seminars", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("연결 오류")

            result = await checker.check_onoffmix()

            assert result.status == HealthStatus.UNHEALTHY
            assert "연결 오류" in result.error_message

    @pytest.mark.asyncio
    async def test_check_eventus_healthy(self):
        """EventUs 헬스체크 - 정상"""
        checker = CollectorHealthChecker()

        mock_seminars = [
            SeminarInfo(title="LLM 워크샵", url="https://test.com", source_type="eventus"),
            SeminarInfo(title="AI 컨퍼런스", url="https://test2.com", source_type="eventus"),
        ]

        with patch.object(checker.eventus, "fetch_seminars", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_seminars

            result = await checker.check_eventus()

            assert result.status == HealthStatus.HEALTHY
            assert result.sample_count == 2

    @pytest.mark.asyncio
    async def test_check_all(self):
        """전체 헬스체크 (4개 수집기)"""
        checker = CollectorHealthChecker()

        with patch.object(
            checker.onoffmix, "fetch_seminars", new_callable=AsyncMock
        ) as mock_onoffmix:
            with patch.object(
                checker.eventus, "fetch_seminars", new_callable=AsyncMock
            ) as mock_eventus:
                with patch.object(
                    checker.devevent, "fetch_seminars", new_callable=AsyncMock
                ) as mock_devevent:
                    with patch.object(
                        checker.rss, "fetch_seminars", new_callable=AsyncMock
                    ) as mock_rss:
                        mock_onoffmix.return_value = [
                            SeminarInfo(
                                title="세미나1", url="https://a.com", source_type="onoffmix"
                            ),
                        ]
                        mock_eventus.return_value = []  # EventUs는 저하 상태
                        mock_devevent.return_value = [
                            SeminarInfo(
                                title="세미나2", url="https://b.com", source_type="devevent"
                            ),
                        ]
                        mock_rss.return_value = [
                            SeminarInfo(title="세미나3", url="https://c.com", source_type="rss"),
                        ]

                        results = await checker.check_all()

                        assert len(results) == 4
                        assert results[0].collector_name == "onoffmix"
                        assert results[0].status == HealthStatus.HEALTHY
                        assert results[1].collector_name == "eventus"
                        assert results[1].status == HealthStatus.DEGRADED
                        assert results[2].collector_name == "devevent"
                        assert results[2].status == HealthStatus.HEALTHY
                        assert results[3].collector_name == "rss"
                        assert results[3].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_run_health_check_helper(self):
        """run_health_check 헬퍼 함수"""
        with patch.object(
            CollectorHealthChecker, "check_all", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = [
                HealthCheckResult(
                    collector_name="onoffmix",
                    status=HealthStatus.HEALTHY,
                    sample_count=3,
                ),
                HealthCheckResult(
                    collector_name="eventus",
                    status=HealthStatus.HEALTHY,
                    sample_count=2,
                ),
            ]

            result = await run_health_check()

            assert "checked_at" in result
            assert "results" in result
            assert "summary" in result
            assert result["summary"]["total"] == 2
            assert result["summary"]["healthy"] == 2
            assert result["summary"]["degraded"] == 0
            assert result["summary"]["unhealthy"] == 0
