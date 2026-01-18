"""
WebhookProcessor 단위 테스트

웹훅 페이로드 처리 및 Activity 생성 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.webhook_processor import (
    EventbriteWebhookPayload,
    FestaWebhookPayload,
    RSSWebhookPayload,
    WebhookProcessor,
    WebhookProcessResult,
    verify_webhook_signature,
)

# ============================================================
# 페이로드 모델 테스트
# ============================================================


class TestRSSWebhookPayload:
    """RSS 웹훅 페이로드 테스트"""

    def test_basic_payload(self):
        """기본 RSS 페이로드"""
        payload = RSSWebhookPayload(
            title="테스트 세미나",
            url="https://example.com/test",
        )

        assert payload.title == "테스트 세미나"
        assert payload.url == "https://example.com/test"
        assert payload.source == "ifttt"  # 기본값

    def test_full_payload(self):
        """전체 필드가 있는 RSS 페이로드"""
        payload = RSSWebhookPayload(
            title="AI 컨퍼런스",
            url="https://example.com/ai-conf",
            published="Mon, 15 Jan 2026 10:00:00 +0000",
            description="AI 기술 발표",
            author="Tech Corp",
            feed_url="https://example.com/feed.rss",
            guid="unique-guid-123",
            source="zapier",
            timestamp="2026-01-15T10:00:00Z",
        )

        assert payload.published is not None
        assert payload.guid == "unique-guid-123"
        assert payload.source == "zapier"


class TestFestaWebhookPayload:
    """Festa 웹훅 페이로드 테스트"""

    def test_basic_payload(self):
        """기본 Festa 페이로드"""
        payload = FestaWebhookPayload(
            event_id="12345",
            title="테스트 이벤트",
        )

        assert payload.event_id == "12345"
        assert payload.event_type == "event.created"  # 기본값

    def test_event_deleted(self):
        """삭제 이벤트 페이로드"""
        payload = FestaWebhookPayload(
            event_id="12345",
            title="삭제된 이벤트",
            event_type="event.deleted",
        )

        assert payload.event_type == "event.deleted"

    def test_online_event(self):
        """온라인 이벤트 페이로드"""
        payload = FestaWebhookPayload(
            event_id="99999",
            title="온라인 웨비나",
            is_online=True,
            location=None,
        )

        assert payload.is_online is True


class TestEventbriteWebhookPayload:
    """Eventbrite 웹훅 페이로드 테스트"""

    def test_api_url_payload(self):
        """API URL만 있는 페이로드"""
        payload = EventbriteWebhookPayload(
            api_url="https://www.eventbriteapi.com/v3/events/123456/",
        )

        assert payload.api_url.endswith("123456/")
        assert payload.event_id is None

    def test_full_payload(self):
        """전체 데이터가 있는 페이로드"""
        payload = EventbriteWebhookPayload(
            api_url="https://www.eventbriteapi.com/v3/events/123456/",
            event_id="123456",
            title="글로벌 테크 서밋",
            url="https://eventbrite.com/e/123456",
            date="2026-07-15",
            organizer="Tech Events",
            is_online=False,
        )

        assert payload.title == "글로벌 테크 서밋"
        assert payload.event_id == "123456"


# ============================================================
# WebhookProcessor 테스트
# ============================================================


class TestWebhookProcessor:
    """WebhookProcessor 테스트"""

    @pytest.mark.asyncio
    async def test_process_rss_webhook_basic(self, test_db_session):
        """기본 RSS 웹훅 처리"""
        processor = WebhookProcessor(test_db_session)
        payload = RSSWebhookPayload(
            title="테스트 세미나",
            url="https://example.com/rss-test-webhook",
            published="2026-03-15",
        )

        result = await processor.process_rss_webhook(payload)

        assert result.success is True
        assert result.activity_id is not None
        assert result.activity_id.startswith("ACT-")
        assert result.is_duplicate is False

    @pytest.mark.asyncio
    async def test_process_rss_webhook_duplicate(self, test_db_session):
        """중복 RSS 웹훅 처리"""
        processor = WebhookProcessor(test_db_session)
        payload = RSSWebhookPayload(
            title="중복 테스트 세미나",
            url="https://example.com/duplicate-rss-webhook",
        )

        # 첫 번째 처리
        result1 = await processor.process_rss_webhook(payload)
        assert result1.success is True
        assert result1.is_duplicate is False

        # 두 번째 처리 (중복)
        result2 = await processor.process_rss_webhook(payload)
        assert result2.success is True
        assert result2.is_duplicate is True
        assert result2.activity_id == result1.activity_id

    @pytest.mark.asyncio
    async def test_process_rss_webhook_with_guid(self, test_db_session):
        """GUID가 있는 RSS 웹훅 처리"""
        processor = WebhookProcessor(test_db_session)
        payload = RSSWebhookPayload(
            title="GUID 테스트",
            url="https://example.com/guid-test",
            guid="unique-rss-guid-12345",
        )

        result = await processor.process_rss_webhook(payload)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_process_festa_webhook_created(self, test_db_session):
        """Festa 이벤트 생성 웹훅 처리"""
        processor = WebhookProcessor(test_db_session)
        payload = FestaWebhookPayload(
            event_id="festa-12345",
            title="Festa 테스트 이벤트",
            url="https://festa.io/events/12345",
            date="2026-05-20",
            organizer="Tech Meetup",
            category="tech",
            is_online=False,
        )

        result = await processor.process_festa_webhook(payload)

        assert result.success is True
        assert result.activity_id is not None
        assert result.is_duplicate is False

    @pytest.mark.asyncio
    async def test_process_festa_webhook_deleted(self, test_db_session):
        """Festa 삭제 이벤트 웹훅 처리"""
        processor = WebhookProcessor(test_db_session)
        payload = FestaWebhookPayload(
            event_id="festa-99999",
            title="삭제된 이벤트",
            event_type="event.deleted",
        )

        result = await processor.process_festa_webhook(payload)

        assert result.success is True
        assert result.activity_id is None
        assert "무시" in result.message

    @pytest.mark.asyncio
    async def test_process_festa_webhook_online(self, test_db_session):
        """Festa 온라인 이벤트 웹훅 처리"""
        processor = WebhookProcessor(test_db_session)
        payload = FestaWebhookPayload(
            event_id="festa-online-001",
            title="온라인 웨비나",
            is_online=True,
            date="2026-06-01",
        )

        result = await processor.process_festa_webhook(payload)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_process_eventbrite_webhook_with_data(self, test_db_session):
        """데이터가 포함된 Eventbrite 웹훅 처리"""
        processor = WebhookProcessor(test_db_session)
        payload = EventbriteWebhookPayload(
            api_url="https://www.eventbriteapi.com/v3/events/123456/",
            event_id="123456",
            title="Eventbrite 테스트 이벤트",
            url="https://eventbrite.com/e/123456",
            date="2026-08-15",
            organizer="Event Org",
            is_online=False,
        )

        result = await processor.process_eventbrite_webhook(payload)

        assert result.success is True
        assert result.activity_id is not None

    @pytest.mark.asyncio
    async def test_process_eventbrite_webhook_api_only(self, test_db_session):
        """API URL만 있는 Eventbrite 웹훅 처리"""
        processor = WebhookProcessor(test_db_session)
        payload = EventbriteWebhookPayload(
            api_url="https://www.eventbriteapi.com/v3/events/789012/",
        )

        # EventbriteCollector.fetch_event_detail을 Mock
        with patch("backend.integrations.external_sources.EventbriteCollector") as MockCollector:
            mock_collector = MagicMock()
            mock_collector.fetch_event_detail = AsyncMock(return_value=None)
            MockCollector.return_value = mock_collector

            result = await processor.process_eventbrite_webhook(payload)

        # 상세 정보를 가져올 수 없으면 실패
        assert result.success is False
        assert "상세 정보" in result.error

    def test_parse_date_rfc2822(self):
        """RFC 2822 형식 날짜 파싱"""
        processor = WebhookProcessor(MagicMock())

        date = processor._parse_date("Mon, 15 Jan 2026 12:00:00 +0000")

        assert date == "2026-01-15"

    def test_parse_date_iso8601(self):
        """ISO 8601 형식 날짜 파싱"""
        processor = WebhookProcessor(MagicMock())

        date = processor._parse_date("2026-03-20T10:30:00Z")

        assert date == "2026-03-20"

    def test_parse_date_simple(self):
        """단순 형식 날짜 파싱"""
        processor = WebhookProcessor(MagicMock())

        date = processor._parse_date("2026-12-25")

        assert date == "2026-12-25"

    def test_parse_date_none(self):
        """None 날짜 파싱"""
        processor = WebhookProcessor(MagicMock())

        date = processor._parse_date(None)

        assert date is None


# ============================================================
# 웹훅 서명 검증 테스트
# ============================================================


class TestWebhookSignatureVerification:
    """웹훅 서명 검증 테스트"""

    def test_verify_sha256_valid(self):
        """유효한 SHA256 서명 검증"""
        import hashlib
        import hmac

        payload = b'{"event": "test"}'
        secret = "test-secret"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        result = verify_webhook_signature(payload, signature, secret, "sha256")

        assert result is True

    def test_verify_sha256_invalid(self):
        """유효하지 않은 SHA256 서명 검증"""
        payload = b'{"event": "test"}'
        secret = "test-secret"
        wrong_signature = "invalid-signature"

        result = verify_webhook_signature(payload, wrong_signature, secret, "sha256")

        assert result is False

    def test_verify_sha1_valid(self):
        """유효한 SHA1 서명 검증"""
        import hashlib
        import hmac

        payload = b'{"event": "test"}'
        secret = "test-secret"
        signature = hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()

        result = verify_webhook_signature(payload, signature, secret, "sha1")

        assert result is True

    def test_verify_prefixed_signature(self):
        """접두사가 있는 서명 검증 (sha256=xxx)"""
        import hashlib
        import hmac

        payload = b'{"event": "test"}'
        secret = "test-secret"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        prefixed_signature = f"sha256={signature}"

        result = verify_webhook_signature(payload, prefixed_signature, secret, "sha256")

        assert result is True

    def test_verify_unsupported_algorithm(self):
        """지원하지 않는 알고리즘"""
        payload = b'{"event": "test"}'
        secret = "test-secret"
        signature = "any-signature"

        result = verify_webhook_signature(payload, signature, secret, "md5")

        assert result is False


# ============================================================
# WebhookProcessResult 테스트
# ============================================================


class TestWebhookProcessResult:
    """WebhookProcessResult 모델 테스트"""

    def test_success_result(self):
        """성공 결과"""
        result = WebhookProcessResult(
            success=True,
            activity_id="ACT-2026-00001",
            is_duplicate=False,
            message="Activity 생성 완료",
        )

        assert result.success is True
        assert result.activity_id == "ACT-2026-00001"
        assert result.error is None

    def test_duplicate_result(self):
        """중복 결과"""
        result = WebhookProcessResult(
            success=True,
            activity_id="ACT-2026-00001",
            is_duplicate=True,
            message="중복 Activity",
        )

        assert result.success is True
        assert result.is_duplicate is True

    def test_error_result(self):
        """에러 결과"""
        result = WebhookProcessResult(
            success=False,
            error="처리 중 오류 발생",
            message="웹훅 처리 실패",
        )

        assert result.success is False
        assert result.activity_id is None
        assert result.error == "처리 중 오류 발생"


# ============================================================
# 에러 처리 테스트
# ============================================================


class TestWebhookProcessorErrorHandling:
    """WebhookProcessor 에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_rss_webhook_error_handling(self, test_db_session):
        """RSS 웹훅 에러 처리"""
        processor = WebhookProcessor(test_db_session)

        # 잘못된 데이터로 페이로드 생성 (빈 URL은 실제로 허용됨)
        # 대신 DB 저장 중 오류를 시뮬레이션
        with patch.object(processor, "_save_activity", new_callable=AsyncMock) as mock_save:
            mock_save.side_effect = Exception("DB 연결 오류")

            payload = RSSWebhookPayload(
                title="에러 테스트",
                url="https://example.com/error-test",
            )

            result = await processor.process_rss_webhook(payload)

            assert result.success is False
            assert "DB 연결 오류" in result.error

    @pytest.mark.asyncio
    async def test_eventbrite_webhook_no_event_id(self, test_db_session):
        """이벤트 ID 없는 Eventbrite 웹훅"""
        processor = WebhookProcessor(test_db_session)
        payload = EventbriteWebhookPayload(
            api_url="https://invalid-url/without/events/",
        )

        result = await processor.process_eventbrite_webhook(payload)

        # event_id를 추출할 수 없으면 실패
        assert result.success is False
        assert "Event ID" in result.error
