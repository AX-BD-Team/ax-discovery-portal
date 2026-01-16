"""
Teams MCP Server 단위 테스트

TeamsMCP 클래스의 각 메서드를 테스트합니다.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.integrations.mcp_teams.server import MCP_TOOLS, TeamsMCP

# ========== Fixtures ==========


@pytest.fixture
def mock_teams_env(monkeypatch):
    """Teams 환경변수 Mock"""
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://outlook.office.com/webhook/test-webhook")
    monkeypatch.setenv("TEAMS_CHANNEL_NAME", "Test-Channel")
    return monkeypatch


@pytest.fixture
def teams_mcp(mock_teams_env):
    """TeamsMCP 인스턴스"""
    return TeamsMCP()


@pytest.fixture
def teams_mcp_no_webhook():
    """Webhook 미설정 TeamsMCP 인스턴스"""
    with patch.dict("os.environ", {"TEAMS_WEBHOOK_URL": ""}, clear=False):
        return TeamsMCP()


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


class TestTeamsMCPInit:
    """TeamsMCP 초기화 테스트"""

    def test_init_with_env(self, mock_teams_env):
        """환경변수로 초기화"""
        mcp = TeamsMCP()
        assert mcp.webhook_url == "https://outlook.office.com/webhook/test-webhook"
        assert mcp.channel_name == "Test-Channel"

    def test_init_without_env(self):
        """환경변수 없이 초기화"""
        with patch.dict("os.environ", {"TEAMS_WEBHOOK_URL": ""}, clear=False):
            mcp = TeamsMCP()
            assert mcp.webhook_url == ""
            assert mcp.channel_name == "AX-BD-Alerts"  # 기본값

    def test_validate_webhook_missing(self, teams_mcp_no_webhook):
        """Webhook URL 미설정 시 검증 실패"""
        with pytest.raises(ValueError, match="TEAMS_WEBHOOK_URL not configured"):
            teams_mcp_no_webhook._validate_webhook()

    def test_validate_webhook_invalid_protocol(self, monkeypatch):
        """Webhook URL이 HTTPS가 아닌 경우"""
        monkeypatch.setenv("TEAMS_WEBHOOK_URL", "http://insecure-webhook")
        mcp = TeamsMCP()
        with pytest.raises(ValueError, match="TEAMS_WEBHOOK_URL must be HTTPS"):
            mcp._validate_webhook()


# ========== send_message 테스트 ==========


class TestSendMessage:
    """send_message 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_send_message_success(self, teams_mcp, mock_httpx_client):
        """메시지 전송 성공"""
        teams_mcp._client = mock_httpx_client

        result = await teams_mcp.send_message(text="테스트 메시지", title="테스트 제목")

        assert result["status"] == "sent"
        assert result["channel"] == "Test-Channel"
        assert "timestamp" in result
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_without_title(self, teams_mcp, mock_httpx_client):
        """제목 없이 메시지 전송"""
        teams_mcp._client = mock_httpx_client

        result = await teams_mcp.send_message(text="제목 없는 메시지")

        assert result["status"] == "sent"
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_no_webhook(self, teams_mcp_no_webhook):
        """Webhook 미설정 시 실패"""
        with pytest.raises(ValueError, match="TEAMS_WEBHOOK_URL not configured"):
            await teams_mcp_no_webhook.send_message(text="테스트")


# ========== send_notification 테스트 ==========


class TestSendNotification:
    """send_notification 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_send_notification_info(self, teams_mcp, mock_httpx_client):
        """Info 레벨 알림"""
        teams_mcp._client = mock_httpx_client

        result = await teams_mcp.send_notification(
            text="정보 알림", title="Info 알림", level="info"
        )

        assert result["status"] == "sent"
        assert result["level"] == "info"

    @pytest.mark.asyncio
    async def test_send_notification_with_facts(self, teams_mcp, mock_httpx_client):
        """Facts 포함 알림"""
        teams_mcp._client = mock_httpx_client

        result = await teams_mcp.send_notification(
            text="Signal 감지",
            title="High-Value Signal",
            level="success",
            facts={"Signal ID": "SIG-001", "점수": "85점"},
        )

        assert result["status"] == "sent"
        assert result["level"] == "success"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("level", ["info", "success", "warning", "error"])
    async def test_send_notification_all_levels(self, teams_mcp, mock_httpx_client, level):
        """모든 알림 레벨 테스트"""
        teams_mcp._client = mock_httpx_client

        result = await teams_mcp.send_notification(
            text=f"{level} 알림 테스트", title=f"{level.upper()} 알림", level=level
        )

        assert result["level"] == level


# ========== send_card 테스트 ==========


class TestSendCard:
    """send_card 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_send_card_success(self, teams_mcp, mock_httpx_client):
        """Adaptive Card 전송 성공"""
        teams_mcp._client = mock_httpx_client

        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [{"type": "TextBlock", "text": "테스트 카드"}],
        }

        result = await teams_mcp.send_card(card)

        assert result["status"] == "sent"
        mock_httpx_client.post.assert_called_once()


# ========== request_approval 테스트 ==========


class TestRequestApproval:
    """request_approval 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_request_approval_success(self, teams_mcp, mock_httpx_client):
        """승인 요청 전송 성공"""
        teams_mcp._client = mock_httpx_client

        result = await teams_mcp.request_approval(
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
    async def test_request_approval_with_details(self, teams_mcp, mock_httpx_client):
        """상세 정보 포함 승인 요청"""
        teams_mcp._client = mock_httpx_client

        result = await teams_mcp.request_approval(
            title="Play 승인",
            description="새 Play 등록 요청",
            requester="김철수",
            item_id="PLAY-002",
            item_type="Play",
            details={"고객사": "신한은행", "예상 규모": "10억원"},
        )

        assert result["status"] == "pending"
        assert result["item_id"] == "PLAY-002"


# ========== send_kpi_digest 테스트 ==========


class TestSendKPIDigest:
    """send_kpi_digest 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_send_kpi_digest_basic(self, teams_mcp, mock_httpx_client):
        """기본 KPI Digest 전송"""
        teams_mcp._client = mock_httpx_client

        result = await teams_mcp.send_kpi_digest(
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
    async def test_send_kpi_digest_with_alerts(self, teams_mcp, mock_httpx_client):
        """경고 포함 KPI Digest"""
        teams_mcp._client = mock_httpx_client

        result = await teams_mcp.send_kpi_digest(
            period="2026-W03",
            metrics={"activities": 10, "signals": 15},
            alerts=["Activity 목표 미달 (10/20)", "Signal→Brief 리드타임 초과"],
        )

        assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_kpi_digest_with_top_plays(self, teams_mcp, mock_httpx_client):
        """Top Plays 포함 KPI Digest"""
        teams_mcp._client = mock_httpx_client

        result = await teams_mcp.send_kpi_digest(
            period="2026-01",
            metrics={"activities": 80, "signals": 100},
            top_plays=[
                {"name": "KT Cloud AI", "score": "92"},
                {"name": "신한은행 DX", "score": "88"},
            ],
        )

        assert result["status"] == "sent"


# ========== 카드 빌더 테스트 ==========


class TestCardBuilders:
    """카드 빌더 메서드 테스트"""

    def test_build_message_card(self, teams_mcp):
        """MessageCard 빌드"""
        card = teams_mcp._build_message_card(text="테스트 메시지", title="테스트 제목")

        assert card["@type"] == "MessageCard"
        assert card["themeColor"] == "0076D7"
        assert card["sections"][0]["activityTitle"] == "테스트 제목"

    def test_build_notification_card_colors(self, teams_mcp):
        """알림 카드 색상 테스트"""
        color_map = {
            "info": "0076D7",
            "success": "28A745",
            "warning": "FFC107",
            "error": "DC3545",
        }

        for level, expected_color in color_map.items():
            card = teams_mcp._build_notification_card(text="테스트", title="테스트", level=level)
            assert card["themeColor"] == expected_color

    def test_build_approval_card(self, teams_mcp):
        """승인 요청 카드 빌드"""
        card = teams_mcp._build_approval_card(
            title="승인 요청",
            description="테스트 설명",
            requester="테스터",
            item_id="TEST-001",
            item_type="Brief",
            details=None,
        )

        assert "attachments" in card
        assert card["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"

    def test_build_kpi_digest_card(self, teams_mcp):
        """KPI Digest 카드 빌드"""
        card = teams_mcp._build_kpi_digest_card(
            period="2026-W03",
            metrics={"activities": 25, "signals": 30},
            alerts=["경고1"],
            top_plays=[{"name": "Play1", "score": "90"}],
        )

        assert "attachments" in card
        content = card["attachments"][0]["content"]
        assert content["type"] == "AdaptiveCard"


# ========== MCP_TOOLS 스키마 테스트 ==========


class TestMCPTools:
    """MCP_TOOLS 스키마 테스트"""

    def test_tools_count(self):
        """도구 개수 확인"""
        assert len(MCP_TOOLS) == 5

    def test_tools_names(self):
        """도구 이름 확인"""
        expected_names = [
            "teams.send_message",
            "teams.send_notification",
            "teams.send_card",
            "teams.request_approval",
            "teams.send_kpi_digest",
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


# ========== 클린업 테스트 ==========


class TestCleanup:
    """클린업 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_close_with_client(self, teams_mcp, mock_httpx_client):
        """클라이언트 있을 때 close"""
        teams_mcp._client = mock_httpx_client

        await teams_mcp.close()

        mock_httpx_client.aclose.assert_called_once()
        assert teams_mcp._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self, teams_mcp):
        """클라이언트 없을 때 close"""
        teams_mcp._client = None

        await teams_mcp.close()  # 에러 없이 완료되어야 함

        assert teams_mcp._client is None
