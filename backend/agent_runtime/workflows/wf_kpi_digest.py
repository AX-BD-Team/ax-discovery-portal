"""
WF-05: KPI Digest

주간 KPI 리포트 생성 + 지연 Play/Action 경고
"""

from typing import Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


@dataclass
class KPIInput:
    """KPI Digest 입력"""
    period: str = "week"  # week, month
    play_ids: list[str] | None = None  # None이면 전체
    notify: bool = False  # Teams/Slack 알림 여부


@dataclass
class KPITarget:
    """PoC 목표 기준"""
    activity_weekly: int = 20
    signal_weekly: int = 30
    brief_weekly: int = 6
    s2_weekly_min: int = 2
    s2_weekly_max: int = 4
    signal_to_brief_days: int = 7
    brief_to_s2_days: int = 14


@dataclass
class KPIDigestOutput:
    """KPI Digest 출력"""
    period: str
    period_start: str
    period_end: str
    metrics: dict[str, Any]
    lead_times: dict[str, Any]
    alerts: list[dict[str, Any]]
    top_plays: list[dict[str, Any]]
    recommendations: list[str]
    confluence_url: str | None = None


class KPIDigestPipeline:
    """
    WF-05: KPI Digest
    
    트리거: /ax:kpi-digest, 주간 배치 (금요일 EOD)
    """
    
    def __init__(self):
        self.logger = logger.bind(workflow="WF-05")
        self.targets = KPITarget()
    
    async def run(self, input_data: KPIInput) -> KPIDigestOutput:
        """파이프라인 실행"""
        self.logger.info("Starting KPI Digest", period=input_data.period)
        
        # 기간 계산
        period_start, period_end = self._calculate_period(input_data.period)
        
        # 1. 메트릭 집계
        metrics = await self._aggregate_metrics(
            period_start, period_end, input_data.play_ids
        )
        
        # 2. 리드타임 계산
        lead_times = await self._calculate_lead_times(period_start, period_end)
        
        # 3. 경고 생성
        alerts = await self._generate_alerts(metrics, lead_times)
        
        # 4. Top Plays 선정
        top_plays = await self._get_top_plays(period_start, period_end)
        
        # 5. 추천 사항 생성
        recommendations = self._generate_recommendations(metrics, alerts)
        
        # 6. (선택) Confluence에 리포트 생성
        confluence_url = None
        if input_data.notify:
            confluence_url = await self._publish_report(
                metrics, lead_times, alerts, top_plays
            )
            await self._send_notifications(confluence_url)
        
        self.logger.info("KPI Digest completed", alerts=len(alerts))
        
        return KPIDigestOutput(
            period=input_data.period,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            metrics=metrics,
            lead_times=lead_times,
            alerts=alerts,
            top_plays=top_plays,
            recommendations=recommendations,
            confluence_url=confluence_url
        )
    
    def _calculate_period(self, period: str) -> tuple[datetime, datetime]:
        """기간 계산"""
        now = datetime.utcnow()
        
        if period == "week":
            # 이번 주 월요일 ~ 일요일
            start = now - timedelta(days=now.weekday())
            end = start + timedelta(days=6)
        else:  # month
            # 이번 달 1일 ~ 말일
            start = now.replace(day=1)
            next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month - timedelta(days=1)
        
        return start.replace(hour=0, minute=0, second=0), end.replace(hour=23, minute=59, second=59)
    
    async def _aggregate_metrics(
        self,
        start: datetime,
        end: datetime,
        play_ids: list[str] | None
    ) -> dict[str, Any]:
        """메트릭 집계"""
        # TODO: DB에서 실제 데이터 조회
        
        return {
            "activity": {
                "actual": 25,
                "target": self.targets.activity_weekly,
                "achievement": 125.0
            },
            "signal": {
                "actual": 35,
                "target": self.targets.signal_weekly,
                "achievement": 116.7
            },
            "brief": {
                "actual": 8,
                "target": self.targets.brief_weekly,
                "achievement": 133.3
            },
            "s2": {
                "actual": 3,
                "target_min": self.targets.s2_weekly_min,
                "target_max": self.targets.s2_weekly_max,
                "achievement": 100.0
            },
            "by_source": {
                "KT": {"signal": 15, "brief": 4},
                "그룹사": {"signal": 12, "brief": 2},
                "대외": {"signal": 8, "brief": 2}
            }
        }
    
    async def _calculate_lead_times(
        self,
        start: datetime,
        end: datetime
    ) -> dict[str, Any]:
        """리드타임 계산"""
        # TODO: 실제 데이터 기반 계산
        
        return {
            "signal_to_brief": {
                "avg_days": 5.2,
                "target_days": self.targets.signal_to_brief_days,
                "on_target": True
            },
            "brief_to_s2": {
                "avg_days": 11.0,
                "target_days": self.targets.brief_to_s2_days,
                "on_target": True
            }
        }
    
    async def _generate_alerts(
        self,
        metrics: dict[str, Any],
        lead_times: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """경고 생성"""
        alerts = []
        
        # 목표 미달 경고
        for key in ["activity", "signal", "brief"]:
            if metrics[key]["achievement"] < 80:
                alerts.append({
                    "type": "UNDER_TARGET",
                    "severity": "YELLOW" if metrics[key]["achievement"] >= 50 else "RED",
                    "metric": key,
                    "message": f"{key} 목표 대비 {metrics[key]['achievement']:.1f}% 달성"
                })
        
        # 리드타임 초과 경고
        for key, data in lead_times.items():
            if not data["on_target"]:
                alerts.append({
                    "type": "LEAD_TIME_EXCEEDED",
                    "severity": "YELLOW",
                    "metric": key,
                    "message": f"{key} 평균 {data['avg_days']}일 (목표: {data['target_days']}일)"
                })
        
        return alerts
    
    async def _get_top_plays(
        self,
        start: datetime,
        end: datetime
    ) -> list[dict[str, Any]]:
        """Top Plays 선정"""
        # TODO: 실제 데이터 기반 선정
        
        return [
            {
                "rank": 1,
                "play_id": "EXT_Desk_D01_Seminar",
                "brief_count": 3,
                "s2_count": 1
            },
            {
                "rank": 2,
                "play_id": "KT_Sales_S01_Interview",
                "brief_count": 2,
                "s2_count": 0
            }
        ]
    
    def _generate_recommendations(
        self,
        metrics: dict[str, Any],
        alerts: list[dict[str, Any]]
    ) -> list[str]:
        """추천 사항 생성"""
        recommendations = []
        
        # 경고 기반 추천
        for alert in alerts:
            if alert["type"] == "UNDER_TARGET":
                recommendations.append(
                    f"{alert['metric']} 목표 달성을 위한 추가 활동 필요"
                )
        
        if not recommendations:
            recommendations.append("현재 페이스 유지 - 목표 달성 중")
        
        return recommendations
    
    async def _publish_report(
        self,
        metrics: dict[str, Any],
        lead_times: dict[str, Any],
        alerts: list[dict[str, Any]],
        top_plays: list[dict[str, Any]]
    ) -> str:
        """Confluence에 리포트 게시"""
        # TODO: Confluence 연동
        return ""
    
    async def _send_notifications(self, confluence_url: str) -> None:
        """Teams/Slack 알림 전송"""
        # TODO: 알림 연동
        pass


workflow = KPIDigestPipeline()


async def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """워크플로 진입점"""
    kpi_input = KPIInput(
        period=input_data.get("period", "week"),
        play_ids=input_data.get("play_ids"),
        notify=input_data.get("notify", False)
    )
    
    result = await workflow.run(kpi_input)
    
    return {
        "period": result.period,
        "period_start": result.period_start,
        "period_end": result.period_end,
        "metrics": result.metrics,
        "lead_times": result.lead_times,
        "alerts": result.alerts,
        "top_plays": result.top_plays,
        "recommendations": result.recommendations,
        "confluence_url": result.confluence_url
    }
