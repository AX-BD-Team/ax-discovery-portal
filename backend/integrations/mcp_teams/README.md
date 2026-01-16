# Teams MCP Server

Microsoft Teams 연동을 위한 MCP 서버

## 기능

- **Incoming Webhook**을 통한 메시지 전송
- **Adaptive Card** 지원
- **승인 요청/응답** 카드
- **KPI Digest** 리포트 카드

## 환경 변수

```bash
# 필수
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxxxx

# 선택
TEAMS_CHANNEL_NAME=AX-BD-Alerts  # 기본값
```

## Teams Incoming Webhook 설정 방법

1. Teams 채널에서 **커넥터** 메뉴 열기
2. **Incoming Webhook** 검색 및 추가
3. Webhook 이름 설정 (예: "AX Discovery Portal")
4. 생성된 Webhook URL을 `TEAMS_WEBHOOK_URL` 환경변수에 설정

## Tools (5개)

| 도구명 | 설명 | 필수 파라미터 |
|--------|------|---------------|
| `teams.send_message` | 텍스트 메시지 전송 | `text` |
| `teams.send_notification` | 알림 전송 (색상 강조) | `text`, `title` |
| `teams.send_card` | Adaptive Card 전송 | `card` |
| `teams.request_approval` | 승인 요청 카드 전송 | `title`, `description`, `requester`, `item_id` |
| `teams.send_kpi_digest` | KPI Digest 카드 전송 | `period`, `metrics` |

## 사용 예시

### 메시지 전송
```python
from backend.integrations.mcp_teams.server import TeamsMCP

teams = TeamsMCP()
await teams.send_message(
    text="새로운 Brief가 생성되었습니다.",
    title="Brief 알림"
)
```

### 알림 전송 (색상 강조)
```python
await teams.send_notification(
    text="Signal 점수가 80점을 넘었습니다.",
    title="High-Value Signal 감지",
    level="success",  # info, success, warning, error
    facts={"Signal ID": "SIG-001", "점수": "85점"}
)
```

### 승인 요청
```python
await teams.request_approval(
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
await teams.send_kpi_digest(
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

## Adaptive Card 직접 전송

```python
card = {
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.4",
    "body": [
        {"type": "TextBlock", "text": "커스텀 카드", "weight": "Bolder"}
    ]
}
await teams.send_card(card)
```

## 알림 레벨별 색상

| Level | 색상 | 아이콘 | 용도 |
|-------|------|--------|------|
| `info` | 파랑 (#0076D7) | ℹ️ | 일반 정보 |
| `success` | 초록 (#28A745) | ✅ | 성공/완료 |
| `warning` | 노랑 (#FFC107) | ⚠️ | 주의/경고 |
| `error` | 빨강 (#DC3545) | ❌ | 오류/실패 |

## Status

✅ 구현 완료 (v0.4.0)
