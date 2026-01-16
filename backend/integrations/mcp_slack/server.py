"""
Slack MCP Server

Slack 연동을 위한 MCP 서버
Incoming Webhook 및 Block Kit 지원
"""

import os
from datetime import datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class SlackMCP:
    """
    Slack MCP 서버

    Tools:
    - slack.send_message: 채널에 텍스트 메시지 전송
    - slack.send_notification: 알림 전송 (색상 강조)
    - slack.send_blocks: Block Kit 메시지 전송
    - slack.request_approval: 승인 요청 메시지 전송
    - slack.send_kpi_digest: KPI Digest 메시지 전송
    """

    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        self.channel_name = os.getenv("SLACK_CHANNEL_NAME", "#ax-bd-alerts")
        self._client: httpx.AsyncClient | None = None
        self.logger = logger.bind(mcp="slack")

    @property
    def client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트 (lazy init)"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _validate_webhook(self) -> None:
        """Webhook URL 검증"""
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL not configured")
        if not self.webhook_url.startswith("https://hooks.slack.com/"):
            raise ValueError("SLACK_WEBHOOK_URL must start with https://hooks.slack.com/")

    # ========== 메시지 Tools ==========

    async def send_message(self, text: str, title: str | None = None) -> dict[str, Any]:
        """
        채널에 텍스트 메시지 전송

        Args:
            text: 메시지 본문
            title: 메시지 제목 (선택)

        Returns:
            전송 결과
        """
        self.logger.info("send_message", title=title, text_length=len(text))
        self._validate_webhook()

        try:
            payload = self._build_simple_message(text=text, title=title)
            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            self.logger.info("send_message_success", status=response.status_code)
            return {
                "status": "sent",
                "channel": self.channel_name,
                "timestamp": datetime.now().isoformat(),
            }
        except httpx.HTTPStatusError as e:
            self.logger.error("send_message_failed", status=e.response.status_code, error=str(e))
            raise
        except Exception as e:
            self.logger.error("send_message_failed", error=str(e))
            raise

    async def send_notification(
        self,
        text: str,
        title: str,
        level: str = "info",
        fields: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        알림 전송 (색상 강조 지원)

        Args:
            text: 알림 본문
            title: 알림 제목
            level: 알림 수준 (info, warning, error, success)
            fields: 추가 정보 (key-value 쌍)

        Returns:
            전송 결과
        """
        self.logger.info("send_notification", title=title, level=level)
        self._validate_webhook()

        try:
            payload = self._build_notification_message(
                text=text, title=title, level=level, fields=fields
            )
            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            self.logger.info("send_notification_success", level=level)
            return {
                "status": "sent",
                "level": level,
                "channel": self.channel_name,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error("send_notification_failed", error=str(e))
            raise

    async def send_blocks(self, blocks: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Block Kit 메시지 전송

        Args:
            blocks: Slack Block Kit 블록 리스트

        Returns:
            전송 결과
        """
        self.logger.info("send_blocks", block_count=len(blocks))
        self._validate_webhook()

        try:
            payload = {"blocks": blocks}
            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            self.logger.info("send_blocks_success")
            return {
                "status": "sent",
                "channel": self.channel_name,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error("send_blocks_failed", error=str(e))
            raise

    async def request_approval(
        self,
        title: str,
        description: str,
        requester: str,
        item_id: str,
        item_type: str = "Brief",
        details: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        승인 요청 메시지 전송

        Args:
            title: 승인 요청 제목
            description: 요청 설명
            requester: 요청자
            item_id: 승인 대상 ID
            item_type: 승인 대상 유형 (Brief, Scorecard, Play 등)
            details: 추가 상세 정보

        Returns:
            전송 결과
        """
        self.logger.info("request_approval", title=title, item_id=item_id, item_type=item_type)
        self._validate_webhook()

        try:
            payload = self._build_approval_message(
                title=title,
                description=description,
                requester=requester,
                item_id=item_id,
                item_type=item_type,
                details=details,
            )
            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            self.logger.info("request_approval_success", item_id=item_id)
            return {
                "status": "pending",
                "item_id": item_id,
                "item_type": item_type,
                "channel": self.channel_name,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error("request_approval_failed", error=str(e))
            raise

    async def send_kpi_digest(
        self,
        period: str,
        metrics: dict[str, int],
        alerts: list[str] | None = None,
        top_plays: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        KPI Digest 메시지 전송

        Args:
            period: 기간 (예: "2026-W03", "2026-01")
            metrics: KPI 메트릭 (예: {"activities": 25, "signals": 30, ...})
            alerts: 경고 목록
            top_plays: 우수 Play 목록

        Returns:
            전송 결과
        """
        self.logger.info("send_kpi_digest", period=period)
        self._validate_webhook()

        try:
            payload = self._build_kpi_digest_message(
                period=period, metrics=metrics, alerts=alerts, top_plays=top_plays
            )
            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            self.logger.info("send_kpi_digest_success", period=period)
            return {
                "status": "sent",
                "period": period,
                "channel": self.channel_name,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error("send_kpi_digest_failed", error=str(e))
            raise

    # ========== 메시지 빌더 ==========

    def _build_simple_message(self, text: str, title: str | None = None) -> dict[str, Any]:
        """간단한 메시지 빌드"""
        if title:
            return {"text": f"*{title}*\n{text}"}
        return {"text": text}

    def _build_notification_message(
        self,
        text: str,
        title: str,
        level: str = "info",
        fields: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """알림 메시지 빌드 (Attachment 사용)"""
        color_map = {
            "info": "#0076D7",  # 파랑
            "success": "#28A745",  # 초록
            "warning": "#FFC107",  # 노랑
            "error": "#DC3545",  # 빨강
        }
        icon_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }

        attachment: dict[str, Any] = {
            "color": color_map.get(level, "#0076D7"),
            "title": f"{icon_map.get(level, 'ℹ️')} {title}",
            "text": text,
            "mrkdwn_in": ["text"],
        }

        if fields:
            attachment["fields"] = [
                {"title": k, "value": v, "short": True} for k, v in fields.items()
            ]

        return {"attachments": [attachment]}

    def _build_approval_message(
        self,
        title: str,
        description: str,
        requester: str,
        item_id: str,
        item_type: str,
        details: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """승인 요청 메시지 빌드 (Block Kit 사용)"""
        base_url = "https://ax-discovery-portal.pages.dev"

        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🔔 {title}", "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": description},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*요청자:*\n{requester}"},
                    {"type": "mrkdwn", "text": f"*유형:*\n{item_type}"},
                    {"type": "mrkdwn", "text": f"*ID:*\n{item_id}"},
                ],
            },
        ]

        # 추가 상세 정보
        if details:
            detail_fields = [{"type": "mrkdwn", "text": f"*{k}:*\n{v}"} for k, v in details.items()]
            blocks.append({"type": "section", "fields": detail_fields[:10]})  # 최대 10개

        # 구분선
        blocks.append({"type": "divider"})

        # 액션 버튼
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ 승인", "emoji": True},
                        "style": "primary",
                        "url": f"{base_url}/{item_type.lower()}/{item_id}?action=approve",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ 반려", "emoji": True},
                        "style": "danger",
                        "url": f"{base_url}/{item_type.lower()}/{item_id}?action=reject",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📋 상세 보기", "emoji": True},
                        "url": f"{base_url}/{item_type.lower()}/{item_id}",
                    },
                ],
            }
        )

        return {"blocks": blocks}

    def _build_kpi_digest_message(
        self,
        period: str,
        metrics: dict[str, int],
        alerts: list[str] | None = None,
        top_plays: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """KPI Digest 메시지 빌드 (Block Kit 사용)"""
        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📈 KPI Digest - {period}", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*📥 Activities:*\n{metrics.get('activities', 0)}",
                    },
                    {"type": "mrkdwn", "text": f"*📊 Signals:*\n{metrics.get('signals', 0)}"},
                    {"type": "mrkdwn", "text": f"*📝 Briefs:*\n{metrics.get('briefs', 0)}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*✅ S2 Validated:*\n{metrics.get('s2_validated', 0)}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*🚀 S3 Pilot-ready:*\n{metrics.get('s3_pilot_ready', 0)}",
                    },
                ],
            },
        ]

        # 경고 섹션
        if alerts:
            alert_text = "\n".join([f"• {alert}" for alert in alerts[:5]])
            blocks.append({"type": "divider"})
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*⚠️ Alerts*\n{alert_text}"},
                }
            )

        # Top Plays 섹션
        if top_plays:
            plays_text = "\n".join(
                [
                    f"{i}. *{play.get('name', 'Unknown')}* - {play.get('score', 'N/A')}점"
                    for i, play in enumerate(top_plays[:3], 1)
                ]
            )
            blocks.append({"type": "divider"})
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*🏆 Top Plays*\n{plays_text}"},
                }
            )

        # 대시보드 링크
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📊 대시보드 보기", "emoji": True},
                        "url": "https://ax-discovery-portal.pages.dev/plays",
                    },
                ],
            }
        )

        return {"blocks": blocks}

    # ========== 정리 ==========

    async def close(self) -> None:
        """HTTP 클라이언트 정리"""
        if self._client:
            await self._client.aclose()
            self._client = None


# MCP Tool 정의
MCP_TOOLS = [
    {
        "name": "slack.send_message",
        "description": "Slack 채널에 텍스트 메시지 전송",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "메시지 본문"},
                "title": {"type": "string", "description": "메시지 제목 (선택)"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "slack.send_notification",
        "description": "Slack 채널에 알림 전송 (색상 강조 지원)",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "알림 본문"},
                "title": {"type": "string", "description": "알림 제목"},
                "level": {
                    "type": "string",
                    "enum": ["info", "success", "warning", "error"],
                    "description": "알림 수준",
                },
                "fields": {
                    "type": "object",
                    "description": "추가 정보 (key-value 쌍)",
                },
            },
            "required": ["text", "title"],
        },
    },
    {
        "name": "slack.send_blocks",
        "description": "Slack 채널에 Block Kit 메시지 전송",
        "parameters": {
            "type": "object",
            "properties": {
                "blocks": {
                    "type": "array",
                    "description": "Slack Block Kit 블록 리스트",
                },
            },
            "required": ["blocks"],
        },
    },
    {
        "name": "slack.request_approval",
        "description": "Slack 채널에 승인 요청 메시지 전송",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "승인 요청 제목"},
                "description": {"type": "string", "description": "요청 설명"},
                "requester": {"type": "string", "description": "요청자"},
                "item_id": {"type": "string", "description": "승인 대상 ID"},
                "item_type": {
                    "type": "string",
                    "enum": ["Brief", "Scorecard", "Play", "Signal"],
                    "description": "승인 대상 유형",
                },
                "details": {
                    "type": "object",
                    "description": "추가 상세 정보",
                },
            },
            "required": ["title", "description", "requester", "item_id"],
        },
    },
    {
        "name": "slack.send_kpi_digest",
        "description": "Slack 채널에 KPI Digest 메시지 전송",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "기간 (예: 2026-W03)"},
                "metrics": {
                    "type": "object",
                    "description": "KPI 메트릭 (activities, signals, briefs, s2_validated, s3_pilot_ready)",
                },
                "alerts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "경고 목록",
                },
                "top_plays": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "우수 Play 목록",
                },
            },
            "required": ["period", "metrics"],
        },
    },
]


# MCP 서버 진입점
if __name__ == "__main__":
    import asyncio

    async def main():
        mcp = SlackMCP()
        print("Slack MCP Server")
        print(f"Webhook configured: {'Yes' if mcp.webhook_url else 'No'}")
        print(f"Channel: {mcp.channel_name}")
        print(f"Tools: {[t['name'] for t in MCP_TOOLS]}")

    asyncio.run(main())
