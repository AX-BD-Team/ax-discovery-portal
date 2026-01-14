"""
PostToolUse Hook - 도구 실행 후 결과 처리 및 감사 로그

이 훅은 모든 MCP 도구 호출 후에 실행되어:
1. 결과 감사 로그 기록
2. 에러 처리 및 알림
3. 메트릭 수집
"""

import json
from datetime import datetime
from typing import Any
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    data: Any
    error: str | None = None
    duration_ms: int = 0


async def log_audit_result(
    tool: str,
    params: dict[str, Any],
    result: ToolResult,
    context: dict[str, Any]
) -> None:
    """도구 실행 결과 감사 로그"""
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "tool": tool,
        "params": params,
        "result": {
            "success": result.success,
            "data_summary": _summarize_data(result.data),
            "error": result.error
        },
        "duration_ms": result.duration_ms,
        "agent_id": context.get("agent_id"),
        "session_id": context.get("session_id"),
        "user": context.get("user")
    }
    
    # TODO: 실제 로그 저장 (DB/파일)
    print(f"[AUDIT_RESULT] {json.dumps(audit_entry, ensure_ascii=False)}")


def _summarize_data(data: Any, max_length: int = 200) -> str:
    """데이터 요약 (로그 크기 제한)"""
    if data is None:
        return "null"
    
    data_str = json.dumps(data, ensure_ascii=False)
    if len(data_str) > max_length:
        return data_str[:max_length] + "..."
    return data_str


async def send_error_notification(
    tool: str,
    error: str,
    context: dict[str, Any]
) -> None:
    """에러 발생 시 알림 전송"""
    # TODO: Teams/Slack 알림 구현
    print(f"[ERROR_NOTIFICATION] Tool: {tool}, Error: {error}")


async def collect_metrics(
    tool: str,
    duration_ms: int,
    success: bool
) -> None:
    """메트릭 수집"""
    # TODO: Prometheus/Datadog 연동
    print(f"[METRIC] tool={tool} duration_ms={duration_ms} success={success}")


async def post_tool_use(
    tool_name: str,
    params: dict[str, Any],
    result: ToolResult,
    context: dict[str, Any]
) -> None:
    """
    도구 실행 후 훅
    
    Args:
        tool_name: 호출한 도구 이름
        params: 도구 파라미터
        result: 도구 실행 결과
        context: 실행 컨텍스트
    """
    # 1. 감사 로그 기록
    await log_audit_result(tool_name, params, result, context)
    
    # 2. 에러 처리
    if not result.success:
        await send_error_notification(tool_name, result.error or "Unknown error", context)
    
    # 3. 메트릭 수집
    await collect_metrics(tool_name, result.duration_ms, result.success)
    
    # 4. 특정 도구별 후처리
    await handle_specific_tools(tool_name, params, result, context)


async def handle_specific_tools(
    tool_name: str,
    params: dict[str, Any],
    result: ToolResult,
    context: dict[str, Any]
) -> None:
    """특정 도구별 후처리 로직"""
    
    # Confluence 페이지 생성 성공 시
    if tool_name == "confluence.create_page" and result.success:
        page_url = result.data.get("url")
        print(f"[INFO] Confluence page created: {page_url}")
        
        # Play DB 업데이트 트리거
        # await trigger_play_db_update(params, result.data)
    
    # Brief 생성 성공 시
    if "brief" in tool_name.lower() and result.success:
        brief_id = result.data.get("brief_id")
        print(f"[INFO] Brief created: {brief_id}")
        
        # Confluence Sync 트리거
        # await trigger_confluence_sync(brief_id)


# Claude Agent SDK 훅 등록
def register_hooks(agent):
    """에이전트에 훅 등록"""
    agent.add_hook("post_tool_use", post_tool_use)
