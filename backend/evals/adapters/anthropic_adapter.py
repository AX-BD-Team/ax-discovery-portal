"""Anthropic API Agent Adapter — 멀티턴 대화 + 도구 호출 지원"""

import json
import os
from typing import Any

import structlog

from backend.evals.adapters.base import AdapterResult, AgentAdapterBase
from backend.evals.models.configs import AgentConfig

logger = structlog.get_logger()

DEFAULT_MODEL = "claude-sonnet-4-20250514"

# 도구별 시뮬레이션 응답 매핑
_TOOL_SIMULATION_MAP: dict[str, dict[str, Any]] = {
    "confluence_get_page": {
        "page_id": "12345",
        "title": "테스트 페이지",
        "content": "페이지 본문 내용입니다.",
        "status": "current",
    },
    "confluence_create_page": {
        "page_id": "12346",
        "title": "새 페이지",
        "url": "https://wiki.example.com/pages/12346",
        "status": "created",
    },
    "confluence_update_page": {
        "page_id": "12345",
        "version": 2,
        "status": "updated",
    },
    "confluence_search": {
        "results": [
            {"page_id": "12345", "title": "검색 결과 1"},
            {"page_id": "12347", "title": "검색 결과 2"},
        ],
        "total": 2,
    },
    "teams_send_message": {
        "message_id": "msg-001",
        "status": "sent",
        "channel": "general",
    },
}


class AnthropicAdapter(AgentAdapterBase):
    """Anthropic API를 직접 호출하는 어댑터 (멀티턴 + 도구 호출)"""

    def __init__(self) -> None:
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다")
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def run(self, prompt: str, agent_config: AgentConfig) -> AdapterResult:
        model = agent_config.model or DEFAULT_MODEL
        max_turns = agent_config.max_turns
        tools = self._build_tools(agent_config.tools_allowed)

        logger.info(
            "Anthropic API 멀티턴 시작",
            model=model,
            prompt_length=len(prompt),
            max_turns=max_turns,
            tools_count=len(tools),
        )

        system_prompt = agent_config.system_prompt_override or self._build_system_prompt(
            agent_config
        )

        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        all_messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        all_tool_calls: list[dict[str, Any]] = []

        total_input_tokens = 0
        total_output_tokens = 0
        n_turns = 0
        last_stop_reason: str | None = None

        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "system": system_prompt,
        }
        if tools:
            create_kwargs["tools"] = tools

        for _turn in range(max_turns):
            response = await self._client.messages.create(
                messages=messages,
                **create_kwargs,
            )

            # 토큰 누적
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens
            n_turns += 1
            last_stop_reason = response.stop_reason

            # assistant 메시지 직렬화 (content 블록 → 딕셔너리)
            assistant_content = self._serialize_content(response.content)
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_content,
            }
            messages.append(assistant_msg)
            all_messages.append(assistant_msg)

            # tool_use 블록 추출 및 처리
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if response.stop_reason != "tool_use" or not tool_use_blocks:
                # end_turn 또는 도구 호출 없음 → 루프 종료
                break

            # 도구 호출 기록 + tool_result 메시지 생성
            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                all_tool_calls.append({
                    "tool_name": block.name,
                    "tool_input": block.input,
                    "tool_use_id": block.id,
                })

                sim_result = self._simulate_tool_result(block.name)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(sim_result, ensure_ascii=False),
                })

            tool_result_msg: dict[str, Any] = {
                "role": "user",
                "content": tool_results,
            }
            messages.append(tool_result_msg)
            all_messages.append(tool_result_msg)

            logger.debug(
                "도구 호출 턴 완료",
                turn=n_turns,
                tool_calls=[b.name for b in tool_use_blocks],
            )

        # 최종 텍스트 추출 (마지막 assistant 메시지에서)
        output_text = self._extract_text(response.content)
        total_tokens = total_input_tokens + total_output_tokens
        cost_usd = self._estimate_cost(model, total_input_tokens, total_output_tokens)

        logger.info(
            "Anthropic API 멀티턴 완료",
            model=model,
            n_turns=n_turns,
            tool_calls_count=len(all_tool_calls),
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            cost_usd=f"${cost_usd:.4f}",
            stop_reason=last_stop_reason,
        )

        return AdapterResult(
            success=True,
            output=output_text,
            messages=all_messages,
            n_turns=n_turns,
            cost_usd=cost_usd,
            total_tokens=total_tokens,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            tool_calls=all_tool_calls,
            model=model,
            stop_reason=last_stop_reason,
        )

    @property
    def adapter_name(self) -> str:
        return "anthropic"

    def _build_tools(self, tools_allowed: list[str]) -> list[dict[str, Any]]:
        """tools_allowed 리스트에서 Anthropic API 도구 스키마 생성"""
        if not tools_allowed:
            return []

        tools: list[dict[str, Any]] = []
        for tool_name in tools_allowed:
            api_name = tool_name.replace(".", "_")
            tools.append({
                "name": api_name,
                "description": f"{tool_name} 도구",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "입력 파라미터",
                        },
                    },
                    "required": ["query"],
                },
            })
        return tools

    def _simulate_tool_result(self, tool_name: str) -> dict[str, Any]:
        """도구 이름 기반 시뮬레이션 응답 반환"""
        if tool_name in _TOOL_SIMULATION_MAP:
            return _TOOL_SIMULATION_MAP[tool_name]
        return {"status": "ok", "result": "시뮬레이션 결과"}

    def _serialize_content(self, content: Any) -> list[dict[str, Any]]:
        """응답 content 블록을 직렬화 가능한 딕셔너리 리스트로 변환"""
        serialized: list[dict[str, Any]] = []
        for block in content:
            if block.type == "text":
                serialized.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                serialized.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        return serialized

    def _extract_text(self, content: Any) -> str:
        """content 블록에서 텍스트만 추출"""
        parts: list[str] = []
        for block in content:
            if block.type == "text":
                parts.append(block.text)
        return "".join(parts)

    def _build_system_prompt(self, config: AgentConfig) -> str:
        parts = [
            "당신은 AX Discovery Portal의 에이전트입니다.",
        ]
        if config.agent_id:
            parts.append(f"역할: {config.agent_id}")
        if config.tools_allowed:
            parts.append(f"사용 가능 도구: {', '.join(config.tools_allowed)}")
        return "\n".join(parts)

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """모델별 토큰 비용 추정 (USD)"""
        # 2025-05 기준 가격
        rates = {
            "claude-sonnet-4-20250514": (3.0 / 1_000_000, 15.0 / 1_000_000),
            "claude-opus-4-20250514": (15.0 / 1_000_000, 75.0 / 1_000_000),
            "claude-haiku-3-5-20241022": (0.80 / 1_000_000, 4.0 / 1_000_000),
        }
        input_rate, output_rate = rates.get(model, (3.0 / 1_000_000, 15.0 / 1_000_000))
        return input_tokens * input_rate + output_tokens * output_rate
