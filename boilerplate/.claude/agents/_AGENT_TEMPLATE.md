---
name: "{{agent-id}}"
description: "{{agent-description}}"
---

# {{Agent Name}} Agent

{{agent-description}}을 담당합니다.

## 역할

- {{responsibility-1}}
- {{responsibility-2}}
- {{responsibility-3}}

## 지원 워크플로

| ID | 이름 | 트리거 | 담당 에이전트 |
|----|------|--------|--------------|
| WF-01 | {{workflow-name}} | {{trigger}} | {{agent}} |

## 실행 흐름

```
1. {{step-1}}
2. {{step-2}}
3. {{step-3}}
```

## 입력/출력 스키마

### 입력

```json
{
  "{{input-field}}": "{{input-type}}",
  "context": {}
}
```

### 출력

```json
{
  "status": "success | error",
  "result": {},
  "metadata": {}
}
```

## 에러 처리

| 에러 유형 | 처리 방식 |
|----------|----------|
| {{error-type-1}} | {{handling-1}} |
| {{error-type-2}} | {{handling-2}} |

## 설정

```json
{
  "agent_id": "{{agent-id}}",
  "max_iterations": 100,
  "timeout": 3600,
  "retry_count": 3
}
```

## 연계 에이전트

| Agent | 연계 목적 |
|-------|----------|
| {{related-agent}} | {{purpose}} |

## 사용 예시

```python
# 에이전트 호출 예시
result = await call_agent("{{agent-id}}", {
    "input": "...",
    "context": {}
})
```
