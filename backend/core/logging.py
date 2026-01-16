"""
AX Discovery Portal - 로깅 설정

structlog 기반 구조화 로깅 + Sentry 에러 모니터링
"""

import logging
import sys
from typing import Any

import structlog

from .config import settings


def setup_logging() -> None:
    """
    애플리케이션 로깅 설정 초기화

    환경별 설정:
    - development: 콘솔 출력, 컬러 포맷, DEBUG 레벨
    - staging/production: JSON 포맷, INFO/WARNING 레벨
    """
    # 로그 레벨 설정
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # 공통 프로세서
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_development:
        # 개발 환경: 컬러 콘솔 출력
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # 프로덕션 환경: JSON 포맷
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    # structlog 설정
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 표준 라이브러리 로깅 설정
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def setup_sentry() -> None:
    """
    Sentry 에러 모니터링 설정

    환경변수 SENTRY_DSN이 설정된 경우에만 활성화됩니다.
    """
    sentry_dsn = settings.sentry_dsn
    if not sentry_dsn:
        structlog.get_logger().info("Sentry DSN not configured, skipping Sentry setup")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        # Sentry 로깅 통합 설정
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.app_env,
            release=f"ax-discovery-portal@{settings.app_version}",
            traces_sample_rate=0.1 if settings.is_production else 1.0,
            profiles_sample_rate=0.1 if settings.is_production else 1.0,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                sentry_logging,
            ],
            send_default_pii=False,
            before_send=_filter_sensitive_data,
        )

        structlog.get_logger().info(
            "Sentry initialized",
            environment=settings.app_env,
            dsn_configured=True,
        )

    except ImportError:
        structlog.get_logger().warning(
            "sentry-sdk not installed, skipping Sentry setup. "
            "Install with: pip install sentry-sdk[fastapi]"
        )
    except Exception as e:
        structlog.get_logger().error("Failed to initialize Sentry", error=str(e))


def _filter_sensitive_data(event: dict, hint: dict) -> dict | None:
    """Sentry로 전송하기 전 민감한 데이터 필터링"""
    if "request" in event:
        headers = event["request"].get("headers", {})
        for header in ["authorization", "cookie", "x-api-key"]:
            if header in headers:
                headers[header] = "[FILTERED]"

    if "exception" in event:
        for exception in event.get("exception", {}).get("values", []):
            if "value" in exception:
                value = exception["value"]
                if "eyJ" in value:
                    exception["value"] = "[JWT TOKEN FILTERED]"
                if "sk-" in value or "sk_" in value:
                    exception["value"] = "[API KEY FILTERED]"

    return event


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """구조화된 로거 인스턴스 반환"""
    return structlog.get_logger(name)


def init_logging() -> None:
    """전체 로깅 시스템 초기화"""
    setup_logging()
    setup_sentry()
