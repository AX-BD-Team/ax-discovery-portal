"""
Agent Runtime Runner 단위 테스트

backend/agent_runtime/runner.py 테스트
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agent_runtime.runner import AgentConfig, AgentRuntime
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
    async def test_connect_mcp_servers_method_exists(self, mock_env):
        """_connect_mcp_servers 메서드 존재 확인 테스트"""
        runtime = AgentRuntime()

        # 메서드 존재 확인
        assert hasattr(runtime, "_connect_mcp_servers")
        assert callable(runtime._connect_mcp_servers)

    @pytest.mark.asyncio
    async def test_connect_mcp_servers_mocked(self, mock_env):
        """MCP 서버 연결 Mock 테스트"""
        runtime = AgentRuntime()

        # _connect_mcp_servers를 Mock으로 대체
        with patch.object(
            runtime, "_connect_mcp_servers", return_value={"confluence": MagicMock()}
        ):
            servers = await runtime._connect_mcp_servers()

            # 검증: dict 반환
            assert isinstance(servers, dict)
            assert "confluence" in servers


class TestSessionManagement:
    """세션 관리 테스트"""

    @pytest.mark.asyncio
    async def test_create_session(self, mock_env):
        """세션 생성 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        # MCP 서버 연결 Mock
        with patch.object(runtime, "_connect_mcp_servers", return_value={}):
            # 세션 생성 (새 시그니처: workflow_id, input_data)
            session_id = await runtime.create_session(
                workflow_id="WF-01", input_data={"test": "data"}
            )

            # 검증
            assert session_id is not None
            assert session_id in runtime.sessions
            assert runtime.sessions[session_id]["workflow_id"] == "WF-01"
            assert runtime.sessions[session_id]["input_data"] == {"test": "data"}
            assert runtime.sessions[session_id]["status"] == "created"

    @pytest.mark.asyncio
    async def test_resume_session_success(self, mock_env):
        """세션 재개 성공 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        # 세션 미리 생성
        session_id = "test-session-id"
        runtime.sessions[session_id] = {
            "workflow_id": "WF-01",
            "input_data": {},
            "status": "created",
            "client": MagicMock(),
            "created_at": asyncio.get_event_loop().time(),
        }

        # 세션 재개
        session = await runtime.resume_session(session_id)

        # 검증
        assert session is not None
        assert session["workflow_id"] == "WF-01"
        assert session["status"] == "resumed"

    @pytest.mark.asyncio
    async def test_resume_session_not_found(self, mock_env):
        """존재하지 않는 세션 재개 시 예외 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        # 존재하지 않는 세션 ID (ValueError 발생)
        with pytest.raises(ValueError, match="Session not found"):
            await runtime.resume_session("non-existent-session-id")

    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(self, mock_env):
        """1시간 타임아웃 세션 삭제 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        current_time = asyncio.get_event_loop().time()

        # 오래된 세션 생성 (2시간 전 = 7200초 전)
        old_session_id = "old-session"
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()
        runtime.sessions[old_session_id] = {
            "workflow_id": "WF-01",
            "input_data": {},
            "status": "created",
            "created_at": current_time - 7200,  # 2시간 전
            "client": mock_client,
        }

        # 최근 세션 생성 (10분 전 = 600초 전)
        recent_session_id = "recent-session"
        runtime.sessions[recent_session_id] = {
            "workflow_id": "WF-02",
            "input_data": {},
            "status": "created",
            "created_at": current_time - 600,  # 10분 전
            "client": MagicMock(),
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

        # _get_workflow_handler 호출 (private 메서드)
        handler = runtime._get_workflow_handler("WF-01")

        # 검증
        assert handler is not None
        assert callable(handler)

    @pytest.mark.asyncio
    async def test_run_workflow_unknown(self, mock_env):
        """알 수 없는 워크플로 예외 테스트"""
        runtime = AgentRuntime()
        await runtime.initialize()

        # MCP 서버 연결 Mock
        with patch.object(runtime, "_connect_mcp_servers", return_value={}):
            # 알 수 없는 워크플로
            with pytest.raises(ValueError, match="Unknown workflow"):
                await runtime.run_workflow("WF-99", {})


class TestToolExtraction:
    """도구 추출 헬퍼 메서드 테스트"""

    def test_extract_tools_with_valid_json(self):
        """유효한 JSON에서 도구 추출 테스트"""
        runtime = AgentRuntime()

        # JSON 블록은 인덴트 없이 작성 (regex 매칭)
        markdown = """## Configuration

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

        markdown = """## Configuration

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

        markdown = """# Test Agent

No configuration section.
"""

        tools = runtime._extract_tools_from_markdown(markdown)

        assert tools is None

    def test_extract_model_from_markdown(self):
        """모델 추출 테스트"""
        runtime = AgentRuntime()

        markdown = """## Configuration

```json
{
  "model": "claude-opus-4"
}
```
"""

        model = runtime._extract_model_from_markdown(markdown)

        assert model == "claude-opus-4"
