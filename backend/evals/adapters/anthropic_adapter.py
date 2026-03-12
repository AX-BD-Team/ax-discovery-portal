"""Anthropic API Agent Adapter — 실제 Claude API 호출"""

import os
from typing import Any

import structlog

from backend.evals.adapters.base import AdapterResult, AgentAdapterBase
from backend.evals.models.configs import AgentConfig

logger = structlog.get_logger()

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AnthropicAdapter(AgentAdapterBase):
    """Anthropic API를 직접 호출하는 어댑터"""

    def __init__(self) -> None:
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다")
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def run(self, prompt: str, agent_config: AgentConfig) -> AdapterResult:
        model = agent_config.model or DEFAULT_MODEL

        logger.info(
            "Anthropic API 호출",
            model=model,
            prompt_length=len(prompt),
            max_turns=agent_config.max_turns,
        )

        system_prompt = agent_config.system_prompt_override or self._build_system_prompt(
            agent_config
        )

        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

        response = await self._client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )

        # 응답 텍스트 추출
        output_text = ""
        for block in response.content:
            if block.type == "text":
                output_text += block.text

        # 토큰 사용량
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        total_tokens = input_tokens + output_tokens
        cost_usd = self._estimate_cost(model, input_tokens, output_tokens)

        logger.info(
            "Anthropic API 응답",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=f"${cost_usd:.4f}",
            stop_reason=response.stop_reason,
        )

        return AdapterResult(
            success=True,
            output=output_text,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": output_text},
            ],
            n_turns=1,
            cost_usd=cost_usd,
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            stop_reason=response.stop_reason,
        )

    @property
    def adapter_name(self) -> str:
        return "anthropic"

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
