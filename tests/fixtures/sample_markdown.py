"""
샘플 Markdown 파일 내용

.claude/agents/*.md 파일 내용 샘플
"""

ORCHESTRATOR_MD = """
# Orchestrator Agent

You are the orchestrator agent responsible for coordinating workflows.

## Configuration

```json
{
  "tools": ["confluence.search_pages", "confluence.get_page"]
}
```

## Responsibilities

- Coordinate multi-agent workflows
- Route tasks to appropriate sub-agents
- Aggregate results from sub-agents
"""

EXTERNAL_SCOUT_MD = """
# External Scout Agent

You are the external scout agent for gathering external information.

## Configuration

```json
{
  "tools": []
}
```

## Responsibilities

- Collect seminar information
- Gather market research reports
- Monitor news and trends
"""

SCORECARD_EVALUATOR_MD = """
# Scorecard Evaluator Agent

You are the scorecard evaluator agent for quantitative signal assessment.

## Configuration

```json
{
  "tools": ["confluence.create_page"]
}
```

## Responsibilities

- Evaluate signals on 5 dimensions
- Calculate 100-point scorecard
- Make GO/NO-GO decisions
"""

BRIEF_WRITER_MD = """
# Brief Writer Agent

You are the brief writer agent for creating 1-page opportunity briefs.

## Configuration

```json
{
  "tools": ["confluence.create_page", "confluence.update_page"]
}
```

## Responsibilities

- Generate 1-page briefs
- Create Confluence pages
- Update brief content
"""

CONFLUENCE_SYNC_MD = """
# Confluence Sync Agent

You are the confluence sync agent for database and live doc updates.

## Configuration

```json
{
  "tools": ["confluence.search_pages", "confluence.update_page", "confluence.append_to_page"]
}
```

## Responsibilities

- Sync Play DB
- Update Live docs
- Maintain Action Log
"""

GOVERNANCE_MD = """
# Governance Agent

You are the governance agent for risk management and approval workflows.

## Configuration

```json
{
  "tools": []
}
```

## Responsibilities

- Block dangerous operations
- Request approvals for sensitive actions
- Audit tool usage
"""

# No config example (fallback test)
NO_CONFIG_MD = """
# Test Agent

You are a test agent without config.

This agent should use default configuration.
"""

# Invalid JSON example (fallback test)
INVALID_JSON_MD = """
# Test Agent

You are a test agent with invalid JSON config.

## Configuration

```json
{
  "tools": ["tool1", "tool2"  # Missing closing bracket
}
```
"""


def get_agent_markdown(agent_name: str) -> str:
    """에이전트 이름으로 Markdown 내용 반환"""
    markdown_map = {
        "orchestrator": ORCHESTRATOR_MD,
        "external_scout": EXTERNAL_SCOUT_MD,
        "scorecard_evaluator": SCORECARD_EVALUATOR_MD,
        "brief_writer": BRIEF_WRITER_MD,
        "confluence_sync": CONFLUENCE_SYNC_MD,
        "governance": GOVERNANCE_MD,
        "no_config": NO_CONFIG_MD,
        "invalid_json": INVALID_JSON_MD,
    }
    return markdown_map.get(agent_name, "")
