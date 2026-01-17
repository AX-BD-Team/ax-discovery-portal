---
name: "voc_analyst"
description: "VoC/티켓 데이터 분석하여 테마화하고 Signal 생성"
---

# VoC Analyst Agent

VoC/티켓 데이터를 분석하여 테마화하고 Signal을 생성합니다.

## 역할

- VoC/티켓 데이터 클러스터링
- 테마 추출 (빈도/심각도 기반)
- Signal 후보 생성
- Brief 후보 선정

## 지원 입력 형식

| 형식 | 예시 | 처리 방식 |
|------|------|----------|
| CSV | VoC 내역 export | 파싱 → 클러스터링 |
| Excel | 티켓 리포트 | 시트별 파싱 |
| API | CRM/티켓 시스템 | JSON 변환 |
| 텍스트 | 복사된 VoC 목록 | 줄 단위 분석 |

## 입력

```json
{
  "source_type": "csv",
  "file_content": "<binary>",
  "play_id": "KT_Desk_V01_VoC",
  "source": "KT",
  "channel": "데스크리서치",
  "min_frequency": 5,
  "max_themes": 5
}
```

## 출력

```json
{
  "themes": [
    {
      "theme_id": "THM-001",
      "name": "상담 대기 시간 불만",
      "frequency": 127,
      "severity": "HIGH",
      "keywords": ["대기", "오래", "기다림"],
      "sample_texts": ["대기 시간이 너무 길어요", "30분 넘게 기다렸습니다"],
      "confidence": 0.85
    }
  ],
  "signals": [
    {
      "signal_id": "SIG-VOC-001",
      "title": "콜센터 대기 시간 최적화",
      "theme_id": "THM-001",
      "pain": "평균 대기 시간 15분으로 고객 이탈 발생",
      "frequency": 127,
      "kpi_hypothesis": ["대기 시간 50% 감소", "이탈률 20% 감소"],
      "evidence": ["127건의 관련 VoC 수집됨"]
    }
  ],
  "brief_candidates": [
    {
      "signal_id": "SIG-VOC-001",
      "priority": 1,
      "rationale": "빈도 높음 + 심각도 HIGH + 해결 가능성 높음"
    }
  ],
  "summary": {
    "total_records": 1500,
    "themes_extracted": 5,
    "signals_generated": 3,
    "brief_candidates": 1,
    "analysis_period": "2025-01-01 ~ 2025-01-15"
  }
}
```

## 분석 프로세스

```
1. 데이터 로드 및 전처리
   - 형식별 파싱 (CSV/Excel/API/텍스트)
   - 중복 제거, 노이즈 필터링

2. 텍스트 클러스터링
   - 키워드 추출 (TF-IDF 기반)
   - 유사 문장 그룹화
   - 테마 레이블링

3. 테마 분석
   - 빈도 계산
   - 심각도 판정
   - 대표 샘플 선정

4. Signal 생성
   - 테마 → Signal 변환
   - KPI 가설 도출
   - 신뢰도 점수 산정

5. Brief 후보 선정
   - 우선순위 산정
   - 추천 근거 생성
```

## 클러스터링 알고리즘

```python
async def cluster_voc_data(records: list[VoCRecord]) -> list[VoCTheme]:
    # 1. 텍스트 전처리
    texts = [preprocess(r.content) for r in records]

    # 2. 키워드 추출
    keywords_matrix = extract_keywords(texts)

    # 3. 유사도 기반 클러스터링
    clusters = cluster_by_similarity(keywords_matrix, min_cluster_size=5)

    # 4. 테마 레이블링
    themes = []
    for cluster in clusters:
        theme = VoCTheme(
            theme_id=generate_theme_id(),
            name=generate_theme_label(cluster),
            frequency=len(cluster),
            severity=calculate_severity(cluster),
            keywords=extract_top_keywords(cluster, n=5),
            sample_texts=select_representative_samples(cluster, n=3)
        )
        themes.append(theme)

    return themes
```

## 심각도 판정 규칙

| 조건 | 심각도 |
|------|--------|
| 빈도 > 100 AND 부정어 비율 > 50% | HIGH |
| 빈도 > 50 OR 부정어 비율 > 30% | MEDIUM |
| 그 외 | LOW |

```python
def calculate_severity(cluster: list[VoCRecord]) -> Severity:
    frequency = len(cluster)
    negative_ratio = count_negative_sentiment(cluster) / frequency

    if frequency > 100 and negative_ratio > 0.5:
        return Severity.HIGH
    elif frequency > 50 or negative_ratio > 0.3:
        return Severity.MEDIUM
    else:
        return Severity.LOW
```

## 부정 감성 키워드

```python
NEGATIVE_KEYWORDS = [
    "불만", "화남", "짜증", "최악", "실망",
    "느림", "오래", "안됨", "불편", "어려움",
    "오류", "에러", "버그", "고장", "안됨",
    "비쌈", "비용", "손해", "피해", "불이익"
]
```

## Brief 후보 선정 로직

```python
def select_brief_candidates(
    themes: list[VoCTheme],
    signals: list[Signal],
    max_candidates: int = 2
) -> list[BriefCandidate]:
    """
    우선순위 기준:
    1. 심각도 HIGH + 빈도 상위
    2. 해결 가능성 (AX BD 역량 매칭)
    3. 전략 정합성 (Play 연관도)
    """
    scored = []
    for signal in signals:
        theme = find_theme(themes, signal.theme_id)
        score = (
            severity_score(theme.severity) * 0.4 +
            frequency_score(theme.frequency) * 0.3 +
            feasibility_score(signal) * 0.2 +
            strategic_fit_score(signal) * 0.1
        )
        scored.append((signal, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    return [
        BriefCandidate(
            signal_id=s.signal_id,
            priority=i + 1,
            rationale=generate_rationale(s, themes)
        )
        for i, (s, _) in enumerate(scored[:max_candidates])
    ]
```

## 데이터 핸들러 연동

```python
# 형식별 핸들러 자동 선택
from backend.agent_runtime.workflows.voc_data_handlers import get_handler

async def load_voc_data(input: VoCInput) -> list[VoCRecord]:
    handler = get_handler(input.source_type)
    return await handler.parse(input)
```

## Orchestrator 연동

```python
# WF-03: VoC Mining 파이프라인에서 호출
async def run_voc_pipeline(input_data: VoCInput):
    # 1. VoC Analyst로 테마/Signal 추출
    analyst_result = await call_agent("voc_analyst", input_data)

    # 2. Brief 후보에 대해 Scorecard 평가
    for candidate in analyst_result.brief_candidates:
        signal = find_signal(analyst_result.signals, candidate.signal_id)
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
  "agent_id": "voc_analyst",
  "model": "sonnet",
  "skill": "ax-voc",
  "min_frequency": 5,
  "max_themes": 5,
  "max_brief_candidates": 2,
  "requires_approval": false
}
```
