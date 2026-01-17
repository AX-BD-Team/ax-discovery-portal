"""
웹훅 처리 서비스

외부 소스(RSS, Festa, Eventbrite)에서 실시간으로 수신되는
웹훅 페이로드를 처리하여 Activity로 변환
"""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.repositories.activity import activity_repo
from backend.integrations.external_sources.base import SeminarInfo

logger = structlog.get_logger()


# ============================================================
# 웹훅 페이로드 모델
# ============================================================


class RSSWebhookPayload(BaseModel):
    """RSS 웹훅 페이로드 (IFTTT/Zapier 등에서 전송)"""

    title: str
    url: str
    published: str | None = None  # 발행일
    description: str | None = None
    author: str | None = None
    feed_url: str | None = None  # 원본 피드 URL
    guid: str | None = None  # RSS guid

    # IFTTT/Zapier 메타데이터
    source: str = "ifttt"  # ifttt, zapier, custom
    timestamp: str | None = None


class FestaWebhookPayload(BaseModel):
    """Festa 웹훅 페이로드"""

    event_id: str
    title: str
    url: str | None = None
    date: str | None = None  # YYYY-MM-DD
    end_date: str | None = None
    organizer: str | None = None
    description: str | None = None
    location: str | None = None
    category: str | None = None
    is_online: bool = False
    ticket_price: int | None = None

    # 웹훅 메타데이터
    event_type: str = "event.created"  # event.created, event.updated, event.deleted
    timestamp: str | None = None


class EventbriteWebhookPayload(BaseModel):
    """Eventbrite 웹훅 페이로드"""

    api_url: str  # Eventbrite API URL (상세 조회용)
    event_id: str | None = None

    # 직접 전달되는 경우
    title: str | None = None
    url: str | None = None
    date: str | None = None
    organizer: str | None = None
    description: str | None = None
    location: str | None = None
    is_online: bool = False

    # 웹훅 메타데이터
    config: dict[str, Any] = Field(default_factory=dict)


class WebhookProcessResult(BaseModel):
    """웹훅 처리 결과"""

    success: bool
    activity_id: str | None = None
    is_duplicate: bool = False
    message: str = ""
    error: str | None = None


# ============================================================
# 웹훅 처리기
# ============================================================


class WebhookProcessor:
    """웹훅 처리 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logger.bind(service="webhook_processor")

    async def process_rss_webhook(
        self,
        payload: RSSWebhookPayload,
        play_id: str = "EXT_Desk_D01_Seminar",
    ) -> WebhookProcessResult:
        """
        RSS 웹훅 처리

        Args:
            payload: RSS 웹훅 페이로드
            play_id: Play ID

        Returns:
            WebhookProcessResult: 처리 결과
        """
        self.logger.info(
            "Processing RSS webhook",
            url=payload.url,
            title=payload.title[:50] if payload.title else None,
        )

        try:
            # SeminarInfo로 변환
            seminar = SeminarInfo(
                title=payload.title,
                url=payload.url,
                source_type="rss",
                date=self._parse_date(payload.published),
                organizer=payload.author,
                description=payload.description,
                external_id=payload.guid or payload.url,
                raw_data={
                    "feed_url": payload.feed_url,
                    "webhook_source": payload.source,
                    "webhook_timestamp": payload.timestamp,
                },
                fetched_at=datetime.now(UTC),
            )

            return await self._save_activity(seminar, play_id)

        except Exception as e:
            self.logger.error("RSS webhook processing failed", error=str(e))
            return WebhookProcessResult(
                success=False,
                error=str(e),
                message="RSS 웹훅 처리 실패",
            )

    async def process_festa_webhook(
        self,
        payload: FestaWebhookPayload,
        play_id: str = "EXT_Desk_D01_Seminar",
    ) -> WebhookProcessResult:
        """
        Festa 웹훅 처리

        Args:
            payload: Festa 웹훅 페이로드
            play_id: Play ID

        Returns:
            WebhookProcessResult: 처리 결과
        """
        self.logger.info(
            "Processing Festa webhook",
            event_id=payload.event_id,
            event_type=payload.event_type,
        )

        # 삭제 이벤트는 무시 (또는 별도 처리)
        if payload.event_type == "event.deleted":
            return WebhookProcessResult(
                success=True,
                message="삭제 이벤트는 무시됨",
            )

        try:
            # SeminarInfo로 변환
            seminar = SeminarInfo(
                title=payload.title,
                url=payload.url or f"https://festa.io/events/{payload.event_id}",
                source_type="festa",
                date=payload.date,
                end_date=payload.end_date,
                organizer=payload.organizer,
                description=payload.description,
                location="온라인" if payload.is_online else payload.location,
                categories=[payload.category] if payload.category else [],
                external_id=f"festa_{payload.event_id}",
                raw_data={
                    "event_id": payload.event_id,
                    "is_online": payload.is_online,
                    "ticket_price": payload.ticket_price,
                    "event_type": payload.event_type,
                    "webhook_timestamp": payload.timestamp,
                },
                fetched_at=datetime.now(UTC),
            )

            return await self._save_activity(seminar, play_id)

        except Exception as e:
            self.logger.error("Festa webhook processing failed", error=str(e))
            return WebhookProcessResult(
                success=False,
                error=str(e),
                message="Festa 웹훅 처리 실패",
            )

    async def process_eventbrite_webhook(
        self,
        payload: EventbriteWebhookPayload,
        play_id: str = "EXT_Desk_D01_Seminar",
    ) -> WebhookProcessResult:
        """
        Eventbrite 웹훅 처리

        Args:
            payload: Eventbrite 웹훅 페이로드
            play_id: Play ID

        Returns:
            WebhookProcessResult: 처리 결과
        """
        self.logger.info(
            "Processing Eventbrite webhook",
            api_url=payload.api_url,
            event_id=payload.event_id,
        )

        try:
            # 이벤트 ID 추출
            event_id = payload.event_id
            if not event_id and payload.api_url:
                # api_url에서 event_id 추출
                # 예: https://www.eventbriteapi.com/v3/events/123456/
                parts = payload.api_url.rstrip("/").split("/")
                if "events" in parts:
                    idx = parts.index("events")
                    if idx + 1 < len(parts):
                        event_id = parts[idx + 1]

            if not event_id:
                return WebhookProcessResult(
                    success=False,
                    error="Event ID를 추출할 수 없습니다",
                    message="Eventbrite 웹훅 처리 실패",
                )

            # 직접 전달된 데이터가 있으면 사용
            if payload.title and payload.url:
                seminar = SeminarInfo(
                    title=payload.title,
                    url=payload.url,
                    source_type="eventbrite",
                    date=payload.date,
                    organizer=payload.organizer,
                    description=payload.description,
                    location="온라인" if payload.is_online else payload.location,
                    external_id=f"eventbrite_{event_id}",
                    raw_data={
                        "event_id": event_id,
                        "api_url": payload.api_url,
                        "is_online": payload.is_online,
                    },
                    fetched_at=datetime.now(UTC),
                )
            else:
                # API에서 상세 정보 조회 필요
                from backend.integrations.external_sources import EventbriteCollector

                collector = EventbriteCollector()
                fetched_seminar = await collector.fetch_event_detail(event_id)

                if not fetched_seminar:
                    return WebhookProcessResult(
                        success=False,
                        error="이벤트 상세 정보를 가져올 수 없습니다",
                        message="Eventbrite 웹훅 처리 실패",
                    )
                seminar = fetched_seminar

            return await self._save_activity(seminar, play_id)

        except Exception as e:
            self.logger.error("Eventbrite webhook processing failed", error=str(e))
            return WebhookProcessResult(
                success=False,
                error=str(e),
                message="Eventbrite 웹훅 처리 실패",
            )

    async def _save_activity(
        self,
        seminar: SeminarInfo,
        play_id: str,
    ) -> WebhookProcessResult:
        """
        Activity 저장 (중복 체크 포함)

        Args:
            seminar: 세미나 정보
            play_id: Play ID

        Returns:
            WebhookProcessResult: 저장 결과
        """
        # 중복 체크
        existing = await activity_repo.check_duplicate(
            self.db,
            url=seminar.url,
            title=seminar.title,
            date=seminar.date,
            external_id=seminar.external_id,
        )

        if existing:
            self.logger.info(
                "Duplicate activity found",
                existing_id=existing.entity_id,
                url=seminar.url,
            )
            return WebhookProcessResult(
                success=True,
                activity_id=existing.entity_id,
                is_duplicate=True,
                message=f"중복 Activity (기존 ID: {existing.entity_id})",
            )

        # Activity 생성
        activity_data = seminar.to_activity_data()
        activity_data["play_id"] = play_id
        activity_data["created_by"] = "webhook"

        entity = await activity_repo.create_activity(self.db, activity_data)
        await self.db.commit()

        self.logger.info(
            "Activity created from webhook",
            activity_id=entity.entity_id,
            title=entity.name[:50],
        )

        return WebhookProcessResult(
            success=True,
            activity_id=entity.entity_id,
            is_duplicate=False,
            message="Activity 생성 완료",
        )

    def _parse_date(self, date_str: str | None) -> str | None:
        """날짜 문자열 파싱 (YYYY-MM-DD 형식으로 변환)"""
        if not date_str:
            return None

        # 다양한 형식 처리
        from email.utils import parsedate_to_datetime

        try:
            # RFC 2822 형식
            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass

        try:
            # ISO 8601 형식
            date_str_normalized = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(date_str_normalized)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # YYYY-MM-DD 형식이면 그대로
        import re

        match = re.match(r"^\d{4}-\d{2}-\d{2}", date_str)
        if match:
            return match.group(0)

        return None


# ============================================================
# 웹훅 검증 유틸리티
# ============================================================


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """
    웹훅 서명 검증

    Args:
        payload: 요청 본문
        signature: 서명 헤더 값
        secret: 비밀 키
        algorithm: 해시 알고리즘

    Returns:
        bool: 검증 성공 여부
    """
    if algorithm == "sha256":
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
    elif algorithm == "sha1":
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha1,
        ).hexdigest()
    else:
        return False

    # sha256=xxx 형식 처리
    if "=" in signature:
        signature = signature.split("=", 1)[1]

    return hmac.compare_digest(expected, signature)
