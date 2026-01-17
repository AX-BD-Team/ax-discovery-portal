"""
WF-05: KPI Digest

주간/월간 KPI 리포트 생성 + 지연 Play/Action 경고

트리거:
- /ax:kpi-digest 커맨드
- 주간 배치 (금요일 EOD)

흐름:
1. 기간 계산 (주간/월간)
2. 메트릭 집계 (Activity, Signal, Brief, S2, S3)
3. 리드타임 계산 (Signal→Brief, Brief→S2)
4. 경고 생성 (목표 미달, 리드타임 초과, 지연 Play)
5. Top Plays 선정
6. 추천 사항 생성
7. (선택) Confluence 리포트 발행 + 알림

PoC 목표:
- Activity 20+/주
- Signal 30+/주
- Brief 6+/주
- S2 2~4/주
- Signal→Brief ≤7일
- Brief→S2 ≤14일
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


# ============================================================
# Enums & Constants
# ============================================================


class AlertSeverity(str, Enum):
    """경고 심각도"""

    INFO = "INFO"
    YELLOW = "YELLOW"
    RED = "RED"


class AlertType(str, Enum):
    """경고 유형"""

    UNDER_TARGET = "UNDER_TARGET"
    LEAD_TIME_EXCEEDED = "LEAD_TIME_EXCEEDED"
    PLAY_DELAYED = "PLAY_DELAYED"
    PLAY_STALE = "PLAY_STALE"
    OVERDUE = "OVERDUE"


# PoC 목표 기준
POC_TARGETS = {
    "activity_weekly": 20,
    "signal_weekly": 30,
    "brief_weekly": 6,
    "s2_weekly_min": 2,
    "s2_weekly_max": 4,
    "signal_to_brief_days": 7,
    "brief_to_s2_days": 14,
}


# ============================================================
# Data Classes
# ============================================================


@dataclass
class KPIInput:
    """KPI Digest 입력"""

    period: str = "week"  # week, month
    play_ids: list[str] | None = None  # None이면 전체
    notify: bool = False  # Teams/Slack 알림 여부
    include_recommendations: bool = True


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
class MetricValue:
    """개별 메트릭 값"""

    actual: int
    target: int
    achievement: float  # 퍼센트
    trend: str = "stable"  # up, down, stable


@dataclass
class LeadTimeMetric:
    """리드타임 메트릭"""

    avg_days: float
    target_days: int
    on_target: bool
    min_days: float = 0.0
    max_days: float = 0.0
    sample_count: int = 0


@dataclass
class Alert:
    """경고 항목"""

    type: str
    severity: str
    metric: str
    message: str
    play_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TopPlay:
    """Top Play 항목"""

    rank: int
    play_id: str
    play_name: str
    signal_count: int
    brief_count: int
    s2_count: int
    owner: str | None = None


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
    status_summary: dict[str, int]
    confluence_url: str | None = None
    generated_at: str = ""


# ============================================================
# 유틸리티 함수
# ============================================================


def calculate_period_range(period: str) -> tuple[datetime, datetime]:
    """기간 범위 계산"""
    now = datetime.now(UTC)

    if period == "week":
        # 이번 주 월요일 00:00 ~ 일요일 23:59
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif period == "month":
        # 이번 달 1일 ~ 말일
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(seconds=1)
    else:
        # 기본 7일
        end = now
        start = now - timedelta(days=7)

    return start, end


def calculate_achievement(actual: int, target: int) -> float:
    """목표 달성률 계산"""
    if target == 0:
        return 100.0 if actual > 0 else 0.0
    return round((actual / target) * 100, 1)


def determine_severity(achievement: float) -> str:
    """달성률에 따른 심각도 결정"""
    if achievement >= 80:
        return AlertSeverity.INFO.value
    elif achievement >= 50:
        return AlertSeverity.YELLOW.value
    else:
        return AlertSeverity.RED.value


# ============================================================
# 메인 파이프라인
# ============================================================


class KPIDigestPipeline:
    """
    WF-05: KPI Digest

    트리거: /ax:kpi-digest, 주간 배치 (금요일 EOD)
    """

    # 단계 정의
    STEPS = [
        {"id": "PERIOD_CALC", "label": "기간 계산"},
        {"id": "METRICS_AGGREGATE", "label": "메트릭 집계"},
        {"id": "LEAD_TIME_CALC", "label": "리드타임 계산"},
        {"id": "ALERTS_GENERATE", "label": "경고 생성"},
        {"id": "TOP_PLAYS", "label": "Top Plays 선정"},
        {"id": "RECOMMENDATIONS", "label": "추천 사항 생성"},
    ]

    def __init__(self):
        self.logger = logger.bind(workflow="WF-05")
        self.targets = KPITarget()

    async def run(self, input_data: KPIInput) -> KPIDigestOutput:
        """파이프라인 실행"""
        self.logger.info("Starting KPI Digest", period=input_data.period)

        # 1. 기간 계산
        period_start, period_end = calculate_period_range(input_data.period)

        # 2. 메트릭 집계
        metrics = await self._aggregate_metrics(period_start, period_end, input_data.play_ids)

        # 3. 리드타임 계산
        lead_times = await self._calculate_lead_times(period_start, period_end)

        # 4. 경고 생성
        alerts = await self._generate_alerts(metrics, lead_times)

        # 5. Top Plays 선정
        top_plays = await self._get_top_plays(period_start, period_end)

        # 6. 추천 사항 생성
        recommendations = []
        if input_data.include_recommendations:
            recommendations = self._generate_recommendations(metrics, alerts)

        # 7. 상태 요약
        status_summary = await self._get_status_summary()

        # 8. (선택) Confluence에 리포트 생성
        confluence_url = None
        if input_data.notify:
            confluence_url = await self._publish_report(
                input_data.period, metrics, lead_times, alerts, top_plays, recommendations
            )
            await self._send_notifications(confluence_url, alerts)

        self.logger.info(
            "KPI Digest completed",
            alerts_count=len(alerts),
            top_plays_count=len(top_plays),
        )

        # alerts/top_plays 타입 변환 (Alert/TopPlay → dict)
        alerts_dict: list[dict[str, Any]] = (
            [self._alert_to_dict(a) for a in alerts]
            if alerts and isinstance(alerts[0], Alert)
            else alerts  # type: ignore[assignment]
        )
        top_plays_dict: list[dict[str, Any]] = (
            [self._top_play_to_dict(p) for p in top_plays]
            if top_plays and isinstance(top_plays[0], TopPlay)
            else top_plays  # type: ignore[assignment]
        )

        return KPIDigestOutput(
            period=input_data.period,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            metrics=metrics,
            lead_times=lead_times,
            alerts=alerts_dict,
            top_plays=top_plays_dict,
            recommendations=recommendations,
            status_summary=status_summary,
            confluence_url=confluence_url,
            generated_at=datetime.now(UTC).isoformat(),
        )

    def _alert_to_dict(self, alert: Alert) -> dict[str, Any]:
        """Alert 객체를 dict로 변환"""
        return {
            "type": alert.type,
            "severity": alert.severity,
            "metric": alert.metric,
            "message": alert.message,
            "play_id": alert.play_id,
            "details": alert.details,
        }

    def _top_play_to_dict(self, play: TopPlay) -> dict[str, Any]:
        """TopPlay 객체를 dict로 변환"""
        return {
            "rank": play.rank,
            "play_id": play.play_id,
            "play_name": play.play_name,
            "signal_count": play.signal_count,
            "brief_count": play.brief_count,
            "s2_count": play.s2_count,
            "owner": play.owner,
        }

    async def _aggregate_metrics(
        self, start: datetime, end: datetime, play_ids: list[str] | None
    ) -> dict[str, Any]:
        """메트릭 집계 (Mock 데이터)"""
        # 실제 구현은 DB에서 조회
        # 주간 기준 mock 데이터

        activity = MetricValue(
            actual=25,
            target=self.targets.activity_weekly,
            achievement=calculate_achievement(25, self.targets.activity_weekly),
        )

        signal = MetricValue(
            actual=35,
            target=self.targets.signal_weekly,
            achievement=calculate_achievement(35, self.targets.signal_weekly),
        )

        brief = MetricValue(
            actual=8,
            target=self.targets.brief_weekly,
            achievement=calculate_achievement(8, self.targets.brief_weekly),
        )

        s2 = MetricValue(
            actual=3,
            target=self.targets.s2_weekly_min,
            achievement=calculate_achievement(3, self.targets.s2_weekly_min),
        )

        return {
            "activity": {
                "actual": activity.actual,
                "target": activity.target,
                "achievement": activity.achievement,
            },
            "signal": {
                "actual": signal.actual,
                "target": signal.target,
                "achievement": signal.achievement,
            },
            "brief": {
                "actual": brief.actual,
                "target": brief.target,
                "achievement": brief.achievement,
            },
            "s2": {
                "actual": s2.actual,
                "target_min": self.targets.s2_weekly_min,
                "target_max": self.targets.s2_weekly_max,
                "achievement": s2.achievement,
            },
            "s3": {
                "actual": 1,
                "target": 1,
                "achievement": 100.0,
            },
            "by_source": {
                "KT": {"activity": 10, "signal": 15, "brief": 4},
                "그룹사": {"activity": 8, "signal": 12, "brief": 2},
                "대외": {"activity": 7, "signal": 8, "brief": 2},
            },
            "by_channel": {
                "데스크리서치": {"signal": 12, "brief": 3},
                "영업PM": {"signal": 10, "brief": 3},
                "인바운드": {"signal": 8, "brief": 1},
                "아웃바운드": {"signal": 5, "brief": 1},
            },
        }

    async def _calculate_lead_times(self, start: datetime, end: datetime) -> dict[str, Any]:
        """리드타임 계산 (Mock 데이터)"""
        # 실제 구현은 Signal/Brief 상태 변경 시점 기준으로 계산

        signal_to_brief = LeadTimeMetric(
            avg_days=5.2,
            target_days=self.targets.signal_to_brief_days,
            on_target=self.targets.signal_to_brief_days >= 5.2,
            min_days=2.0,
            max_days=10.0,
            sample_count=8,
        )

        brief_to_s2 = LeadTimeMetric(
            avg_days=11.0,
            target_days=self.targets.brief_to_s2_days,
            on_target=self.targets.brief_to_s2_days >= 11.0,
            min_days=5.0,
            max_days=18.0,
            sample_count=3,
        )

        return {
            "signal_to_brief": {
                "avg_days": signal_to_brief.avg_days,
                "target_days": signal_to_brief.target_days,
                "on_target": signal_to_brief.on_target,
                "min_days": signal_to_brief.min_days,
                "max_days": signal_to_brief.max_days,
                "sample_count": signal_to_brief.sample_count,
            },
            "brief_to_s2": {
                "avg_days": brief_to_s2.avg_days,
                "target_days": brief_to_s2.target_days,
                "on_target": brief_to_s2.on_target,
                "min_days": brief_to_s2.min_days,
                "max_days": brief_to_s2.max_days,
                "sample_count": brief_to_s2.sample_count,
            },
        }

    async def _generate_alerts(
        self, metrics: dict[str, Any], lead_times: dict[str, Any]
    ) -> list[Alert]:
        """경고 생성"""
        alerts = []

        # 목표 미달 경고
        for key in ["activity", "signal", "brief"]:
            achievement = metrics[key]["achievement"]
            if achievement < 80:
                severity = determine_severity(achievement)
                alerts.append(
                    Alert(
                        type=AlertType.UNDER_TARGET.value,
                        severity=severity,
                        metric=key,
                        message=f"{key.capitalize()} 목표 대비 {achievement:.1f}% 달성",
                        details={
                            "actual": metrics[key]["actual"],
                            "target": metrics[key]["target"],
                        },
                    )
                )

        # S2 목표 확인
        s2_actual = metrics["s2"]["actual"]
        s2_min = metrics["s2"]["target_min"]
        if s2_actual < s2_min:
            alerts.append(
                Alert(
                    type=AlertType.UNDER_TARGET.value,
                    severity=AlertSeverity.YELLOW.value,
                    metric="s2",
                    message=f"S2 {s2_actual}건 (목표: {s2_min}~{metrics['s2']['target_max']}건)",
                    details={
                        "actual": s2_actual,
                        "target_min": s2_min,
                        "target_max": metrics["s2"]["target_max"],
                    },
                )
            )

        # 리드타임 초과 경고
        for key, data in lead_times.items():
            if not data["on_target"]:
                alerts.append(
                    Alert(
                        type=AlertType.LEAD_TIME_EXCEEDED.value,
                        severity=AlertSeverity.YELLOW.value,
                        metric=key,
                        message=f"{key.replace('_', ' ').title()} 평균 {data['avg_days']:.1f}일 (목표: {data['target_days']}일)",
                        details={
                            "avg_days": data["avg_days"],
                            "target_days": data["target_days"],
                            "max_days": data.get("max_days", 0),
                        },
                    )
                )

        return alerts

    async def _get_top_plays(self, start: datetime, end: datetime) -> list[TopPlay]:
        """Top Plays 선정 (Mock 데이터)"""
        # 실제 구현은 DB에서 Signal/Brief 수 기준 정렬

        return [
            TopPlay(
                rank=1,
                play_id="EXT_Desk_D01_Seminar",
                play_name="대외 세미나 리서치",
                signal_count=12,
                brief_count=3,
                s2_count=1,
                owner="김에이전트",
            ),
            TopPlay(
                rank=2,
                play_id="KT_Sales_S01_Interview",
                play_name="KT 영업PM 인터뷰",
                signal_count=8,
                brief_count=2,
                s2_count=1,
                owner="이매니저",
            ),
            TopPlay(
                rank=3,
                play_id="KT_Inbound_I01",
                play_name="KT 인바운드 Triage",
                signal_count=6,
                brief_count=2,
                s2_count=0,
                owner="박담당",
            ),
        ]

    async def _get_status_summary(self) -> dict[str, int]:
        """Play 상태 요약 (Mock 데이터)"""
        return {
            "green": 8,
            "yellow": 3,
            "red": 1,
            "total": 12,
        }

    def _generate_recommendations(self, metrics: dict[str, Any], alerts: list[Alert]) -> list[str]:
        """추천 사항 생성"""
        recommendations = []

        # 경고 기반 추천
        under_target_metrics = [a.metric for a in alerts if a.type == AlertType.UNDER_TARGET.value]

        if "activity" in under_target_metrics:
            recommendations.append("📌 Activity 목표 달성을 위해 세미나/인터뷰 추가 계획 필요")

        if "signal" in under_target_metrics:
            recommendations.append(
                "📌 Signal 추출 효율화: 기존 Activity 재검토 또는 새로운 원천 탐색"
            )

        if "brief" in under_target_metrics:
            recommendations.append(
                "📌 Brief 전환율 향상: 대기 중인 Signal Scorecard 평가 우선 진행"
            )

        # 리드타임 초과
        lead_time_alerts = [a for a in alerts if a.type == AlertType.LEAD_TIME_EXCEEDED.value]

        if lead_time_alerts:
            recommendations.append("⏱️ 리드타임 단축: 병목 구간 분석 및 프로세스 개선 검토")

        # 성과 좋을 때
        if not recommendations:
            all_good = all(
                metrics[k]["achievement"] >= 100 for k in ["activity", "signal", "brief"]
            )
            if all_good:
                recommendations.append("🎉 모든 KPI 목표 달성! 현재 페이스 유지")
            else:
                recommendations.append("✅ 대부분의 KPI가 양호합니다. 지속적인 모니터링 권장")

        return recommendations

    async def _publish_report(
        self,
        period: str,
        metrics: dict[str, Any],
        lead_times: dict[str, Any],
        alerts: list[Alert],
        top_plays: list[TopPlay],
        recommendations: list[str],
    ) -> str:
        """Confluence에 리포트 게시"""
        # TODO: Confluence MCP 연동
        self.logger.info("Publishing KPI report to Confluence")
        return ""

    async def _send_notifications(self, confluence_url: str, alerts: list[Alert]) -> None:
        """Teams/Slack 알림 전송"""
        # TODO: Teams MCP 연동
        red_alerts = [a for a in alerts if a.severity == AlertSeverity.RED.value]
        if red_alerts:
            self.logger.warning(
                "Sending RED alert notifications",
                count=len(red_alerts),
            )


# ============================================================
# AG-UI 이벤트 발행 버전
# ============================================================


class KPIDigestPipelineWithEvents(KPIDigestPipeline):
    """
    WF-05: KPI Digest with AG-UI Events

    실시간 이벤트 발행을 포함한 KPI Digest 파이프라인
    """

    def __init__(self, emitter: "WorkflowEventEmitter"):
        super().__init__()
        self.emitter = emitter
        self.logger = logger.bind(workflow="WF-05", with_events=True)

    async def run(self, input_data: KPIInput) -> KPIDigestOutput:
        """워크플로 실행 (이벤트 발행 포함)"""
        self.logger.info("Starting KPI Digest with events", period=input_data.period)

        # 실행 시작 이벤트
        await self.emitter.emit_run_started(
            workflow_id="WF-05",
            input_data={
                "period": input_data.period,
                "notify": input_data.notify,
            },
            steps=self.STEPS,
        )

        try:
            # Step 1: 기간 계산
            await self.emitter.emit_step_started(
                step_id="PERIOD_CALC",
                step_index=0,
                step_label="기간 계산",
                message=f"{input_data.period} 기간을 계산하고 있습니다...",
            )

            period_start, period_end = calculate_period_range(input_data.period)

            await self.emitter.emit_step_finished(
                step_id="PERIOD_CALC",
                step_index=0,
                result={
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat(),
                },
            )

            # Step 2: 메트릭 집계
            await self.emitter.emit_step_started(
                step_id="METRICS_AGGREGATE",
                step_index=1,
                step_label="메트릭 집계",
                message="Activity, Signal, Brief, S2 메트릭을 집계하고 있습니다...",
            )

            metrics = await self._aggregate_metrics(period_start, period_end, input_data.play_ids)

            await self.emitter.emit_surface(
                surface_id="metrics-summary",
                surface={
                    "id": "metrics-summary",
                    "type": "kpi_metrics",
                    "title": "KPI 메트릭 요약",
                    "metrics": {
                        "activity": metrics["activity"],
                        "signal": metrics["signal"],
                        "brief": metrics["brief"],
                        "s2": metrics["s2"],
                    },
                },
            )

            await self.emitter.emit_step_finished(
                step_id="METRICS_AGGREGATE",
                step_index=1,
                result={"metrics_collected": True},
            )

            # Step 3: 리드타임 계산
            await self.emitter.emit_step_started(
                step_id="LEAD_TIME_CALC",
                step_index=2,
                step_label="리드타임 계산",
                message="Signal→Brief, Brief→S2 리드타임을 계산하고 있습니다...",
            )

            lead_times = await self._calculate_lead_times(period_start, period_end)

            await self.emitter.emit_surface(
                surface_id="lead-times",
                surface={
                    "id": "lead-times",
                    "type": "lead_times",
                    "title": "리드타임 분석",
                    "lead_times": lead_times,
                },
            )

            await self.emitter.emit_step_finished(
                step_id="LEAD_TIME_CALC",
                step_index=2,
                result=lead_times,
            )

            # Step 4: 경고 생성
            await self.emitter.emit_step_started(
                step_id="ALERTS_GENERATE",
                step_index=3,
                step_label="경고 생성",
                message="목표 미달 및 지연 항목을 분석하고 있습니다...",
            )

            alerts = await self._generate_alerts(metrics, lead_times)

            if alerts:
                await self.emitter.emit_surface(
                    surface_id="alerts",
                    surface={
                        "id": "alerts",
                        "type": "kpi_alerts",
                        "title": f"경고 {len(alerts)}건",
                        "alerts": [self._alert_to_dict(a) for a in alerts],
                    },
                )

            await self.emitter.emit_step_finished(
                step_id="ALERTS_GENERATE",
                step_index=3,
                result={"alerts_count": len(alerts)},
            )

            # Step 5: Top Plays 선정
            await self.emitter.emit_step_started(
                step_id="TOP_PLAYS",
                step_index=4,
                step_label="Top Plays 선정",
                message="성과 우수 Play를 선정하고 있습니다...",
            )

            top_plays = await self._get_top_plays(period_start, period_end)

            await self.emitter.emit_surface(
                surface_id="top-plays",
                surface={
                    "id": "top-plays",
                    "type": "leaderboard",
                    "title": "Top Plays",
                    "plays": [self._top_play_to_dict(p) for p in top_plays],
                },
            )

            await self.emitter.emit_step_finished(
                step_id="TOP_PLAYS",
                step_index=4,
                result={"top_plays_count": len(top_plays)},
            )

            # Step 6: 추천 사항 생성
            await self.emitter.emit_step_started(
                step_id="RECOMMENDATIONS",
                step_index=5,
                step_label="추천 사항 생성",
                message="개선 권고사항을 생성하고 있습니다...",
            )

            recommendations = []
            if input_data.include_recommendations:
                recommendations = self._generate_recommendations(metrics, alerts)

            status_summary = await self._get_status_summary()

            await self.emitter.emit_step_finished(
                step_id="RECOMMENDATIONS",
                step_index=5,
                result={"recommendations_count": len(recommendations)},
            )

            # Confluence 발행 (선택)
            confluence_url = None
            if input_data.notify:
                confluence_url = await self._publish_report(
                    input_data.period, metrics, lead_times, alerts, top_plays, recommendations
                )
                await self._send_notifications(confluence_url, alerts)

            # 결과 생성
            result = KPIDigestOutput(
                period=input_data.period,
                period_start=period_start.isoformat(),
                period_end=period_end.isoformat(),
                metrics=metrics,
                lead_times=lead_times,
                alerts=[self._alert_to_dict(a) for a in alerts],
                top_plays=[self._top_play_to_dict(p) for p in top_plays],
                recommendations=recommendations,
                status_summary=status_summary,
                confluence_url=confluence_url,
                generated_at=datetime.now(UTC).isoformat(),
            )

            # 실행 완료 이벤트
            await self.emitter.emit_run_finished(
                result={
                    "period": result.period,
                    "alerts_count": len(alerts),
                    "recommendations_count": len(recommendations),
                }
            )

            return result

        except Exception as e:
            self.logger.error("Pipeline error", error=str(e))
            await self.emitter.emit_run_error(str(e), recoverable=False)
            raise


# ============================================================
# DB 연동 버전
# ============================================================


class KPIDigestPipelineWithDB(KPIDigestPipelineWithEvents):
    """
    WF-05: KPI Digest with DB Integration

    데이터베이스 연동을 포함한 완전한 파이프라인
    """

    def __init__(self, emitter: "WorkflowEventEmitter", db: "AsyncSession"):
        super().__init__(emitter)
        self.db = db
        self.logger = logger.bind(workflow="WF-05", with_db=True)

    async def _aggregate_metrics(
        self, start: datetime, end: datetime, play_ids: list[str] | None
    ) -> dict[str, Any]:
        """DB 기반 메트릭 집계"""
        from backend.database.repositories.play_record import play_record_repo
        from backend.database.repositories.signal import signal_repo

        # PlayRecord에서 전체 통계 가져오기
        stats = await play_record_repo.get_stats(self.db)

        # 주간/월간 목표 설정
        period_days = (end - start).days + 1
        multiplier = period_days / 7  # 주간 기준 배수

        activity_target = int(self.targets.activity_weekly * multiplier)
        signal_target = int(self.targets.signal_weekly * multiplier)
        brief_target = int(self.targets.brief_weekly * multiplier)

        # Signal 원천별 통계
        by_source = {}
        for source in ["KT", "그룹사", "대외"]:
            items, count = await signal_repo.get_multi_filtered(
                self.db, source=source, skip=0, limit=1000
            )
            by_source[source] = {
                "signal": count,
            }

        return {
            "activity": {
                "actual": stats["total_activity"],
                "target": activity_target,
                "achievement": calculate_achievement(stats["total_activity"], activity_target),
            },
            "signal": {
                "actual": stats["total_signal"],
                "target": signal_target,
                "achievement": calculate_achievement(stats["total_signal"], signal_target),
            },
            "brief": {
                "actual": stats["total_brief"],
                "target": brief_target,
                "achievement": calculate_achievement(stats["total_brief"], brief_target),
            },
            "s2": {
                "actual": stats["total_s2"],
                "target_min": self.targets.s2_weekly_min,
                "target_max": self.targets.s2_weekly_max,
                "achievement": calculate_achievement(stats["total_s2"], self.targets.s2_weekly_min),
            },
            "s3": {
                "actual": stats["total_s3"],
                "target": 1,
                "achievement": calculate_achievement(stats["total_s3"], 1),
            },
            "by_source": by_source,
        }

    async def _calculate_lead_times(self, start: datetime, end: datetime) -> dict[str, Any]:
        """DB 기반 리드타임 계산"""

        # Signal → Brief 리드타임 (Brief가 있는 Signal 기준)
        # TODO: 실제 구현은 Signal.created_at과 Brief.created_at 차이 계산
        signal_to_brief_days: list[float] = []

        # Brief → S2 리드타임 (VALIDATED 상태인 Brief 기준)
        # TODO: Brief.created_at과 validation 완료 시점 차이 계산
        brief_to_s2_days: list[float] = []

        # Mock 데이터 (실제 구현 시 DB 쿼리로 대체)
        signal_to_brief_avg = (
            5.2
            if not signal_to_brief_days
            else sum(signal_to_brief_days) / len(signal_to_brief_days)
        )
        brief_to_s2_avg = (
            11.0 if not brief_to_s2_days else sum(brief_to_s2_days) / len(brief_to_s2_days)
        )

        return {
            "signal_to_brief": {
                "avg_days": signal_to_brief_avg,
                "target_days": self.targets.signal_to_brief_days,
                "on_target": signal_to_brief_avg <= self.targets.signal_to_brief_days,
                "sample_count": len(signal_to_brief_days) or 8,
            },
            "brief_to_s2": {
                "avg_days": brief_to_s2_avg,
                "target_days": self.targets.brief_to_s2_days,
                "on_target": brief_to_s2_avg <= self.targets.brief_to_s2_days,
                "sample_count": len(brief_to_s2_days) or 3,
            },
        }

    async def _get_top_plays(self, start: datetime, end: datetime) -> list[TopPlay]:
        """DB 기반 Top Plays 선정"""
        from backend.database.repositories.play_record import play_record_repo

        leaderboard = await play_record_repo.get_leaderboard(self.db)

        top_plays = []
        for i, play_data in enumerate(leaderboard.get("top_plays", [])[:5]):
            top_plays.append(
                TopPlay(
                    rank=i + 1,
                    play_id=play_data["play_id"],
                    play_name=play_data.get("play_name", play_data["play_id"]),
                    signal_count=play_data.get("signal_qtd", 0),
                    brief_count=play_data.get("brief_qtd", 0),
                    s2_count=0,  # TODO: S2 count 추가
                    owner=None,
                )
            )

        return top_plays

    async def _get_status_summary(self) -> dict[str, int]:
        """DB 기반 Play 상태 요약"""
        from backend.database.repositories.play_record import play_record_repo

        alerts_data = await play_record_repo.get_alerts(self.db)

        green_count = await self._count_plays_by_status("G")
        yellow_count = len(alerts_data.get("yellow_plays", []))
        red_count = len(alerts_data.get("red_plays", []))

        return {
            "green": green_count,
            "yellow": yellow_count,
            "red": red_count,
            "total": green_count + yellow_count + red_count,
        }

    async def _count_plays_by_status(self, status: str) -> int:
        """특정 상태의 Play 수 조회"""
        from backend.database.repositories.play_record import play_record_repo

        items, total = await play_record_repo.get_multi_filtered(
            self.db, status=status, skip=0, limit=1
        )
        return total


# ============================================================
# 워크플로 인스턴스 및 진입점
# ============================================================

workflow = KPIDigestPipeline()


async def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """워크플로 진입점"""
    kpi_input = KPIInput(
        period=input_data.get("period", "week"),
        play_ids=input_data.get("play_ids"),
        notify=input_data.get("notify", False),
        include_recommendations=input_data.get("include_recommendations", True),
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
        "status_summary": result.status_summary,
        "confluence_url": result.confluence_url,
        "generated_at": result.generated_at,
    }


async def run_with_events(
    input_data: dict[str, Any], emitter: "WorkflowEventEmitter"
) -> dict[str, Any]:
    """이벤트 발행을 포함한 워크플로 실행"""
    kpi_input = KPIInput(
        period=input_data.get("period", "week"),
        play_ids=input_data.get("play_ids"),
        notify=input_data.get("notify", False),
        include_recommendations=input_data.get("include_recommendations", True),
    )

    pipeline = KPIDigestPipelineWithEvents(emitter)
    result = await pipeline.run(kpi_input)

    return {
        "period": result.period,
        "period_start": result.period_start,
        "period_end": result.period_end,
        "metrics": result.metrics,
        "lead_times": result.lead_times,
        "alerts": result.alerts,
        "top_plays": result.top_plays,
        "recommendations": result.recommendations,
        "status_summary": result.status_summary,
        "confluence_url": result.confluence_url,
        "generated_at": result.generated_at,
    }


# 타입 힌트를 위한 import (순환 참조 방지)
if __name__ != "__main__":
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.agent_runtime.event_manager import WorkflowEventEmitter
