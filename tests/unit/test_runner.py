"""
Agent Runtime Runner 단위 테스트

backend/agent_runtime/runner.py 테스트
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from backend.agent_runtime.runner import AgentRuntime, AgentConfig
from tests.fixtures.sample_agents import get_all_sample_agents
from tests.fixtures.sample_markdown import get_agent_markdown


class TestAgentLoading:
    """에이전트 로딩 테스트"""

    @pytest.mark.asyncio
    async def test_load_agents_success(self, mock_env, sample_agent_markdown, monkeypatch):
        """6개 에이전트 로드 성공 테스트"""
        # .claude/agents 경로를 tmp_path로 변경
        runtime = AgentRuntime()

        with patch("backend.agent_runtime.runner.Path") as MockPath:
            # .claude/agents 경로 Mock
            mock_agents_dir = sample_agent_markdown
            MockPath.return_value = mock_agents_dir

            # _load_agents 호출
            await runtime._load_agents()

            # 6개 에이전트 로드 확인
            assert len(runtime.agents) == 6
            assert "orchestrator" in runtime.agents
            assert "external_scout" in runtime.agents
            assert "scorecard_evaluator" in runtime.agents
            assert "brief_writer" in runtime.agents
            assert "confluence_sync" in runtime.agents
            assert "governance" in runtime.agents

            # 각 에이전트의 구조 확인
            orchestrator = runtime.agents["orchestrator"]
            assert "config" in orchestrator
            assert "definition" in orchestrator
            assert isinstance(orchestrator["config"], AgentConfig)
            assert orchestrator["definition"].tools is not None

    @pytest.mark.asyncio
    async def test_parse_agent_definition_with_tools(self, tmp_path):
        """도구 설정이 있는 에이전트 파싱 테스트"""
        runtime = AgentRuntime()

        # 샘플 Markdown 파일 생성
        agent_file = tmp_path / "test_agent.md"
        agent_file.write_text(get_agent_markdown("orchestrator"), encoding="utf-8")

        # 파싱
        agent_def = await runtime._parse_agent_definition(agent_file)

        # 검증
        assert agent_def.tools is not None
        assert "confluence.search_pages" in agent_def.tools
        assert "confluence.get_page" in agent_def.tools
        assert agent_def.prompt is not None
        assert "orchestrator" in agent_def.prompt.lower()

    @pytest.mark.asyncio
    async def test_parse_agent_definition_no_config(self, tmp_path):
        """설정이 없는 에이전트 파싱 테스트 (fallback)"""
        runtime = AgentRuntime()

        # 설정 없는 Markdown 파일 생성
        agent_file = tmp_path / "no_config_agent.md"
        agent_file.write_text(get_agent_markdown("no_config"), encoding="utf-8")

        # 파싱
        agent_def = await runtime._parse_agent_definition(agent_file)

        # 검증: tools가 None (모든 도구 허용)
        assert agent_def.tools is None
        assert agent_def.prompt is not None

    @pytest.mark.asyncio
    async def test_parse_agent_definition_invalid_json(self, tmp_path):
        """잘못된 JSON 설정 처리 테스트"""
        runtime = AgentRuntime()

        # 잘못된 JSON이 있는 Markdown 파일 생성
        agent_file = tmp_path / "invalid_json_agent.md"
        agent_file.write_text(get_agent_markdown("invalid_json"), encoding="utf-8")

        # 파싱 (예외 발생 없이 fallback)
        agent_def = await runtime._parse_agent_definition(agent_file)

        # 검증: tools가 None (파싱 실패 시 기본값)
        assert agent_def.tools is None

    @pytest.mark.asyncio
    async def test_load_agents_file_not_found(self, mock_env, tmp_path, caplog):
        """에이전트 파일이 없을 때 경고 로그 테스트"""
        runtime = AgentRuntime()

        # 존재하지 않는 디렉토리
        non_existent_dir = tmp_path / "non_existent"

        with patch("backend.agent_runtime.runner.Path") as MockPath:
            MockPath.return_value = non_existent_dir

            # _load_agents 호출
            await runtime._load_agents()

            # 에이전트가 로드되지 않음
            assert len(runtime.agents) == 0


class TestMCPServerConnection:
    """MCP 서버 연동 테스트"""

    @pytest.mark.asyncio
    async def test_connect_mcp_servers_success(self, mock_env, mock_confluence_mcp):
        """MCP 서버 연결 성공 테스트"""
        runtime = AgentRuntime()

        with patch("backend.agent_runtime.runner.ConfluenceMCP") as MockConfluenceMCP:
            MockConfluenceMCP.return_value = mock_confluence_mcp

            # MCP 서버 연결
            servers = await runtime._connect_mcp_servers()

            # 검증
            assert "confluence" in servers
            assert servers["confluence"] is not None

    @pytest.mark.asyncio
    async def test_connect_mcp_servers_missing_credentials(self, monkeypatch):
        """환경변수 없을 때 빈 딕셔너리 반환 테스트"""
        # 환경변수 제거
        monkeypatch.delenv("CONFLUENCE_BASE_URL", raising=False)
        monkeypatch.delenv("CONFLUENCE_API_TOKEN", raising=False)

        runtime = AgentRuntime()

        with patch("backend.agent_runtime.runner.ConfluenceMCP") as MockConfluenceMCP:
            # 예외 발생 시뮬레이션
            MockConfluenceMCP.side_effect = Exception("Missing credentials")

            # MCP 서버 연결 (예외 처리로 빈 딕셔너리 반환)
            servers = await runtime._connect_mcp_servers()

            # 검증: 빈 딕셔너리 반환
            assert servers == {}


class TestSessionManagement:
    """세션 관리 테스트"""

    @pytest.mark.asyncio
    async def test_create_session(self, mock_env, mock_claude_sdk_client):
        """세션 생성 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        with patch("backend.agent_runtime.runner.ClaudeSDKClient") as MockClient:
            MockClient.return_value = mock_claude_sdk_client

            # 세션 생성
            session_id = await runtime.create_session(
                agent_id="orchestrator",
                user_id="test_user"
            )

            # 검증
            assert session_id is not None
            assert session_id in runtime.sessions
            assert runtime.sessions[session_id]["agent_id"] == "orchestrator"
            assert runtime.sessions[session_id]["user_id"] == "test_user"

    @pytest.mark.asyncio
    async def test_resume_session_success(self, mock_env):
        """세션 재개 성공 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        # 세션 미리 생성
        session_id = "test-session-id"
        runtime.sessions[session_id] = {
            "agent_id": "orchestrator",
            "user_id": "test_user",
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "client": MagicMock()
        }

        # 세션 재개
        session = await runtime.resume_session(session_id)

        # 검증
        assert session is not None
        assert session["agent_id"] == "orchestrator"
        # last_activity가 업데이트됨
        assert session["last_activity"] > session["created_at"]

    @pytest.mark.asyncio
    async def test_resume_session_not_found(self, mock_env):
        """존재하지 않는 세션 재개 시 예외 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        # 존재하지 않는 세션 ID
        with pytest.raises(KeyError):
            await runtime.resume_session("non-existent-session-id")

    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(self, mock_env):
        """1시간 타임아웃 세션 삭제 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        # 오래된 세션 생성 (2시간 전)
        old_session_id = "old-session"
        runtime.sessions[old_session_id] = {
            "agent_id": "orchestrator",
            "user_id": "test_user",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
            "last_activity": datetime.now(timezone.utc) - timedelta(hours=2),
            "client": MagicMock()
        }

        # 최근 세션 생성 (10분 전)
        recent_session_id = "recent-session"
        runtime.sessions[recent_session_id] = {
            "agent_id": "external_scout",
            "user_id": "test_user",
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=10),
            "last_activity": datetime.now(timezone.utc) - timedelta(minutes=10),
            "client": MagicMock()
        }

        # 정리 실행
        await runtime._cleanup_old_sessions()

        # 검증: 오래된 세션은 삭제, 최근 세션은 유지
        assert old_session_id not in runtime.sessions
        assert recent_session_id in runtime.sessions


class TestWorkflowRouting:
    """워크플로 라우팅 테스트"""

    @pytest.mark.asyncio
    async def test_get_workflow_handler_wf01(self, mock_env):
        """WF-01 핸들러 반환 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        # WF-01 핸들러 가져오기
        handler = await runtime.get_workflow_handler("WF-01")

        # 검증
        assert handler is not None
        assert callable(handler)

    @pytest.mark.asyncio
    async def test_run_workflow_unknown(self, mock_env):
        """알 수 없는 워크플로 예외 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        # 알 수 없는 워크플로
        with pytest.raises(ValueError, match="Unknown workflow"):
            await runtime.run_workflow("WF-99", {})


class TestToolExtraction:
    """도구 추출 헬퍼 메서드 테스트"""

    def test_extract_tools_with_valid_json(self):
        """유효한 JSON에서 도구 추출 테스트"""
        runtime = AgentRuntime()

        markdown = """
        ## Configuration

        ```json
        {
          "tools": ["tool1", "tool2", "tool3"]
        }
        ```
        """

        tools = runtime._extract_tools_from_markdown(markdown)

        assert tools is not None
        assert len(tools) == 3
        assert "tool1" in tools

    def test_extract_tools_with_allowed_tools_key(self):
        """allowed_tools 키 사용 시 도구 추출 테스트"""
        runtime = AgentRuntime()

        markdown = """
        ## Configuration

        ```json
        {
          "allowed_tools": ["confluence.search_pages"]
        }
        ```
        """

        tools = runtime._extract_tools_from_markdown(markdown)

        assert tools is not None
        assert "confluence.search_pages" in tools

    def test_extract_tools_no_config(self):
        """설정이 없을 때 None 반환 테스트"""
        runtime = AgentRuntime()

        markdown = """
        # Test Agent

        No configuration section.
        """

        tools = runtime._extract_tools_from_markdown(markdown)

        assert tools is None

    def test_extract_model_from_markdown(self):
        """모델 추출 테스트"""
        runtime = AgentRuntime()

        markdown = """
        ## Configuration

        ```json
        {
          "model": "claude-opus-4"
        }
        ```
        """

        model = runtime._extract_model_from_markdown(markdown)

        assert model == "claude-opus-4"
