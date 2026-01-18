"""
외부 세미나 수집기 헬스체크

OnOffMix, EventUs 등 웹 스크래핑 기반 수집기의 상태를 모니터링합니다.
HTML 구조 변경 시 조기 감지를 위한 진단 도구입니다.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

import structlog

from .devevent_collector import DevEventCollector
from .eventus_collector import EventUsCollector
from .onoffmix_collector import OnOffMixCollector
from .rss_collector import RSSCollector

logger = structlog.get_logger()


class HealthStatus(str, Enum):
    """수집기 상태"""

    HEALTHY = "healthy"  # 정상: 1건 이상 수집
    DEGRADED = "degraded"  # 저하: 0건 수집 (HTML 구조 변경 가능성)
    UNHEALTHY = "unhealthy"  # 비정상: 예외 발생


@dataclass
class HealthCheckResult:
    """헬스체크 결과"""

    collector_name: str
    status: HealthStatus
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    sample_count: int = 0
    error_message: str | None = None
    response_time_ms: float | None = None

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "collector_name": self.collector_name,
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "sample_count": self.sample_count,
            "error_message": self.error_message,
            "response_time_ms": self.response_time_ms,
        }


class CollectorHealthChecker:
    """
    수집기 헬스체크 클래스

    OnOffMix, EventUs 등 웹 스크래핑 기반 수집기의 상태를 확인합니다.
    """

    def __init__(self):
        self.onoffmix = OnOffMixCollector()
        self.eventus = EventUsCollector()
        self.devevent = DevEventCollector()
        self.rss = RSSCollector()

    async def check_onoffmix(self) -> HealthCheckResult:
        """
        OnOffMix 수집기 상태 확인

        Returns:
            HealthCheckResult: 헬스체크 결과
        """
        start_time = datetime.now(UTC)

        try:
            # 소량 테스트 수집 (AI 키워드로 최대 5개)
            seminars = await self.onoffmix.fetch_seminars(
                keywords=["AI"],
                categories=["it"],
                limit=5,
            )

            elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if len(seminars) > 0:
                logger.info(
                    "OnOffMix 헬스체크 정상",
                    sample_count=len(seminars),
                    response_time_ms=round(elapsed_ms, 2),
                )
                return HealthCheckResult(
                    collector_name="onoffmix",
                    status=HealthStatus.HEALTHY,
                    sample_count=len(seminars),
                    response_time_ms=round(elapsed_ms, 2),
                )
            else:
                logger.warning(
                    "OnOffMix 수집 결과 없음 (HTML 구조 변경 가능성)",
                    response_time_ms=round(elapsed_ms, 2),
                )
                return HealthCheckResult(
                    collector_name="onoffmix",
                    status=HealthStatus.DEGRADED,
                    sample_count=0,
                    error_message="수집 결과 없음 - HTML 구조 변경 가능성",
                    response_time_ms=round(elapsed_ms, 2),
                )

        except Exception as e:
            elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            logger.error(
                "OnOffMix 헬스체크 실패",
                error=str(e),
                response_time_ms=round(elapsed_ms, 2),
            )
            return HealthCheckResult(
                collector_name="onoffmix",
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                response_time_ms=round(elapsed_ms, 2),
            )

    async def check_eventus(self) -> HealthCheckResult:
        """
        EventUs 수집기 상태 확인

        Returns:
            HealthCheckResult: 헬스체크 결과
        """
        start_time = datetime.now(UTC)

        try:
            # 소량 테스트 수집
            seminars = await self.eventus.fetch_seminars(
                keywords=["AI"],
                categories=["it"],
                limit=5,
            )

            elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if len(seminars) > 0:
                logger.info(
                    "EventUs 헬스체크 정상",
                    sample_count=len(seminars),
                    response_time_ms=round(elapsed_ms, 2),
                )
                return HealthCheckResult(
                    collector_name="eventus",
                    status=HealthStatus.HEALTHY,
                    sample_count=len(seminars),
                    response_time_ms=round(elapsed_ms, 2),
                )
            else:
                logger.warning(
                    "EventUs 수집 결과 없음 (HTML 구조 변경 가능성)",
                    response_time_ms=round(elapsed_ms, 2),
                )
                return HealthCheckResult(
                    collector_name="eventus",
                    status=HealthStatus.DEGRADED,
                    sample_count=0,
                    error_message="수집 결과 없음 - HTML 구조 변경 가능성",
                    response_time_ms=round(elapsed_ms, 2),
                )

        except Exception as e:
            elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            logger.error(
                "EventUs 헬스체크 실패",
                error=str(e),
                response_time_ms=round(elapsed_ms, 2),
            )
            return HealthCheckResult(
                collector_name="eventus",
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                response_time_ms=round(elapsed_ms, 2),
            )

    async def check_devevent(self) -> HealthCheckResult:
        """
        DevEvent (GitHub) 수집기 상태 확인

        Returns:
            HealthCheckResult: 헬스체크 결과
        """
        start_time = datetime.now(UTC)

        try:
            # 소량 테스트 수집
            seminars = await self.devevent.fetch_seminars(
                keywords=["AI"],
                limit=5,
            )

            elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if len(seminars) > 0:
                logger.info(
                    "DevEvent 헬스체크 정상",
                    sample_count=len(seminars),
                    response_time_ms=round(elapsed_ms, 2),
                )
                return HealthCheckResult(
                    collector_name="devevent",
                    status=HealthStatus.HEALTHY,
                    sample_count=len(seminars),
                    response_time_ms=round(elapsed_ms, 2),
                )
            else:
                logger.warning(
                    "DevEvent 수집 결과 없음",
                    response_time_ms=round(elapsed_ms, 2),
                )
                return HealthCheckResult(
                    collector_name="devevent",
                    status=HealthStatus.DEGRADED,
                    sample_count=0,
                    error_message="수집 결과 없음 - GitHub 저장소 확인 필요",
                    response_time_ms=round(elapsed_ms, 2),
                )

        except Exception as e:
            elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            logger.error(
                "DevEvent 헬스체크 실패",
                error=str(e),
                response_time_ms=round(elapsed_ms, 2),
            )
            return HealthCheckResult(
                collector_name="devevent",
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                response_time_ms=round(elapsed_ms, 2),
            )

    async def check_rss(self) -> HealthCheckResult:
        """
        RSS 수집기 상태 확인

        Returns:
            HealthCheckResult: 헬스체크 결과
        """
        start_time = datetime.now(UTC)

        try:
            # 소량 테스트 수집 (AI 관련 키워드)
            seminars = await self.rss.fetch_seminars(
                keywords=["AI", "GPT", "LLM"],
                limit=5,
            )

            elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if len(seminars) > 0:
                logger.info(
                    "RSS 헬스체크 정상",
                    sample_count=len(seminars),
                    feed_count=len(self.rss.feed_urls),
                    response_time_ms=round(elapsed_ms, 2),
                )
                return HealthCheckResult(
                    collector_name="rss",
                    status=HealthStatus.HEALTHY,
                    sample_count=len(seminars),
                    response_time_ms=round(elapsed_ms, 2),
                )
            else:
                logger.warning(
                    "RSS 수집 결과 없음",
                    response_time_ms=round(elapsed_ms, 2),
                )
                return HealthCheckResult(
                    collector_name="rss",
                    status=HealthStatus.DEGRADED,
                    sample_count=0,
                    error_message="수집 결과 없음 - 피드 URL 확인 필요",
                    response_time_ms=round(elapsed_ms, 2),
                )

        except Exception as e:
            elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            logger.error(
                "RSS 헬스체크 실패",
                error=str(e),
                response_time_ms=round(elapsed_ms, 2),
            )
            return HealthCheckResult(
                collector_name="rss",
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                response_time_ms=round(elapsed_ms, 2),
            )

    async def check_all(self) -> list[HealthCheckResult]:
        """
        전체 수집기 헬스체크

        Returns:
            list[HealthCheckResult]: 모든 수집기의 헬스체크 결과
        """
        results = []

        # OnOffMix 체크
        onoffmix_result = await self.check_onoffmix()
        results.append(onoffmix_result)

        # EventUs 체크
        eventus_result = await self.check_eventus()
        results.append(eventus_result)

        # DevEvent 체크
        devevent_result = await self.check_devevent()
        results.append(devevent_result)

        # RSS 체크
        rss_result = await self.check_rss()
        results.append(rss_result)

        # 전체 상태 요약 로그
        healthy_count = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        logger.info(
            "수집기 헬스체크 완료",
            total=len(results),
            healthy=healthy_count,
            degraded=sum(1 for r in results if r.status == HealthStatus.DEGRADED),
            unhealthy=sum(1 for r in results if r.status == HealthStatus.UNHEALTHY),
        )

        return results


async def run_health_check() -> dict:
    """
    헬스체크 실행 헬퍼 함수

    Returns:
        dict: 헬스체크 결과 요약
    """
    checker = CollectorHealthChecker()
    results = await checker.check_all()

    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "results": [r.to_dict() for r in results],
        "summary": {
            "total": len(results),
            "healthy": sum(1 for r in results if r.status == HealthStatus.HEALTHY),
            "degraded": sum(1 for r in results if r.status == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for r in results if r.status == HealthStatus.UNHEALTHY),
        },
    }
