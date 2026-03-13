"""
Evals Adapter 시스템 통합 단위 테스트

테스트 대상:
- AdapterResult, AgentAdapterBase (base.py)
- StubAdapter (stub.py)
- AnthropicAdapter (anthropic_adapter.py)
- create_adapter (factory.py)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.evals.adapters import AdapterResult, create_adapter
from backend.evals.adapters.base import AgentAdapterBase
from backend.evals.adapters.stub import StubAdapter
from backend.evals.models.configs import AgentConfig

# ============================================================================
# 헬퍼: AgentConfig 기본 생성
# ============================================================================


def _make_config(**overrides: Any) -> AgentConfig:
    defaults: dict[str, Any] = {
        "model": "claude-sonnet-4-20250514",
        "max_turns": 5,
        "tools_allowed": [],
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)


# ============================================================================
# 헬퍼: Anthropic API mock 응답 생성
# ============================================================================


def _make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(tool_id: str, name: str, tool_input: dict[str, Any]) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = tool_input
    return block


def _make_response(
    content: list[MagicMock],
    stop_reason: str = "end_turn",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.stop_reason = stop_reason
    resp.usage = MagicMock()
    resp.usage.input_tokens = input_tokens
    resp.usage.output_tokens = output_tokens
    return resp


# ============================================================================
# 1. StubAdapter 테스트
# ============================================================================


class TestStubAdapter:
    async def test_stub_adapter_run(self) -> None:
        adapter = StubAdapter()
        config = _make_config()
        result = await adapter.run("안녕하세요", config)

        assert isinstance(result, AdapterResult)
        assert result.success is True
        assert isinstance(result.output, str)
        assert len(result.output) > 0

    async def test_stub_adapter_name(self) -> None:
        adapter = StubAdapter()
        assert adapter.adapter_name == "stub"

    async def test_stub_adapter_result_fields(self) -> None:
        adapter = StubAdapter()
        config = _make_config(model="test-model")
        result = await adapter.run("테스트 프롬프트", config)

        assert result.success is True
        assert result.output == "[Stub] 에이전트 실행 완료"
        assert result.n_turns == 1
        assert result.cost_usd == pytest.approx(0.001)
        assert result.total_tokens == 150
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.model == "test-model"
        assert result.stop_reason == "end_turn"
        assert result.tool_calls == []

        # messages 구조 검증
        assert len(result.messages) == 2
        assert result.messages[0]["role"] == "user"
        assert result.messages[0]["content"] == "테스트 프롬프트"
        assert result.messages[1]["role"] == "assistant"

    async def test_stub_adapter_is_base_subclass(self) -> None:
        adapter = StubAdapter()
        assert isinstance(adapter, AgentAdapterBase)


# ============================================================================
# 2. Factory 테스트
# ============================================================================


class TestFactory:
    def test_factory_returns_stub_when_no_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("EVALS_STUB_MODE", raising=False)

        adapter = create_adapter()
        assert isinstance(adapter, StubAdapter)
        assert adapter.adapter_name == "stub"

    def test_factory_returns_stub_when_stub_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EVALS_STUB_MODE", "true")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        adapter = create_adapter()
        assert isinstance(adapter, StubAdapter)

    def test_factory_returns_stub_when_stub_mode_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EVALS_STUB_MODE", "yes")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        adapter = create_adapter()
        assert isinstance(adapter, StubAdapter)

    def test_factory_returns_anthropic_when_api_key_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        monkeypatch.delenv("EVALS_STUB_MODE", raising=False)

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_cls.return_value = MagicMock()

            adapter = create_adapter()

            from backend.evals.adapters.anthropic_adapter import AnthropicAdapter

            assert isinstance(adapter, AnthropicAdapter)
            assert adapter.adapter_name == "anthropic"


# ============================================================================
# 3. AnthropicAdapter 멀티턴 테스트 (Mock 기반)
# ============================================================================


class TestAnthropicAdapterMultiTurn:
    """AnthropicAdapter 테스트 — anthropic 패키지를 mock으로 대체"""

    def _create_adapter_with_mock(self, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, AsyncMock]:
        """API 키 설정 + anthropic.AsyncAnthropic mock 후 인스턴스 반환"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_create = AsyncMock()
        mock_client.messages = MagicMock()
        mock_client.messages.create = mock_create

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_cls.return_value = mock_client

            from backend.evals.adapters.anthropic_adapter import AnthropicAdapter

            adapter = AnthropicAdapter()

        return adapter, mock_create

    async def test_anthropic_adapter_single_turn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter, mock_create = self._create_adapter_with_mock(monkeypatch)

        response = _make_response(
            content=[_make_text_block("단일 턴 응답입니다.")],
            stop_reason="end_turn",
            input_tokens=200,
            output_tokens=80,
        )
        mock_create.return_value = response

        config = _make_config(max_turns=5)
        result = await adapter.run("테스트 질문", config)

        assert result.success is True
        assert result.output == "단일 턴 응답입니다."
        assert result.n_turns == 1
        assert result.stop_reason == "end_turn"
        assert result.tool_calls == []
        mock_create.assert_awaited_once()

    async def test_anthropic_adapter_multi_turn_with_tools(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        adapter, mock_create = self._create_adapter_with_mock(monkeypatch)

        # 1턴: 도구 호출
        tool_block = _make_tool_use_block("toolu_001", "confluence_get_page", {"query": "검색어"})
        response_turn1 = _make_response(
            content=[_make_text_block("페이지를 검색할게요."), tool_block],
            stop_reason="tool_use",
            input_tokens=150,
            output_tokens=60,
        )

        # 2턴: 최종 응답
        response_turn2 = _make_response(
            content=[_make_text_block("검색 결과를 정리했어요.")],
            stop_reason="end_turn",
            input_tokens=300,
            output_tokens=100,
        )

        mock_create.side_effect = [response_turn1, response_turn2]

        config = _make_config(
            tools_allowed=["confluence_get_page"],
            max_turns=10,
        )
        result = await adapter.run("Confluence에서 페이지를 검색해줘", config)

        assert result.success is True
        assert result.n_turns == 2
        assert result.stop_reason == "end_turn"
        assert result.output == "검색 결과를 정리했어요."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool_name"] == "confluence_get_page"
        assert mock_create.await_count == 2

    async def test_anthropic_adapter_max_turns_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter, mock_create = self._create_adapter_with_mock(monkeypatch)

        # 매 턴마다 도구 호출 → max_turns 도달 시 루프 종료
        tool_block = _make_tool_use_block("toolu_loop", "confluence_search", {"query": "반복"})
        response_with_tool = _make_response(
            content=[_make_text_block("검색 중..."), tool_block],
            stop_reason="tool_use",
            input_tokens=100,
            output_tokens=50,
        )

        max_turns = 3
        mock_create.return_value = response_with_tool

        config = _make_config(
            tools_allowed=["confluence_search"],
            max_turns=max_turns,
        )
        result = await adapter.run("무한 검색", config)

        assert result.n_turns == max_turns
        assert mock_create.await_count == max_turns

    async def test_anthropic_adapter_tool_calls_recorded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        adapter, mock_create = self._create_adapter_with_mock(monkeypatch)

        tool1 = _make_tool_use_block("toolu_a", "confluence_get_page", {"query": "page1"})
        tool2 = _make_tool_use_block("toolu_b", "teams_send_message", {"query": "알림"})

        # 1턴: 도구 2개 동시 호출
        response_turn1 = _make_response(
            content=[tool1, tool2],
            stop_reason="tool_use",
            input_tokens=100,
            output_tokens=40,
        )
        # 2턴: 최종 응답
        response_turn2 = _make_response(
            content=[_make_text_block("완료")],
            stop_reason="end_turn",
            input_tokens=200,
            output_tokens=30,
        )
        mock_create.side_effect = [response_turn1, response_turn2]

        config = _make_config(
            tools_allowed=["confluence_get_page", "teams_send_message"],
            max_turns=5,
        )
        result = await adapter.run("작업 실행", config)

        assert len(result.tool_calls) == 2
        tool_names = [tc["tool_name"] for tc in result.tool_calls]
        assert "confluence_get_page" in tool_names
        assert "teams_send_message" in tool_names
        assert result.tool_calls[0]["tool_use_id"] == "toolu_a"
        assert result.tool_calls[1]["tool_use_id"] == "toolu_b"

    async def test_anthropic_adapter_cost_accumulation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        adapter, mock_create = self._create_adapter_with_mock(monkeypatch)

        tool_block = _make_tool_use_block("toolu_cost", "confluence_search", {"query": "test"})

        # 턴1: input=500, output=200
        resp1 = _make_response(
            content=[_make_text_block("검색"), tool_block],
            stop_reason="tool_use",
            input_tokens=500,
            output_tokens=200,
        )
        # 턴2: input=800, output=300
        resp2 = _make_response(
            content=[_make_text_block("완료")],
            stop_reason="end_turn",
            input_tokens=800,
            output_tokens=300,
        )
        mock_create.side_effect = [resp1, resp2]

        config = _make_config(
            tools_allowed=["confluence_search"],
            max_turns=5,
            model="claude-sonnet-4-20250514",
        )
        result = await adapter.run("비용 테스트", config)

        assert result.input_tokens == 500 + 800
        assert result.output_tokens == 200 + 300
        assert result.total_tokens == 1300 + 500
        assert result.cost_usd > 0

        # claude-sonnet-4 비용 계산 검증: (1300 * 3/1M) + (500 * 15/1M)
        expected_cost = 1300 * 3.0 / 1_000_000 + 500 * 15.0 / 1_000_000
        assert result.cost_usd == pytest.approx(expected_cost)


# ============================================================================
# 4. 도구 스키마 테스트
# ============================================================================


class TestToolSchema:
    """AnthropicAdapter의 _build_tools, _simulate_tool_result 테스트"""

    def _create_adapter(self, monkeypatch: pytest.MonkeyPatch) -> Any:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_cls.return_value = MagicMock()

            from backend.evals.adapters.anthropic_adapter import AnthropicAdapter

            return AnthropicAdapter()

    def test_build_tools_from_allowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = self._create_adapter(monkeypatch)
        tools = adapter._build_tools(["confluence_get_page", "teams_send_message"])

        assert len(tools) == 2
        assert tools[0]["name"] == "confluence_get_page"
        assert tools[1]["name"] == "teams_send_message"

        # 스키마 구조 검증
        for tool in tools:
            assert "description" in tool
            assert "input_schema" in tool
            schema = tool["input_schema"]
            assert schema["type"] == "object"
            assert "query" in schema["properties"]

    def test_build_tools_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = self._create_adapter(monkeypatch)
        tools = adapter._build_tools([])
        assert tools == []

    def test_build_tools_dot_to_underscore(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = self._create_adapter(monkeypatch)
        tools = adapter._build_tools(["mcp.confluence.search"])
        assert tools[0]["name"] == "mcp_confluence_search"

    def test_simulate_tool_result_known(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = self._create_adapter(monkeypatch)

        result = adapter._simulate_tool_result("confluence_get_page")
        assert result["page_id"] == "12345"
        assert result["title"] == "테스트 페이지"
        assert "content" in result

    def test_simulate_tool_result_unknown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = self._create_adapter(monkeypatch)

        result = adapter._simulate_tool_result("unknown_tool_xyz")
        assert result["status"] == "ok"
        assert result["result"] == "시뮬레이션 결과"
