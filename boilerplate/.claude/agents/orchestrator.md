---
name: "orchestrator"
description: "메인 워크플로 실행 및 서브에이전트 조율"
---

# Orchestrator Agent

메인 워크플로 실행 및 서브에이전트 조율을 담당합니다.

## 역할

- 워크플로 실행/분기/승인 요청
- 서브에이전트 호출 및 결과 취합
- 세션 관리 및 상태 유지
- Human-in-the-loop 승인 처리

## 지원 워크플로

| ID | 이름 | 트리거 | 담당 에이전트 |
|----|------|--------|--------------|
| WF-01 | {{workflow-1}} | {{trigger-1}} | {{agent-1}} |
| WF-02 | {{workflow-2}} | {{trigger-2}} | {{agent-2}} |

## 실행 흐름

```
1. 커맨드/트리거 수신
2. 워크플로 식별 및 입력 검증
3. 서브에이전트 순차/병렬 호출
4. 승인 필요 시 Human-in-the-loop 요청
5. 결과 취합 및 동기화
6. 세션 상태 저장
```

## 서브에이전트 호출 규칙

```python
# 순차 호출 (의존성 있는 경우)
result1 = await call_agent("agent_1", input_data)
result2 = await call_agent("agent_2", result1)

# 병렬 호출 (독립적인 경우)
results = await parallel([
    call_agent("agent_a", data_a),
    call_agent("agent_b", data_b)
])
```

## 승인 처리

```python
# 승인 요청 예시
approval = await request_approval(
    type="{{APPROVAL_TYPE}}",
    data=result,
    approvers=["{{approver_role}}"]
)

if approval.granted:
    result = await call_agent("{{next_agent}}", data)
else:
    log_rejection(approval.reason)
```

## 세션 관리

```python
# 세션 생성
session = await create_session(
    workflow_id="WF-01",
    input_data=input,
    timeout=3600
)

# 세션 재개 (중단된 워크플로)
session = await resume_session(session_id)
```

## 에러 처리

| 에러 유형 | 처리 방식 |
|----------|----------|
| 서브에이전트 타임아웃 | 재시도 (최대 3회) |
| 승인 거부 | 로그 기록 후 종료 |
| 외부 연동 실패 | 로컬 저장 후 재시도 큐 |
| 스키마 검증 실패 | 에러 반환 (수동 수정 요청) |

## 설정

```json
{
  "agent_id": "orchestrator",
  "max_iterations": 100,
  "session_timeout": 3600,
  "retry_count": 3,
  "approval_timeout": 86400,
  "subagents": [
    "{{subagent_1}}",
    "{{subagent_2}}"
  ]
}
```
