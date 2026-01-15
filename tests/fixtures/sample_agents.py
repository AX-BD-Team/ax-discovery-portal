"""
샘플 에이전트 정의

테스트용 AgentDefinition 객체들
"""

from backend.agent_runtime.runner import AgentDefinition


def get_orchestrator_agent() -> AgentDefinition:
    """Orchestrator 에이전트 정의"""
    return AgentDefinition(
        name="orchestrator",
        prompt="You are the orchestrator agent...",
        tools=["confluence.search_pages", "confluence.get_page"],
    )


def get_external_scout_agent() -> AgentDefinition:
    """External Scout 에이전트 정의"""
    return AgentDefinition(
        name="external_scout", prompt="You are the external scout agent...", tools=[]
    )


def get_scorecard_evaluator_agent() -> AgentDefinition:
    """Scorecard Evaluator 에이전트 정의"""
    return AgentDefinition(
        name="scorecard_evaluator",
        prompt="You are the scorecard evaluator agent...",
        tools=["confluence.create_page"],
    )


def get_brief_writer_agent() -> AgentDefinition:
    """Brief Writer 에이전트 정의"""
    return AgentDefinition(
        name="brief_writer",
        prompt="You are the brief writer agent...",
        tools=["confluence.create_page", "confluence.update_page"],
    )


def get_confluence_sync_agent() -> AgentDefinition:
    """Confluence Sync 에이전트 정의"""
    return AgentDefinition(
        name="confluence_sync",
        prompt="You are the confluence sync agent...",
        tools=["confluence.search_pages", "confluence.update_page", "confluence.append_to_page"],
    )


def get_governance_agent() -> AgentDefinition:
    """Governance 에이전트 정의"""
    return AgentDefinition(name="governance", prompt="You are the governance agent...", tools=[])


def get_all_sample_agents() -> dict[str, AgentDefinition]:
    """모든 샘플 에이전트 반환"""
    return {
        "orchestrator": get_orchestrator_agent(),
        "external_scout": get_external_scout_agent(),
        "scorecard_evaluator": get_scorecard_evaluator_agent(),
        "brief_writer": get_brief_writer_agent(),
        "confluence_sync": get_confluence_sync_agent(),
        "governance": get_governance_agent(),
    }
