"""Agent Adapter 팩토리"""

import os

import structlog

from backend.evals.adapters.base import AgentAdapterBase
from backend.evals.models.configs import AgentConfig

logger = structlog.get_logger()


def create_adapter(agent_config: AgentConfig | None = None) -> AgentAdapterBase:
    """환경 + 설정 기반으로 적절한 adapter 생성

    우선순위:
    1. EVALS_STUB_MODE=true → StubAdapter (명시적 stub 강제)
    2. ANTHROPIC_API_KEY 미설정 → StubAdapter (API 호출 불가)
    3. 그 외 → AnthropicAdapter (실제 API 호출)
    """
    # 1. 명시적 stub 모드
    if os.environ.get("EVALS_STUB_MODE", "").lower() in ("true", "1", "yes"):
        logger.info("Adapter: StubAdapter (EVALS_STUB_MODE=true)")
        from backend.evals.adapters.stub import StubAdapter

        return StubAdapter()

    # 2. API 키 확인
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("Adapter: StubAdapter (ANTHROPIC_API_KEY 미설정)")
        from backend.evals.adapters.stub import StubAdapter

        return StubAdapter()

    # 3. 실제 API 호출
    logger.info("Adapter: AnthropicAdapter (live mode)")
    from backend.evals.adapters.anthropic_adapter import AnthropicAdapter

    return AnthropicAdapter()
