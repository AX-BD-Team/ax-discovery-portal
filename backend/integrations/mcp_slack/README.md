# Slack MCP Server

Slack 연동을 위한 MCP 서버

## 기능

- **Incoming Webhook**을 통한 메시지 전송
- **Block Kit** 지원 (리치 메시지)
- **승인 요청** 메시지
- **KPI Digest** 리포트 메시지

## 환경 변수

```bash
# 필수
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/xxx/xxx

# 선택
SLACK_CHANNEL_NAME=#ax-bd-alerts  # 기본값
```

## Slack Incoming Webhook 설정 방법

### 1단계: Slack 앱 생성

1. https://api.slack.com/apps 접속
2. **Create New App** 클릭
3. **From scratch** 선택
4. 앱 이름: `AX Discovery Portal`
5. 워크스페이스 선택 후 **Create App**

### 2단계: Incoming Webhook 활성화

1. 좌측 메뉴에서 **Incoming Webhooks** 클릭
2. **Activate Incoming Webhooks** 토글 ON
3. **Add New Webhook to Workspace** 클릭
4. 알림 받을 채널 선택 (예: `#ax-bd-alerts`)
5. **Allow** 클릭
6. 생성된 **Webhook URL 복사**

### 3단계: 환경변수 설정

```bash
# .env 파일에 추가
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

## Tools (5개)

| 도구명 | 설명 | 필수 파라미터 |
|--------|------|---------------|
| `slack.send_message` | 텍스트 메시지 전송 | `text` |
| `slack.send_notification` | 알림 전송 (색상 강조) | `text`, `title` |
| `slack.send_blocks` | Block Kit 메시지 전송 | `blocks` |
| `slack.request_approval` | 승인 요청 메시지 전송 | `title`, `description`, `requester`, `item_id` |
| `slack.send_kpi_digest` | KPI Digest 메시지 전송 | `period`, `metrics` |

## 사용 예시

### 메시지 전송
```python
from backend.integrations.mcp_slack.server import SlackMCP

slack = SlackMCP()
await slack.send_message(
    text="새로운 Brief가 생성되었습니다.",
    title="Brief 알림"
)
```

### 알림 전송 (색상 강조)
```python
await slack.send_notification(
    text="Signal 점수가 80점을 넘었습니다.",
    title="High-Value Signal 감지",
    level="success",  # info, success, warning, error
    fields={"Signal ID": "SIG-001", "점수": "85점"}
)
```

### 승인 요청
```python
await slack.request_approval(
    title="Brief 승인 요청",
    description="KT Cloud AI 사업기회 Brief가 작성되었습니다.",
    requester="홍길동",
    item_id="BRF-001",
    item_type="Brief",
    details={"고객사": "KT", "예상 규모": "5억원"}
)
```

### KPI Digest
```python
await slack.send_kpi_digest(
    period="2026-W03",
    metrics={
        "activities": 25,
        "signals": 32,
        "briefs": 8,
        "s2_validated": 3,
        "s3_pilot_ready": 1
    },
    alerts=["Signal→Brief 리드타임 초과 (9일)"],
    top_plays=[
        {"name": "KT Cloud AI", "score": "92"},
        {"name": "신한은행 DX", "score": "88"}
    ]
)
```

## 알림 레벨별 색상

| Level | 색상 | 용도 |
|-------|------|------|
| `info` | 파랑 (#0076D7) | 일반 정보 |
| `success` | 초록 (#28A745) | 성공/완료 |
| `warning` | 노랑 (#FFC107) | 주의/경고 |
| `error` | 빨강 (#DC3545) | 오류/실패 |

## Status

✅ 구현 완료 (v0.4.0)
