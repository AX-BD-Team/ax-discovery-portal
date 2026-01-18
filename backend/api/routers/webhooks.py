"""
Webhooks Router

외부 소스(RSS, Festa, Eventbrite)에서 실시간 이벤트 수신
"""

import os

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.services.webhook_processor import (
    EventbriteWebhookPayload,
    FestaWebhookPayload,
    RSSWebhookPayload,
    WebhookProcessor,
    verify_webhook_signature,
)

logger = structlog.get_logger()

router = APIRouter()


# ============================================================
# Response Models
# ============================================================


class WebhookResponse(BaseModel):
    """웹훅 응답"""

    success: bool
    activity_id: str | None = None
    is_duplicate: bool = False
    message: str = ""


# ============================================================
# RSS Webhook
# ============================================================


@router.post("/seminar/rss", response_model=WebhookResponse)
async def receive_rss_webhook(
    payload: RSSWebhookPayload,
    db: AsyncSession = Depends(get_db),
    x_webhook_secret: str | None = Header(None, alias="X-Webhook-Secret"),
):
    """
    RSS 피드 업데이트 웹훅 수신

    IFTTT, Zapier 등에서 RSS 피드 업데이트 시 호출

    Example IFTTT Applet:
    - Trigger: New feed item in RSS
    - Action: Make web request to this endpoint

    Args:
        payload: RSS 웹훅 페이로드
        x_webhook_secret: 웹훅 비밀 키 (선택)

    Returns:
        WebhookResponse: 처리 결과
    """
    logger.info(
        "RSS webhook received",
        url=payload.url,
        source=payload.source,
    )

    # 선택적 비밀 키 검증
    expected_secret = os.getenv("WEBHOOK_RSS_SECRET")
    if expected_secret and x_webhook_secret != expected_secret:
        logger.warning("Invalid RSS webhook secret")
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Play ID (환경변수 또는 기본값)
    play_id = os.getenv("SEMINAR_DEFAULT_PLAY_ID", "EXT_Desk_D01_Seminar")

    # 웹훅 처리
    processor = WebhookProcessor(db)
    result = await processor.process_rss_webhook(payload, play_id)

    return WebhookResponse(
        success=result.success,
        activity_id=result.activity_id,
        is_duplicate=result.is_duplicate,
        message=result.message,
    )


# ============================================================
# Festa Webhook
# ============================================================


@router.post("/seminar/festa", response_model=WebhookResponse)
async def receive_festa_webhook(
    payload: FestaWebhookPayload,
    db: AsyncSession = Depends(get_db),
    x_festa_signature: str | None = Header(None, alias="X-Festa-Signature"),
):
    """
    Festa 이벤트 웹훅 수신

    Festa에서 이벤트 생성/수정/삭제 시 호출
    (Festa 웹훅 기능 활성화 필요)

    Args:
        payload: Festa 웹훅 페이로드
        x_festa_signature: Festa 웹훅 서명

    Returns:
        WebhookResponse: 처리 결과
    """
    logger.info(
        "Festa webhook received",
        event_id=payload.event_id,
        event_type=payload.event_type,
    )

    # Play ID
    play_id = os.getenv("SEMINAR_DEFAULT_PLAY_ID", "EXT_Desk_D01_Seminar")

    # 웹훅 처리
    processor = WebhookProcessor(db)
    result = await processor.process_festa_webhook(payload, play_id)

    return WebhookResponse(
        success=result.success,
        activity_id=result.activity_id,
        is_duplicate=result.is_duplicate,
        message=result.message,
    )


# ============================================================
# Eventbrite Webhook
# ============================================================


@router.post("/seminar/eventbrite", response_model=WebhookResponse)
async def receive_eventbrite_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Eventbrite 이벤트 웹훅 수신

    Eventbrite Webhook 설정에서 등록된 엔드포인트로 호출됨

    Eventbrite 웹훅 형식:
    - api_url: 이벤트 상세 정보 API URL
    - config: 웹훅 설정 정보

    Args:
        request: FastAPI Request (raw body 접근용)

    Returns:
        WebhookResponse: 처리 결과
    """
    # Raw body 읽기 (서명 검증용)
    body = await request.body()

    # 서명 검증 (Eventbrite webhook)
    webhook_secret = os.getenv("EVENTBRITE_WEBHOOK_SECRET")
    if webhook_secret:
        signature = request.headers.get("X-Eventbrite-Signature", "")
        if not verify_webhook_signature(body, signature, webhook_secret):
            logger.warning("Invalid Eventbrite webhook signature")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # JSON 파싱
    try:
        payload_dict = await request.json()
    except Exception:
        payload_dict = {}
        # body에서 다시 파싱 시도
        import json

        try:
            payload_dict = json.loads(body)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from e

    logger.info(
        "Eventbrite webhook received",
        api_url=payload_dict.get("api_url"),
    )

    # 페이로드 생성
    payload = EventbriteWebhookPayload(
        api_url=payload_dict.get("api_url", ""),
        event_id=payload_dict.get("event_id"),
        title=payload_dict.get("title"),
        url=payload_dict.get("url"),
        date=payload_dict.get("date"),
        organizer=payload_dict.get("organizer"),
        description=payload_dict.get("description"),
        location=payload_dict.get("location"),
        is_online=payload_dict.get("is_online", False),
        config=payload_dict.get("config", {}),
    )

    # Play ID
    play_id = os.getenv("SEMINAR_DEFAULT_PLAY_ID", "EXT_Desk_D01_Seminar")

    # 웹훅 처리
    processor = WebhookProcessor(db)
    result = await processor.process_eventbrite_webhook(payload, play_id)

    return WebhookResponse(
        success=result.success,
        activity_id=result.activity_id,
        is_duplicate=result.is_duplicate,
        message=result.message,
    )


# ============================================================
# Generic Webhook (Custom Integration)
# ============================================================


class GenericSeminarPayload(BaseModel):
    """범용 세미나 웹훅 페이로드"""

    title: str
    url: str
    date: str | None = None
    organizer: str | None = None
    description: str | None = None
    location: str | None = None
    categories: list[str] | None = None
    source_type: str = "custom"  # 소스 식별자
    external_id: str | None = None
    play_id: str | None = None


@router.post("/seminar/custom", response_model=WebhookResponse)
async def receive_custom_webhook(
    payload: GenericSeminarPayload,
    db: AsyncSession = Depends(get_db),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
):
    """
    범용 세미나 웹훅 수신

    커스텀 통합을 위한 범용 엔드포인트

    Args:
        payload: 범용 세미나 페이로드
        x_api_key: API 키 (인증)

    Returns:
        WebhookResponse: 처리 결과
    """
    # API 키 검증
    expected_key = os.getenv("WEBHOOK_API_KEY")
    if expected_key and x_api_key != expected_key:
        logger.warning("Invalid custom webhook API key")
        raise HTTPException(status_code=401, detail="Invalid API key")

    logger.info(
        "Custom webhook received",
        url=payload.url,
        source_type=payload.source_type,
    )

    # RSS 페이로드로 변환하여 처리
    rss_payload = RSSWebhookPayload(
        title=payload.title,
        url=payload.url,
        published=payload.date,
        description=payload.description,
        author=payload.organizer,
        guid=payload.external_id,
        source=payload.source_type,
    )

    # Play ID
    play_id = (
        payload.play_id
        or os.getenv("SEMINAR_DEFAULT_PLAY_ID", "EXT_Desk_D01_Seminar")
        or "EXT_Desk_D01_Seminar"
    )

    # 웹훅 처리
    processor = WebhookProcessor(db)
    result = await processor.process_rss_webhook(rss_payload, play_id)

    return WebhookResponse(
        success=result.success,
        activity_id=result.activity_id,
        is_duplicate=result.is_duplicate,
        message=result.message,
    )


# ============================================================
# Webhook Health Check
# ============================================================


@router.get("/health")
async def webhook_health():
    """웹훅 엔드포인트 헬스체크"""
    return {
        "status": "ok",
        "endpoints": [
            "/webhooks/seminar/rss",
            "/webhooks/seminar/festa",
            "/webhooks/seminar/eventbrite",
            "/webhooks/seminar/custom",
        ],
    }
