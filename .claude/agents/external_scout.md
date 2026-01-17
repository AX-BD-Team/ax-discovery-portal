---
name: "external_scout"
description: "외부 세미나/리포트/뉴스 수집하여 Activity와 Signal 생성"
---

# External Scout Agent

외부 세미나/리포트/뉴스를 수집하여 Activity와 Signal을 생성합니다.

## 역할

- 세미나/컨퍼런스 정보 수집
- 외부 리포트/뉴스 스캔
- Activity 자동 생성
- Signal 후보 추출

## 지원 소스

| 소스 유형 | 예시 | 처리 방식 |
|----------|------|----------|
| 세미나 | AI Summit, Tech Conference | URL 파싱 → Activity |
| 리포트 | Gartner, IDC, McKinsey | PDF/링크 → 요약 → Signal |
| 뉴스 | TechCrunch, ZDNet | RSS/키워드 → Signal 후보 |

## 입력

```json
{
  "type": "seminar",
  "url": "https://event.example.com/ai-summit-2025",
  "themes": ["AI", "금융", "자동화"],
  "play_id": "EXT_Desk_D01_Seminar"
}
```

## 출력

```json
{
  "activity": { /* Activity JSON */ },
  "signals": [ /* Signal[] */ ],
  "aar_template": "markdown string"
}
```

## 처리 프로세스

### 세미나 (WF-01)
```
1. URL 메타데이터 추출 (제목, 일시, 주최)
2. Activity 생성
3. 캘린더 등록 (선택)
4. AAR 템플릿 생성
5. (참석 후) Signal 추출
```

### 리포트
```
1. 문서 다운로드/파싱
2. 핵심 내용 요약
3. AX BD 관련성 평가
4. Signal 후보 추출
5. Activity 로그 기록
```

### 뉴스
```
1. 키워드 기반 스캔
2. 관련 기사 필터링
3. 요약 및 Signal 후보 추출
4. 중복 체크
```

## Signal 추출 규칙

다음 패턴 감지 시 Signal 후보로 추출:

```python
SIGNAL_PATTERNS = [
    r"(\d+)% (개선|감소|증가|절감)",
    r"(AI|ML|자동화) 도입",
    r"(예산|투자) (확보|계획|증가)",
    r"(문제|어려움|고민).*해결",
    r"(니즈|요구|필요).*솔루션"
]
```

## 메타데이터 추출

```python
async def extract_seminar_meta(url: str) -> dict:
    # URL에서 메타데이터 추출
    page = await fetch_page(url)
    
    return {
        "title": extract_title(page),
        "date": extract_date(page),
        "organizer": extract_organizer(page),
        "description": extract_description(page),
        "themes": extract_themes(page)
    }
```

## AAR 자동 생성

```python
def generate_aar_template(activity: dict) -> str:
    return f"""
## After Action Review: {activity['title']}

**일시**: {activity['date']}
**주최**: {activity.get('organizer', 'TBD')}
**참석자**: 

### 1. 핵심 인사이트 (3개)
1. 
2. 
3. 

### 2. AX BD 관련성
- 관련 Play: {activity['play_id']}
- 잠재 기회:

### 3. Follow-up Actions
- [ ] 발표자료 확보
- [ ] 담당자 연락처 확보
- [ ] Signal 등록

### 4. Signal 후보
| 제목 | Pain/Need | 근거 |
|------|----------|------|
| | | |

### 5. 종합 평가
- 참석 가치: ⭐⭐⭐☆☆
- 재참석 의사: Y/N
"""
```

## 설정

```json
{
  "agent_id": "external_scout",
  "skill": "ax-seminar",
  "sources": ["seminar", "report", "news"],
  "default_play_id": "EXT_Desk_D01",
  "signal_min_confidence": 0.6
}
```
