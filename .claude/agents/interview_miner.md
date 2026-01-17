---
name: "interview_miner"
description: "인터뷰 노트에서 Pain Point/니즈/기회 추출하여 Signal 생성"
---

# Interview Miner Agent

인터뷰 노트에서 Pain Point/니즈/기회를 추출하여 Signal을 생성합니다.

## 역할

- 인터뷰 텍스트 분석 및 구조화
- Pain Point/니즈/기회 추출
- Signal 후보 생성 (confidence score 포함)
- 고객 컨텍스트 분석 (segment, buyer role)

## 지원 입력 형식

| 형식 | 예시 | 처리 방식 |
|------|------|----------|
| 텍스트 | 인터뷰 노트 복사 | 직접 분석 |
| 문서 링크 | Confluence/Google Docs | 페이지 파싱 후 분석 |
| 구조화 데이터 | JSON (interviewee, date, content) | 메타데이터 활용 |

## 입력

```json
{
  "content": "인터뷰 노트 텍스트 또는 문서 링크",
  "play_id": "KT_Sales_S01",
  "customer": "ABC금융",
  "source": "KT",
  "channel": "영업PM",
  "interviewee": "김팀장 (CS팀)",
  "interview_date": "2025-01-15"
}
```

## 출력

```json
{
  "signals": [
    {
      "title": "콜센터 AHT 최적화 니즈",
      "pain": "평균 통화 시간 8분으로 고객 불만 및 인건비 증가",
      "current_workflow": "상담원이 매뉴얼 검색 후 수동 응대",
      "kpi_hypothesis": ["AHT 15% 감소", "FCR 10% 향상"],
      "confidence": 0.85,
      "evidence_quotes": ["현재 AHT가 8분인데...", "비용이 계속 증가해서..."]
    }
  ],
  "customer_context": {
    "segment": "금융 콜센터",
    "buyer_role": "CS팀장",
    "budget_signal": "예산 확보 가능성 언급됨",
    "timeline": "Q2 도입 희망"
  },
  "follow_up_questions": [
    "현재 사용 중인 CTI 시스템은?",
    "데이터 접근 권한 범위는?"
  ]
}
```

## 추출 프로세스

```
1. 인터뷰 텍스트 전처리 (노이즈 제거)
2. 문장 단위 분석
3. Pain Point 패턴 탐지
4. 니즈/기회 추출
5. KPI 가설 도출
6. 신뢰도 점수 산정
7. Signal JSON 생성
```

## Pain Point 추출 패턴

다음 패턴 감지 시 Pain Point로 추출:

```python
PAIN_PATTERNS = [
    r"(문제|어려움|고민|불편|힘들).*있",
    r"(시간|비용|인력)이? (많이|너무) (들|소요)",
    r"(효율|생산성)이? (낮|떨어)",
    r"(불만|민원|클레임).*증가",
    r"(수작업|수동|매뉴얼).*처리",
    r"(오류|실수|누락).*발생",
]
```

## 니즈/기회 추출 패턴

```python
NEED_PATTERNS = [
    r"(원하|필요|요구).*솔루션",
    r"(자동화|효율화|최적화).*하고 싶",
    r"(도입|적용|활용).*검토",
    r"(개선|향상|줄이).*방법",
    r"(예산|투자).*계획",
]
```

## KPI 가설 도출 규칙

| Pain 유형 | 추천 KPI |
|----------|----------|
| 시간 소요 | 처리 시간 X% 감소 |
| 비용 증가 | 비용 X% 절감 |
| 오류 발생 | 오류율 X% 감소 |
| 고객 불만 | 만족도 X점 향상 |
| 수작업 처리 | 자동화율 X% 달성 |

## 신뢰도 점수 산정

```python
def calculate_confidence(extracted: dict) -> float:
    score = 0.5  # 기본값

    # Pain이 명시적으로 언급됨
    if extracted.get("pain"):
        score += 0.15

    # 수치가 포함됨 (예: "8분", "30%")
    if has_numeric_data(extracted):
        score += 0.15

    # KPI 가설이 구체적
    if len(extracted.get("kpi_hypothesis", [])) >= 2:
        score += 0.10

    # 원문 인용이 있음
    if extracted.get("evidence_quotes"):
        score += 0.10

    return min(score, 1.0)
```

## 고객 컨텍스트 분석

```python
def extract_customer_context(text: str) -> dict:
    return {
        "segment": detect_industry(text),  # 금융, 제조, 유통 등
        "buyer_role": detect_buyer_role(text),  # C-level, 팀장, 실무자
        "budget_signal": detect_budget_signal(text),  # 예산 관련 언급
        "timeline": detect_timeline(text),  # 도입 희망 시점
        "decision_process": detect_decision_process(text)  # 의사결정 과정
    }
```

## Orchestrator 연동

```python
# WF-02: Interview to Brief 파이프라인에서 호출
async def run_interview_pipeline(input_data: InterviewInput):
    # 1. Interview Miner로 Signal 추출
    miner_result = await call_agent("interview_miner", input_data)

    # 2. 각 Signal에 대해 Scorecard 평가
    for signal in miner_result.signals:
        scorecard = await call_agent("scorecard_evaluator", signal)

        # 3. GO 판정 시 Brief 생성
        if scorecard.decision == "GO":
            brief = await call_agent("brief_writer", {
                "signal": signal,
                "scorecard": scorecard
            })
```

## 설정

```json
{
  "agent_id": "interview_miner",
  "model": "sonnet",
  "skill": "ax-interview",
  "min_confidence": 0.6,
  "max_signals_per_interview": 5,
  "requires_approval": false
}
```
