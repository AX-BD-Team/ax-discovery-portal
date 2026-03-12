"""Agent Adapter 추상 인터페이스"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from backend.evals.models.configs import AgentConfig


@dataclass
class AdapterResult:
    """Adapter 실행 결과"""

    success: bool
    output: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    n_turns: int = 0
    cost_usd: float = 0.0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model: str | None = None
    stop_reason: str | None = None


class AgentAdapterBase(ABC):
    """Agent adapter 추상 클래스"""

    @abstractmethod
    async def run(self, prompt: str, agent_config: AgentConfig) -> AdapterResult:
        """에이전트 실행

        Args:
            prompt: 에이전트에게 전달할 프롬프트
            agent_config: 에이전트 설정

        Returns:
            AdapterResult
        """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """어댑터 이름"""
