---
name: "{{command-name}}"
description: "{{command-description}}"
---

# /{{command-name}} Command

{{command-description}}

## 사용법

```
/{{command-name}} [options] [arguments]
```

## 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--option-1` | {{option-1-description}} | {{default-1}} |
| `--option-2` | {{option-2-description}} | {{default-2}} |

## 예시

```bash
# 기본 실행
/{{command-name}}

# 옵션 적용
/{{command-name}} --option-1 value
```

## 실행 흐름

1. **입력 검증**: 인자 및 옵션 유효성 검사
2. **워크플로 실행**: {{workflow-description}}
3. **결과 반환**: {{result-description}}

## 연계 Skill

- **{{skill-name}}**: {{skill-role}}

## 출력 형식

```json
{
  "status": "success | error",
  "message": "{{result-message}}",
  "data": {}
}
```
