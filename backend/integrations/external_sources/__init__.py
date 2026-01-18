"""
외부 세미나 소스 수집기 패키지

다양한 플랫폼에서 AI/AX 관련 세미나/이벤트 정보 수집

지원 소스:
- RSS: RSS 피드 구독
- OnOffMix: 온오프믹스 (onoffmix.com)
- EventUs: 이벤터스 (event-us.kr)
- DevEvent: GitHub brave-people/Dev-Event
- Eventbrite: Eventbrite (eventbrite.com)
- Festa: ⚠️ DEPRECATED (2025.01.31 서비스 종료)
"""

from .base import BaseSeminarCollector, SeminarInfo
from .devevent_collector import DevEventCollector
from .eventbrite_collector import EventbriteCollector
from .eventus_collector import EventUsCollector
from .festa_collector import FestaCollector  # DEPRECATED
from .health_check import (
    CollectorHealthChecker,
    HealthCheckResult,
    HealthStatus,
    run_health_check,
)
from .keywords import (
    AI_AX_KEYWORDS,
    CATEGORY_KEYWORDS,
    EXCLUDE_KEYWORDS,
    filter_by_ai_keywords,
    filter_excludes,
    get_search_keywords,
)
from .onoffmix_collector import OnOffMixCollector
from .rss_collector import RSSCollector

__all__ = [
    # 기본 클래스
    "BaseSeminarCollector",
    "SeminarInfo",
    # 수집기
    "RSSCollector",
    "OnOffMixCollector",
    "EventUsCollector",
    "DevEventCollector",
    "EventbriteCollector",
    "FestaCollector",  # DEPRECATED
    # 헬스체크
    "CollectorHealthChecker",
    "HealthCheckResult",
    "HealthStatus",
    "run_health_check",
    # 키워드 유틸리티
    "AI_AX_KEYWORDS",
    "CATEGORY_KEYWORDS",
    "EXCLUDE_KEYWORDS",
    "filter_by_ai_keywords",
    "filter_excludes",
    "get_search_keywords",
]


# 기본 수집기 목록 (추천 순서)
DEFAULT_COLLECTORS = [
    "rss",
    "onoffmix",
    "eventus",
    "devevent",
    "eventbrite",
]

# DEPRECATED 수집기
DEPRECATED_COLLECTORS = [
    "festa",  # 2025.01.31 서비스 종료
]
