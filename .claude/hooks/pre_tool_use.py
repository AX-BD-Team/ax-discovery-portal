"""
PreToolUse Hook - 도구 실행 전 권한 검사 및 승인 처리

이 훅은 모든 MCP 도구 호출 전에 실행되어:
1. 권한 규칙 검사
2. 필요 시 승인 요청
3. 감사 로그 기록
"""

import re
import json
from datetime import datetime
from typing import Any
from dataclasses import dataclass
from enum import Enum


class PermissionMode(Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"
    LOG = "log"


@dataclass
class PermissionRule:
    pattern: str
    mode: PermissionMode
    approvers: list[str] | None = None
    description: str = ""


@dataclass
class HookResult:
    allowed: bool
    reason: str | None = None
    
    @classmethod
    def allow(cls) -> "HookResult":
        return cls(allowed=True)
    
    @classmethod
    def deny(cls, reason: str) -> "HookResult":
        return cls(allowed=False, reason=reason)


# 권한 규칙 정의
PERMISSION_RULES = [
    # Confluence 쓰기 작업 - 승인 필요
    PermissionRule(
        pattern=r"confluence\.create_page",
        mode=PermissionMode.ASK,
        approvers=["bd_lead", "owner"],
        description="Confluence 페이지 생성"
    ),
    PermissionRule(
        pattern=r"confluence\.update_page",
        mode=PermissionMode.ASK,
        approvers=["owner"],
        description="Confluence 페이지 수정"
    ),
    PermissionRule(
        pattern=r"confluence\.append_to_page",
        mode=PermissionMode.LOG,
        description="Confluence 페이지 내용 추가"
    ),
    
    # DB 작업
    PermissionRule(
        pattern=r"confluence\.db_upsert_row",
        mode=PermissionMode.LOG,
        description="Confluence DB 행 업데이트"
    ),
    PermissionRule(
        pattern=r"confluence\.db_delete_row",
        mode=PermissionMode.DENY,
        description="Confluence DB 행 삭제 (차단)"
    ),
    
    # 외부 API
    PermissionRule(
        pattern=r"external\..*",
        mode=PermissionMode.LOG,
        description="외부 API 호출"
    ),
    
    # 읽기 작업 - 허용
    PermissionRule(
        pattern=r"confluence\.(search|get|query).*",
        mode=PermissionMode.ALLOW,
        description="Confluence 읽기 작업"
    ),
]


def find_matching_rule(tool_name: str) -> PermissionRule | None:
    """도구 이름에 매칭되는 권한 규칙 찾기"""
    for rule in PERMISSION_RULES:
        if re.match(rule.pattern, tool_name):
            return rule
    return None


async def request_approval(
    tool: str,
    params: dict[str, Any],
    approvers: list[str],
    timeout: int = 86400
) -> dict[str, Any]:
    """
    승인 요청 (실제 구현에서는 Teams/Slack 연동)
    
    Returns:
        {"granted": bool, "approver": str, "reason": str}
    """
    # TODO: Teams/Slack 연동 구현
    # 현재는 자동 승인 (개발용)
    return {
        "granted": True,
        "approver": approvers[0] if approvers else "system",
        "reason": "Auto-approved (development mode)"
    }


async def log_audit(
    tool: str,
    params: dict[str, Any],
    result: str,
    context: dict[str, Any]
) -> None:
    """감사 로그 기록"""
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "tool": tool,
        "params": params,
        "result": result,
        "agent_id": context.get("agent_id"),
        "session_id": context.get("session_id"),
        "user": context.get("user")
    }
    
    # TODO: 실제 로그 저장 (DB/파일)
    print(f"[AUDIT] {json.dumps(audit_entry, ensure_ascii=False)}")


async def pre_tool_use(
    tool_name: str,
    params: dict[str, Any],
    context: dict[str, Any]
) -> HookResult:
    """
    도구 실행 전 훅
    
    Args:
        tool_name: 호출할 도구 이름
        params: 도구 파라미터
        context: 실행 컨텍스트 (agent_id, session_id, user 등)
    
    Returns:
        HookResult: 허용/거부 결과
    """
    # 1. 매칭되는 규칙 찾기
    rule = find_matching_rule(tool_name)
    
    if rule is None:
        # 규칙 없으면 기본 허용 (로그만)
        await log_audit(tool_name, params, "ALLOWED_DEFAULT", context)
        return HookResult.allow()
    
    # 2. 모드별 처리
    if rule.mode == PermissionMode.DENY:
        await log_audit(tool_name, params, "DENIED", context)
        return HookResult.deny(
            reason=f"Tool '{tool_name}' is not allowed: {rule.description}"
        )
    
    elif rule.mode == PermissionMode.ASK:
        # 승인 요청
        approval = await request_approval(
            tool=tool_name,
            params=params,
            approvers=rule.approvers or []
        )
        
        if not approval["granted"]:
            await log_audit(tool_name, params, "REJECTED", context)
            return HookResult.deny(
                reason=f"Approval rejected: {approval.get('reason', 'No reason')}"
            )
        
        await log_audit(tool_name, params, f"APPROVED_BY_{approval['approver']}", context)
        return HookResult.allow()
    
    elif rule.mode == PermissionMode.LOG:
        await log_audit(tool_name, params, "ALLOWED_LOGGED", context)
        return HookResult.allow()
    
    else:  # ALLOW
        return HookResult.allow()


# Claude Agent SDK 훅 등록
def register_hooks(agent):
    """에이전트에 훅 등록"""
    agent.add_hook("pre_tool_use", pre_tool_use)
