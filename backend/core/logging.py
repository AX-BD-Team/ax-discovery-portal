"""
AX Discovery Portal - 로깅 설정

structlog 기반 구조화 로깅 + Sentry 에러 모니터링
"""

import logging
import sys
from typing import Any

import structlog

from .config import settings

# Windows cp949 호환을 위한 이모지 대체 맵
EMOJI_REPLACEMENTS: dict[str, str] = {
    "✅": "[OK]",
    "❌": "[FAIL]",
    "⚠️": "[WARN]",
    "⚠": "[WARN]",
    "🔍": "[SEARCH]",
    "📊": "[DATA]",
    "📝": "[NOTE]",
    "🚀": "[START]",
    "💡": "[TIP]",
    "🔧": "[FIX]",
    "📋": "[LIST]",
    "🎯": "[TARGET]",
    "📅": "[DATE]",
    "🏢": "[ORG]",
    "💰": "[MONEY]",
    "📍": "[LOC]",
    "🔗": "[LINK]",
    "⏰": "[TIME]",
    "🎉": "[DONE]",
    "❓": "[?]",
    "🤖": "[AI]",
}


def _ensure_utf8_stdout() -> None:
    """Windows에서 stdout을 UTF-8로 설정"""
    if sys.platform != "win32":
        return

    # stdout이 reconfigure 메서드를 가지고 있으면 UTF-8로 재설정
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # reconfigure 실패 시 무시 (이미 UTF-8이거나 터미널 제한)
            pass


def _sanitize_emoji_for_console(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Windows cp949 호환을 위한 이모지 대체 프로세서"""

    def replace_emojis(value: Any) -> Any:
        """문자열 값에서 이모지를 대체"""
        if not isinstance(value, str):
            return value
        result = value
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            result = result.replace(emoji, replacement)
        return result

    # 모든 문자열 값에서 이모지 대체
    for key, value in event_dict.items():
        event_dict[key] = replace_emojis(value)

    return event_dict


def setup_logging() -> None:
    """
    애플리케이션 로깅 설정 초기화

    환경별 설정:
    - development: 콘솔 출력, 컬러 포맷, DEBUG 레벨
    - staging/production: JSON 포맷, INFO/WARNING 레벨
    """
    # Windows UTF-8 stdout 설정
    _ensure_utf8_stdout()

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
        # 개발 환경: 컬러 콘솔 출력 + Windows 이모지 대체
        processors = shared_processors + [
            _sanitize_emoji_for_console,  # Windows cp949 호환
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
