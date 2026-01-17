---
name: "governance"
description: "위험 작업 차단, 승인, 감사 로그 담당"
---

# Governance Agent

위험 작업 차단, 승인, 감사 로그를 담당합니다.

## 역할

- 위험 Tool Call 사전 차단
- Human-in-the-loop 승인 처리
- 모든 작업 감사 로그
- 권한 검증

## Permission Rules

```json
{
  "rules": [
    {
      "pattern": "confluence.create_page",
      "mode": "ask",
      "approvers": ["bd_lead", "owner"]
    },
    {
      "pattern": "confluence.update_page",
      "mode": "ask",
      "approvers": ["owner"]
    },
    {
      "pattern": "confluence.db_delete_row",
      "mode": "deny"
    },
    {
      "pattern": "external.*",
      "mode": "log"
    }
  ]
}
```

## Permission Modes

| 모드 | 설명 | 사용 예 |
|------|------|--------|
| `allow` | 즉시 허용 | 읽기 작업 |
| `ask` | 사용자 승인 필요 | 쓰기 작업 |
| `deny` | 항상 차단 | 삭제 작업 |
| `log` | 허용하되 로깅 | 외부 API |

## Hooks

### PreToolUse Hook

```python
async def pre_tool_use(context: ToolContext) -> HookResult:
    tool_name = context.tool_name
    params = context.params
    
    # 1. 규칙 매칭
    rule = find_matching_rule(tool_name)
    
    # 2. 모드별 처리
    if rule.mode == "deny":
        return HookResult.deny(
            reason=f"Tool '{tool_name}' is not allowed"
        )
    
    elif rule.mode == "ask":
        approval = await request_approval(
            tool=tool_name,
            params=params,
            approvers=rule.approvers
        )
        if not approval.granted:
            return HookResult.deny(reason=approval.reason)
    
    # 3. 감사 로그
    await log_tool_call(context, "ALLOWED")
    
    return HookResult.allow()
```

### PostToolUse Hook

```python
async def post_tool_use(context: ToolContext, result: ToolResult):
    # 결과 감사 로그
    await log_audit({
        "tool": context.tool_name,
        "params": context.params,
        "result": result.data,
        "status": result.status,
        "agent_id": context.agent_id,
        "session_id": context.session_id,
        "timestamp": now(),
        "duration_ms": result.duration_ms
    })
```

## 감사 로그 스키마

```json
{
  "log_id": "AUDIT-2025-00001",
  "timestamp": "2025-01-14T10:30:00Z",
  "agent_id": "brief_writer",
  "session_id": "sess_abc123",
  "tool": "confluence.create_page",
  "params": {
    "title": "[Brief] 콜센터 AHT 최적화",
    "space_key": "AXBD"
  },
  "result_status": "SUCCESS",
  "duration_ms": 1250,
  "user": "user@example.com",
  "approval": {
    "required": true,
    "granted": true,
    "approver": "bd_lead@example.com"
  }
}
```

## 승인 플로우

```
1. Tool Call 요청
2. PreToolUse Hook 실행
3. 규칙 매칭 → "ask" 모드
4. 승인 요청 전송 (Teams/Slack/Email)
5. 승인자 응답 대기 (timeout: 24h)
6. 승인 시 → Tool 실행
7. 거부 시 → 로그 기록 후 종료
```

## 알림 채널

```python
async def send_approval_request(request: ApprovalRequest):
    # Teams 카드 전송
    await teams.send_adaptive_card(
        webhook_url=TEAMS_WEBHOOK_URL,
        card={
            "type": "AdaptiveCard",
            "body": [
                {"type": "TextBlock", "text": f"승인 요청: {request.tool}"},
                {"type": "TextBlock", "text": f"요청자: {request.agent_id}"},
                {"type": "FactSet", "facts": format_params(request.params)}
            ],
            "actions": [
                {"type": "Action.Submit", "title": "승인", "data": {"action": "approve"}},
                {"type": "Action.Submit", "title": "거부", "data": {"action": "reject"}}
            ]
        }
    )
```

## 설정

```json
{
  "agent_id": "governance",
  "audit_log_db": "${AUDIT_LOG_DB_URL}",
  "approval_timeout": 86400,
  "notification_channels": ["teams", "email"],
  "default_mode": "ask"
}
```
