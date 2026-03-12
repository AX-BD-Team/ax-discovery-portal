"""Stub Agent Adapter — API 호출 없이 하드코딩된 응답 반환"""

import asyncio

from backend.evals.adapters.base import AdapterResult, AgentAdapterBase
from backend.evals.models.configs import AgentConfig


class StubAdapter(AgentAdapterBase):
    """Stub 어댑터 (CI/테스트용)"""

    async def run(self, prompt: str, agent_config: AgentConfig) -> AdapterResult:
        await asyncio.sleep(0.05)

        return AdapterResult(
            success=True,
            output="[Stub] 에이전트 실행 완료",
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "[Stub 응답] 에이전트 실행이 완료되었습니다."},
            ],
            n_turns=1,
            cost_usd=0.001,
            total_tokens=150,
            input_tokens=100,
            output_tokens=50,
            model=agent_config.model or "stub",
            stop_reason="end_turn",
        )

    @property
    def adapter_name(self) -> str:
        return "stub"
