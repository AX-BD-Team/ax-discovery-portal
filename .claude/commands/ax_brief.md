# /ax:brief Command

Scorecard 통과 Signal을 1-Page Opportunity Brief로 변환합니다.

## 사용법

```
/ax:brief --signal-id <id> [--auto] [--owner <name>]
```

## 인자

| 인자 | 필수 | 설명 | 예시 |
|------|------|------|------|
| `--signal-id` | ✅ | Signal ID | SIG-2025-001 |
| `--auto` | | 자동 채움 모드 | |
| `--owner` | | Brief 담당자 | 홍길동 |

## 실행 워크플로

**WF-02/WF-03의 Brief 생성 단계**

```
1. Signal + Scorecard 로드
2. BriefWriter Agent 호출
3. 템플릿 필드 자동 채움
4. 수동 입력 필드 프롬프트
5. (승인 후) Confluence 페이지 생성
6. Play DB 업데이트
```

## 출력

```
📝 Brief 생성 중...

📋 Signal: SIG-2025-001
📊 Scorecard: 75점 (GO)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brief 초안 (자동 채움)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 제목: 콜센터 AHT 최적화 AI 솔루션

👥 Customer
- Segment: 금융 콜센터
- Buyer Role: [입력 필요]
- Account: [입력 필요]

❗ Problem
- Pain: 평균 통화 시간 8분으로 고객 불만 및 인건비 증가
- Why Now: AI 도입 예산 확보, 경쟁사 도입 사례 증가

💡 Solution Hypothesis
- Approach: [입력 필요]
- Integration Points: [입력 필요]

📊 KPIs
- AHT 15% 감소
- FCR 10% 향상

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ 누락 필드를 입력해주세요:

1. Buyer Role (의사결정자): 
```

## 승인 플로우

```
Brief 초안 생성 완료

🔐 Brief 생성 승인 요청
- 요청자: brief_writer
- Signal: SIG-2025-001
- 총점: 75점

승인자에게 알림이 전송되었습니다.
승인 대기 중... (timeout: 24h)

[승인됨]

✅ Brief 생성 완료!

📄 Brief ID: BRF-2025-001
🔗 Confluence: https://confluence.../BRF-2025-001
📂 Play DB 업데이트됨

➡️ '/ax:sprint --brief-id BRF-2025-001' 명령으로 Validation Sprint를 시작할 수 있습니다.
```

## 에러 처리

| 에러 | 메시지 | 해결 방법 |
|------|--------|----------|
| Scorecard 없음 | "먼저 Scorecard 평가가 필요합니다" | /ax:triage 실행 |
| GO 아님 | "GO 판정이 아닌 Signal입니다" | PIVOT/HOLD 안내 |
| 승인 거부 | "Brief 생성이 거부되었습니다" | 사유 확인 |

## 관련 커맨드

- `/ax:triage --signal-id <id>` - Scorecard 평가
- `/ax:sprint --brief-id <id>` - Validation Sprint 시작
