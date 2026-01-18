"""
알림 서비스

Play 진행 상황 Slack/Teams 알림
"""

import os
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.play_record import PlayRecord
from backend.database.models.task import Task
from backend.database.repositories.play_record import play_record_repo
from backend.database.repositories.task import task_repo
from backend.integrations.mcp_slack.server import SlackMCP
from backend.integrations.mcp_teams.server import TeamsMCP

logger = structlog.get_logger()


class NotificationService:
    """
    통합 알림 서비스

    Slack과 Teams로 Play 진행 상황 알림 전송
    """

    def __init__(self):
        self.slack = SlackMCP()
        self.teams = TeamsMCP()
        self.logger = logger.bind(service="notification")

        # 알림 채널 설정 (환경변수)
        self.enabled_channels = os.getenv("NOTIFICATION_CHANNELS", "slack,teams").split(",")

    async def _send_to_all(self, method_name: str, **kwargs) -> dict[str, Any]:
        """
        모든 활성화된 채널로 알림 전송

        Args:
            method_name: 호출할 메서드 이름
            **kwargs: 메서드 인자

        Returns:
            dict: 채널별 결과
        """
        results = {}

        if "slack" in self.enabled_channels:
            try:
                method = getattr(self.slack, method_name)
                results["slack"] = await method(**kwargs)
            except Exception as e:
                self.logger.error("Slack notification failed", error=str(e))
                results["slack"] = {"status": "error", "error": str(e)}

        if "teams" in self.enabled_channels:
            try:
                method = getattr(self.teams, method_name)
                results["teams"] = await method(**kwargs)
            except Exception as e:
                self.logger.error("Teams notification failed", error=str(e))
                results["teams"] = {"status": "error", "error": str(e)}

        return results

    async def notify_play_progress(
        self,
        play: PlayRecord,
        change_type: str,
        details: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Play 진행 상황 알림

        Args:
            play: PlayRecord
            change_type: 변경 유형 (task_completed, goal_achieved, rag_changed)
            details: 추가 상세 정보

        Returns:
            dict: 알림 결과
        """
        # 알림 제목 및 레벨 결정
        title_map = {
            "task_completed": "✅ Task 완료",
            "goal_achieved": "🎯 목표 달성",
            "rag_changed": "📊 RAG 상태 변경",
            "signal_created": "📥 Signal 생성",
            "brief_created": "📝 Brief 생성",
            "s2_entered": "🚀 S2 진입",
        }

        level_map = {
            "task_completed": "success",
            "goal_achieved": "success",
            "rag_changed": "warning" if play.status in ["Y", "R"] else "info",
            "signal_created": "info",
            "brief_created": "info",
            "s2_entered": "success",
        }

        title = title_map.get(change_type, "📢 Play 업데이트")
        level = level_map.get(change_type, "info")

        # 알림 본문
        rag_emoji = {"G": "🟢", "Y": "🟡", "R": "🔴"}
        rag = rag_emoji.get(
            play.status if isinstance(play.status, str) else play.status.value, "⚪"
        )

        text = (
            f"*{play.play_name}*\n상태: {rag} | Signal: {play.signal_qtd} | Brief: {play.brief_qtd}"
        )

        # 필드 정보
        fields = {
            "Play ID": play.play_id,
            "Owner": play.owner or "-",
        }
        if details:
            fields.update(details)

        return await self._send_to_all(
            "send_notification",
            text=text,
            title=title,
            level=level,
            fields=fields,
        )

    async def notify_task_completed(
        self,
        db: AsyncSession,
        task: Task,
    ) -> dict[str, Any]:
        """
        Task 완료 알림

        Args:
            db: 데이터베이스 세션
            task: 완료된 Task

        Returns:
            dict: 알림 결과
        """
        play = await play_record_repo.get_by_id(db, task.play_id)
        if not play:
            return {"status": "skipped", "reason": "Play not found"}

        # Task 통계 조회
        stats = await task_repo.get_stats_by_play(db, task.play_id)

        details = {
            "Task": task.title,
            "진행률": f"{stats['completed']}/{stats['total']} ({stats['completion_rate']:.0%})",
        }

        return await self.notify_play_progress(play, "task_completed", details)

    async def notify_goal_achieved(
        self,
        db: AsyncSession,
        play_id: str,
        goal_type: str,
    ) -> dict[str, Any]:
        """
        목표 달성 알림

        Args:
            db: 데이터베이스 세션
            play_id: Play ID
            goal_type: 목표 유형 (signal, brief, s2)

        Returns:
            dict: 알림 결과
        """
        play = await play_record_repo.get_by_id(db, play_id)
        if not play:
            return {"status": "skipped", "reason": "Play not found"}

        goal_text = {
            "signal": f"Signal {play.signal_qtd}/{getattr(play, 'signal_goal', '?')}",
            "brief": f"Brief {play.brief_qtd}/{getattr(play, 'brief_goal', '?')}",
            "s2": f"S2 {play.s2_qtd}/{getattr(play, 's2_goal', '?')}",
        }

        details = {
            "달성 목표": goal_text.get(goal_type, goal_type),
        }

        return await self.notify_play_progress(play, "goal_achieved", details)

    async def notify_rag_changed(
        self,
        db: AsyncSession,
        play_id: str,
        old_rag: str,
        new_rag: str,
    ) -> dict[str, Any]:
        """
        RAG 상태 변경 알림

        Args:
            db: 데이터베이스 세션
            play_id: Play ID
            old_rag: 이전 RAG 상태
            new_rag: 새 RAG 상태

        Returns:
            dict: 알림 결과
        """
        play = await play_record_repo.get_by_id(db, play_id)
        if not play:
            return {"status": "skipped", "reason": "Play not found"}

        rag_emoji = {"G": "🟢 Green", "Y": "🟡 Yellow", "R": "🔴 Red"}

        details = {
            "변경": f"{rag_emoji.get(old_rag, old_rag)} → {rag_emoji.get(new_rag, new_rag)}",
        }

        return await self.notify_play_progress(play, "rag_changed", details)

    async def notify_overdue_tasks(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        기한 초과 Task 알림

        Args:
            db: 데이터베이스 세션

        Returns:
            dict: 알림 결과
        """
        overdue_tasks = await task_repo.get_overdue_tasks(db)

        if not overdue_tasks:
            return {"status": "skipped", "reason": "No overdue tasks"}

        # Play별 그룹화
        play_tasks: dict[str, list] = {}
        for task in overdue_tasks:
            if task.play_id not in play_tasks:
                play_tasks[task.play_id] = []
            play_tasks[task.play_id].append(task)

        text = f"*⚠️ 기한 초과 Task {len(overdue_tasks)}건*\n\n"
        for play_id, tasks in play_tasks.items():
            text += f"• *{play_id}*: {len(tasks)}건\n"
            for task in tasks[:3]:  # 최대 3개 표시
                text += f"  - {task.title} (기한: {task.due_date})\n"
            if len(tasks) > 3:
                text += f"  - ... 외 {len(tasks) - 3}건\n"

        return await self._send_to_all(
            "send_notification",
            text=text,
            title="⏰ 기한 초과 Task 알림",
            level="warning",
        )

    async def notify_blocked_tasks(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        블로킹된 Task 알림

        Args:
            db: 데이터베이스 세션

        Returns:
            dict: 알림 결과
        """
        blocked_tasks = await task_repo.get_blocked_tasks(db)

        if not blocked_tasks:
            return {"status": "skipped", "reason": "No blocked tasks"}

        text = f"*🚫 블로킹된 Task {len(blocked_tasks)}건*\n\n"
        for task in blocked_tasks[:10]:  # 최대 10개
            text += f"• *{task.title}*\n"
            text += f"  Play: {task.play_id}\n"
            if task.blocker_note:
                text += f"  사유: {task.blocker_note}\n"
            text += "\n"

        return await self._send_to_all(
            "send_notification",
            text=text,
            title="🚫 블로킹된 Task 알림",
            level="error",
        )

    async def send_daily_summary(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        일간 요약 알림

        Args:
            db: 데이터베이스 세션

        Returns:
            dict: 알림 결과
        """
        # 전체 통계
        stats = await play_record_repo.get_stats(db)

        # 알림
        alerts = await play_record_repo.get_alerts(db)

        metrics = {
            "activities": stats["total_activity"],
            "signals": stats["total_signal"],
            "briefs": stats["total_brief"],
            "s2_validated": stats["total_s2"],
            "s3_pilot_ready": stats.get("total_s3", 0),
        }

        alert_list = []
        if alerts["red_plays"]:
            alert_list.append(f"Red Play: {len(alerts['red_plays'])}개")
        if alerts["overdue_plays"]:
            alert_list.append(f"기한 초과: {len(alerts['overdue_plays'])}개")
        if alerts["stale_plays"]:
            alert_list.append(f"7일 이상 미활동: {len(alerts['stale_plays'])}개")

        period = datetime.now().strftime("%Y-%m-%d")

        return await self._send_to_all(
            "send_kpi_digest",
            period=period,
            metrics=metrics,
            alerts=alert_list if alert_list else None,
        )


# 싱글톤 인스턴스
notification_service = NotificationService()
