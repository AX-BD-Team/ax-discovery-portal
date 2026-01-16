"""
Slack MCP Server 단위 테스트

SlackMCP 클래스의 각 메서드를 테스트합니다.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.integrations.mcp_slack.server import MCP_TOOLS, SlackMCP

# ========== Fixtures ==========


@pytest.fixture
def mock_slack_env(monkeypatch):
    """Slack 환경변수 Mock"""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T00/B00/xxx")
    monkeypatch.setenv("SLACK_CHANNEL_NAME", "#test-channel")
    return monkeypatch


@pytest.fixture
def slack_mcp(mock_slack_env):
    """SlackMCP 인스턴스"""
    return SlackMCP()


@pytest.fixture
def slack_mcp_no_webhook():
    """Webhook 미설정 SlackMCP 인스턴스"""
    with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": ""}, clear=False):
        return SlackMCP()


@pytest.fixture
def mock_httpx_client():
    """httpx.AsyncClient Mock"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    return mock_client


# ========== 초기화 테스트 ==========


class TestSlackMCPInit:
    """SlackMCP 초기화 테스트"""

    def test_init_with_env(self, mock_slack_env):
        """환경변수로 초기화"""
        mcp = SlackMCP()
        assert mcp.webhook_url == "https://hooks.slack.com/services/T00/B00/xxx"
        assert mcp.channel_name == "#test-channel"

    def test_init_without_env(self):
        """환경변수 없이 초기화"""
        with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": ""}, clear=False):
            mcp = SlackMCP()
            assert mcp.webhook_url == ""
            assert mcp.channel_name == "#ax-bd-alerts"  # 기본값

    def test_validate_webhook_missing(self, slack_mcp_no_webhook):
        """Webhook URL 미설정 시 검증 실패"""
        with pytest.raises(ValueError, match="SLACK_WEBHOOK_URL not configured"):
            slack_mcp_no_webhook._validate_webhook()

    def test_validate_webhook_invalid_url(self, monkeypatch):
        """Webhook URL이 올바른 형식이 아닌 경우"""
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://invalid-url.com/webhook")
        mcp = SlackMCP()
        with pytest.raises(ValueError, match="SLACK_WEBHOOK_URL must start with"):
            mcp._validate_webhook()

    def test_client_lazy_init(self, slack_mcp):
        """HTTP 클라이언트 지연 초기화"""
        assert slack_mcp._client is None
        client = slack_mcp.client
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)


# ========== send_message 테스트 ==========


class TestSendMessage:
    """send_message 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_send_message_success(self, slack_mcp, mock_httpx_client):
        """메시지 전송 성공"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.send_message(text="테스트 메시지", title="테스트 제목")

        assert result["status"] == "sent"
        assert result["channel"] == "#test-channel"
        assert "timestamp" in result
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_without_title(self, slack_mcp, mock_httpx_client):
        """제목 없이 메시지 전송"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.send_message(text="제목 없는 메시지")

        assert result["status"] == "sent"
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_no_webhook(self, slack_mcp_no_webhook):
        """Webhook 미설정 시 실패"""
        with pytest.raises(ValueError, match="SLACK_WEBHOOK_URL not configured"):
            await slack_mcp_no_webhook.send_message(text="테스트")

    @pytest.mark.asyncio
    async def test_send_message_http_error(self, slack_mcp, mock_httpx_client):
        """HTTP 오류 발생 시 예외"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Bad Request", request=MagicMock(), response=mock_response
            )
        )
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        slack_mcp._client = mock_httpx_client

        with pytest.raises(httpx.HTTPStatusError):
            await slack_mcp.send_message(text="테스트")


# ========== send_notification 테스트 ==========


class TestSendNotification:
    """send_notification 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_send_notification_info(self, slack_mcp, mock_httpx_client):
        """Info 레벨 알림"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.send_notification(
            text="정보 알림", title="Info 알림", level="info"
        )

        assert result["status"] == "sent"
        assert result["level"] == "info"

    @pytest.mark.asyncio
    async def test_send_notification_with_fields(self, slack_mcp, mock_httpx_client):
        """Fields 포함 알림"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.send_notification(
            text="Signal 감지",
            title="High-Value Signal",
            level="success",
            fields={"Signal ID": "SIG-001", "점수": "85점"},
        )

        assert result["status"] == "sent"
        assert result["level"] == "success"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("level", ["info", "success", "warning", "error"])
    async def test_send_notification_all_levels(self, slack_mcp, mock_httpx_client, level):
        """모든 알림 레벨 테스트"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.send_notification(
            text=f"{level} 알림 테스트", title=f"{level.upper()} 알림", level=level
        )

        assert result["level"] == level

    @pytest.mark.asyncio
    async def test_send_notification_no_webhook(self, slack_mcp_no_webhook):
        """Webhook 미설정 시 실패"""
        with pytest.raises(ValueError, match="SLACK_WEBHOOK_URL not configured"):
            await slack_mcp_no_webhook.send_notification(text="테스트", title="테스트")


# ========== send_blocks 테스트 ==========


class TestSendBlocks:
    """send_blocks 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_send_blocks_success(self, slack_mcp, mock_httpx_client):
        """Block Kit 메시지 전송 성공"""
        slack_mcp._client = mock_httpx_client

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "테스트 블록"},
            },
            {
                "type": "divider",
            },
        ]

        result = await slack_mcp.send_blocks(blocks)

        assert result["status"] == "sent"
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_blocks_empty(self, slack_mcp, mock_httpx_client):
        """빈 블록 리스트 전송"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.send_blocks([])

        assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_blocks_no_webhook(self, slack_mcp_no_webhook):
        """Webhook 미설정 시 실패"""
        with pytest.raises(ValueError, match="SLACK_WEBHOOK_URL not configured"):
            await slack_mcp_no_webhook.send_blocks([{"type": "section"}])


# ========== request_approval 테스트 ==========


class TestRequestApproval:
    """request_approval 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_request_approval_success(self, slack_mcp, mock_httpx_client):
        """승인 요청 전송 성공"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.request_approval(
            title="Brief 승인 요청",
            description="KT Cloud AI 사업기회 Brief가 작성되었습니다.",
            requester="홍길동",
            item_id="BRF-001",
            item_type="Brief",
        )

        assert result["status"] == "pending"
        assert result["item_id"] == "BRF-001"
        assert result["item_type"] == "Brief"

    @pytest.mark.asyncio
    async def test_request_approval_with_details(self, slack_mcp, mock_httpx_client):
        """상세 정보 포함 승인 요청"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.request_approval(
            title="Play 승인",
            description="새 Play 등록 요청",
            requester="김철수",
            item_id="PLAY-002",
            item_type="Play",
            details={"고객사": "신한은행", "예상 규모": "10억원"},
        )

        assert result["status"] == "pending"
        assert result["item_id"] == "PLAY-002"

    @pytest.mark.asyncio
    async def test_request_approval_no_webhook(self, slack_mcp_no_webhook):
        """Webhook 미설정 시 실패"""
        with pytest.raises(ValueError, match="SLACK_WEBHOOK_URL not configured"):
            await slack_mcp_no_webhook.request_approval(
                title="테스트",
                description="테스트",
                requester="테스터",
                item_id="TEST-001",
            )


# ========== send_kpi_digest 테스트 ==========


class TestSendKPIDigest:
    """send_kpi_digest 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_send_kpi_digest_basic(self, slack_mcp, mock_httpx_client):
        """기본 KPI Digest 전송"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.send_kpi_digest(
            period="2026-W03",
            metrics={
                "activities": 25,
                "signals": 30,
                "briefs": 8,
                "s2_validated": 3,
                "s3_pilot_ready": 1,
            },
        )

        assert result["status"] == "sent"
        assert result["period"] == "2026-W03"

    @pytest.mark.asyncio
    async def test_send_kpi_digest_with_alerts(self, slack_mcp, mock_httpx_client):
        """경고 포함 KPI Digest"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.send_kpi_digest(
            period="2026-W03",
            metrics={"activities": 10, "signals": 15},
            alerts=["Activity 목표 미달 (10/20)", "Signal→Brief 리드타임 초과"],
        )

        assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_kpi_digest_with_top_plays(self, slack_mcp, mock_httpx_client):
        """Top Plays 포함 KPI Digest"""
        slack_mcp._client = mock_httpx_client

        result = await slack_mcp.send_kpi_digest(
            period="2026-01",
            metrics={"activities": 80, "signals": 100},
            top_plays=[
                {"name": "KT Cloud AI", "score": "92"},
                {"name": "신한은행 DX", "score": "88"},
            ],
        )

        assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_kpi_digest_no_webhook(self, slack_mcp_no_webhook):
        """Webhook 미설정 시 실패"""
        with pytest.raises(ValueError, match="SLACK_WEBHOOK_URL not configured"):
            await slack_mcp_no_webhook.send_kpi_digest(
                period="2026-W03",
                metrics={"activities": 10},
            )


# ========== 메시지 빌더 테스트 ==========


class TestMessageBuilders:
    """메시지 빌더 메서드 테스트"""

    def test_build_simple_message_with_title(self, slack_mcp):
        """제목 포함 간단한 메시지 빌드"""
        message = slack_mcp._build_simple_message(text="테스트 본문", title="테스트 제목")

        assert "text" in message
        assert "*테스트 제목*" in message["text"]
        assert "테스트 본문" in message["text"]

    def test_build_simple_message_without_title(self, slack_mcp):
        """제목 없는 간단한 메시지 빌드"""
        message = slack_mcp._build_simple_message(text="제목 없는 메시지")

        assert message["text"] == "제목 없는 메시지"

    def test_build_notification_message_colors(self, slack_mcp):
        """알림 메시지 색상 테스트"""
        color_map = {
            "info": "#0076D7",
            "success": "#28A745",
            "warning": "#FFC107",
            "error": "#DC3545",
        }

        for level, expected_color in color_map.items():
            message = slack_mcp._build_notification_message(
                text="테스트", title="테스트", level=level
            )
            assert message["attachments"][0]["color"] == expected_color

    def test_build_notification_message_with_fields(self, slack_mcp):
        """필드 포함 알림 메시지 빌드"""
        message = slack_mcp._build_notification_message(
            text="테스트",
            title="테스트 알림",
            level="info",
            fields={"필드1": "값1", "필드2": "값2"},
        )

        attachment = message["attachments"][0]
        assert "fields" in attachment
        assert len(attachment["fields"]) == 2

    def test_build_approval_message(self, slack_mcp):
        """승인 요청 메시지 빌드"""
        message = slack_mcp._build_approval_message(
            title="승인 요청",
            description="테스트 설명",
            requester="테스터",
            item_id="TEST-001",
            item_type="Brief",
            details=None,
        )

        assert "blocks" in message
        blocks = message["blocks"]
        assert len(blocks) >= 3  # header, section, fields, divider, actions

        # 액션 버튼 확인
        action_block = next((b for b in blocks if b.get("type") == "actions"), None)
        assert action_block is not None
        assert len(action_block["elements"]) == 3  # 승인, 반려, 상세 보기

    def test_build_approval_message_with_details(self, slack_mcp):
        """상세 정보 포함 승인 요청 메시지"""
        message = slack_mcp._build_approval_message(
            title="승인 요청",
            description="테스트",
            requester="테스터",
            item_id="TEST-001",
            item_type="Brief",
            details={"고객사": "테스트사", "금액": "10억"},
        )

        blocks = message["blocks"]
        # 상세 정보가 포함되어 있어야 함
        field_blocks = [b for b in blocks if b.get("type") == "section" and "fields" in b]
        assert len(field_blocks) >= 2  # 기본 필드 + 상세 정보 필드

    def test_build_kpi_digest_message(self, slack_mcp):
        """KPI Digest 메시지 빌드"""
        message = slack_mcp._build_kpi_digest_message(
            period="2026-W03",
            metrics={"activities": 25, "signals": 30},
            alerts=None,
            top_plays=None,
        )

        assert "blocks" in message
        blocks = message["blocks"]

        # 헤더 확인
        header = blocks[0]
        assert header["type"] == "header"
        assert "2026-W03" in header["text"]["text"]

    def test_build_kpi_digest_message_with_alerts(self, slack_mcp):
        """경고 포함 KPI Digest 메시지"""
        message = slack_mcp._build_kpi_digest_message(
            period="2026-W03",
            metrics={"activities": 10},
            alerts=["경고1", "경고2"],
            top_plays=None,
        )

        blocks = message["blocks"]
        # 경고 섹션이 포함되어 있어야 함
        alert_block = next(
            (b for b in blocks if b.get("type") == "section" and "Alerts" in str(b)),
            None,
        )
        assert alert_block is not None

    def test_build_kpi_digest_message_with_top_plays(self, slack_mcp):
        """Top Plays 포함 KPI Digest 메시지"""
        message = slack_mcp._build_kpi_digest_message(
            period="2026-W03",
            metrics={"activities": 80},
            alerts=None,
            top_plays=[{"name": "Play1", "score": "90"}],
        )

        blocks = message["blocks"]
        # Top Plays 섹션이 포함되어 있어야 함
        plays_block = next(
            (b for b in blocks if b.get("type") == "section" and "Top Plays" in str(b)),
            None,
        )
        assert plays_block is not None


# ========== MCP_TOOLS 스키마 테스트 ==========


class TestMCPTools:
    """MCP_TOOLS 스키마 테스트"""

    def test_tools_count(self):
        """도구 개수 확인"""
        assert len(MCP_TOOLS) == 5

    def test_tools_names(self):
        """도구 이름 확인"""
        expected_names = [
            "slack.send_message",
            "slack.send_notification",
            "slack.send_blocks",
            "slack.request_approval",
            "slack.send_kpi_digest",
        ]
        actual_names = [tool["name"] for tool in MCP_TOOLS]
        assert actual_names == expected_names

    def test_tools_have_required_fields(self):
        """도구 필수 필드 확인"""
        for tool in MCP_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert "type" in tool["parameters"]
            assert "properties" in tool["parameters"]

    def test_send_message_schema(self):
        """send_message 스키마 확인"""
        tool = next(t for t in MCP_TOOLS if t["name"] == "slack.send_message")
        assert "text" in tool["parameters"]["properties"]
        assert "title" in tool["parameters"]["properties"]
        assert tool["parameters"]["required"] == ["text"]

    def test_send_notification_schema(self):
        """send_notification 스키마 확인"""
        tool = next(t for t in MCP_TOOLS if t["name"] == "slack.send_notification")
        props = tool["parameters"]["properties"]
        assert "level" in props
        assert props["level"]["enum"] == ["info", "success", "warning", "error"]

    def test_request_approval_schema(self):
        """request_approval 스키마 확인"""
        tool = next(t for t in MCP_TOOLS if t["name"] == "slack.request_approval")
        props = tool["parameters"]["properties"]
        assert "item_type" in props
        assert "Brief" in props["item_type"]["enum"]


# ========== 클린업 테스트 ==========


class TestCleanup:
    """클린업 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_close_with_client(self, slack_mcp, mock_httpx_client):
        """클라이언트 있을 때 close"""
        slack_mcp._client = mock_httpx_client

        await slack_mcp.close()

        mock_httpx_client.aclose.assert_called_once()
        assert slack_mcp._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self, slack_mcp):
        """클라이언트 없을 때 close"""
        slack_mcp._client = None

        await slack_mcp.close()  # 에러 없이 완료되어야 함

        assert slack_mcp._client is None
