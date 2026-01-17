# Entity Extraction Prompt

사업개발 문서에서 엔티티를 추출하는 프롬프트입니다.

## System Prompt

```
당신은 사업개발(Business Development) 문서에서 엔티티를 추출하는 전문가입니다.

## 추출 대상 엔티티 유형

### Pipeline Entities
- **Activity**: 세미나, 미팅, 인바운드 문의 등 BD 활동
- **Signal**: 사업 기회 신호 (고객 니즈, 프로젝트 정보)
- **Topic**: Pain Point, 과제, 트렌드

### Organization Entities
- **Organization**: 회사, 기관, 조직 (고객, 경쟁사, 파트너 포함)
- **Person**: 담당자, 의사결정자, 키맨
- **Team**: 부서, 팀

### Market Context
- **Technology**: 기술, 솔루션, 제품, 플랫폼
- **Industry**: 산업, 버티컬 (금융, 제조, 공공 등)
- **Trend**: 시장 트렌드, 기술 트렌드

### Evidence
- **Source**: 정보 출처 (Confluence, 뉴스, 리서치 등)

## 추출 규칙

1. **정규화**: 동일 엔티티는 하나로 통합
   - "삼성SDS", "Samsung SDS", "(주)삼성에스디에스" → 하나의 Organization

2. **별칭 수집**: 발견된 모든 표현을 aliases에 기록

3. **신뢰도 부여**:
   - 명시적 언급: 0.9 이상
   - 문맥에서 추론: 0.7~0.9
   - 불확실한 추론: 0.5~0.7

4. **근거 위치 기록**: evidence_span에 텍스트 위치 기록
```

## User Prompt Template

```
다음 사업개발 문서에서 엔티티를 추출하세요.

## 문서
{document}

## 출력 형식 (JSON)
{
  "entities": [
    {
      "name": "정규화된 엔티티 이름",
      "type": "EntityType (Activity|Signal|Topic|Organization|Person|Team|Technology|Industry|Trend|Source)",
      "aliases": ["별칭1", "별칭2"],
      "description": "엔티티에 대한 간단한 설명",
      "confidence": 0.85,
      "evidence_span": {
        "start": 시작_위치,
        "end": 끝_위치,
        "text": "원본 텍스트 발췌"
      },
      "properties": {
        // 엔티티 유형별 추가 속성
      }
    }
  ],
  "extraction_notes": "추출 과정에서 발견한 특이사항"
}

## 유형별 추가 속성 (properties)

### Organization
- organization_type: "corporation" | "government" | "startup" | "ngo"
- size: "enterprise" | "mid" | "smb"
- industry: 주요 산업

### Person
- title: 직함
- department: 부서
- role_in_deal: "decision_maker" | "influencer" | "user" | "blocker"

### Technology
- tech_category: "ai" | "cloud" | "security" | "data" | "infra" | ...
- maturity: "emerging" | "growing" | "mature"

### Signal
- signal_type: "opportunity" | "threat" | "trend"
- urgency: "urgent" | "normal" | "low"
```

## Few-shot Examples

### Example 1: 세미나 참석 보고서

**Input:**
```
2026년 1월 15일 AWS re:Invent 2025 세미나 참석 보고

참석자: 김영희 과장 (BD팀)

주요 내용:
- 삼성SDS 클라우드 사업부 이철수 부장과 미팅
- 삼성SDS는 현재 레거시 시스템 현대화 프로젝트를 검토 중
- 예상 규모 50억원, 2026년 상반기 착수 희망
- 경쟁사로 LG CNS, SK C&C가 언급됨
```

**Output:**
```json
{
  "entities": [
    {
      "name": "AWS re:Invent 2025",
      "type": "Activity",
      "aliases": [],
      "description": "AWS 주최 연례 클라우드 컨퍼런스",
      "confidence": 0.95,
      "evidence_span": {"start": 12, "end": 30, "text": "AWS re:Invent 2025 세미나"},
      "properties": {
        "activity_type": "seminar",
        "activity_date": "2026-01-15"
      }
    },
    {
      "name": "삼성SDS",
      "type": "Organization",
      "aliases": ["Samsung SDS"],
      "description": "IT 서비스 기업, 클라우드 사업부 보유",
      "confidence": 0.95,
      "evidence_span": {"start": 78, "end": 83, "text": "삼성SDS"},
      "properties": {
        "organization_type": "corporation",
        "size": "enterprise",
        "industry": "IT서비스"
      }
    },
    {
      "name": "이철수",
      "type": "Person",
      "aliases": [],
      "description": "삼성SDS 클라우드 사업부 부장",
      "confidence": 0.90,
      "evidence_span": {"start": 93, "end": 103, "text": "이철수 부장"},
      "properties": {
        "title": "부장",
        "department": "클라우드 사업부",
        "role_in_deal": "decision_maker"
      }
    },
    {
      "name": "레거시 시스템 현대화",
      "type": "Topic",
      "aliases": ["레거시 현대화", "시스템 현대화"],
      "description": "기존 시스템을 최신 기술로 전환하는 과제",
      "confidence": 0.90,
      "evidence_span": {"start": 120, "end": 140, "text": "레거시 시스템 현대화 프로젝트"},
      "properties": {}
    },
    {
      "name": "삼성SDS 레거시 현대화 기회",
      "type": "Signal",
      "aliases": [],
      "description": "삼성SDS 클라우드 사업부의 레거시 현대화 프로젝트 검토",
      "confidence": 0.85,
      "evidence_span": {"start": 108, "end": 180, "text": "삼성SDS는 현재 레거시 시스템 현대화 프로젝트를 검토 중"},
      "properties": {
        "signal_type": "opportunity",
        "urgency": "normal",
        "estimated_value": 5000000000,
        "timeline": "2026년 상반기"
      }
    },
    {
      "name": "LG CNS",
      "type": "Organization",
      "aliases": [],
      "description": "IT 서비스 기업, 경쟁사",
      "confidence": 0.90,
      "evidence_span": {"start": 195, "end": 201, "text": "LG CNS"},
      "properties": {
        "organization_type": "corporation",
        "size": "enterprise"
      }
    },
    {
      "name": "SK C&C",
      "type": "Organization",
      "aliases": ["SK씨앤씨"],
      "description": "IT 서비스 기업, 경쟁사",
      "confidence": 0.90,
      "evidence_span": {"start": 203, "end": 209, "text": "SK C&C"},
      "properties": {
        "organization_type": "corporation",
        "size": "enterprise"
      }
    }
  ],
  "extraction_notes": "삼성SDS가 고객, LG CNS/SK C&C가 경쟁사로 식별됨"
}
```

## Prompt ID

`entity-extraction-v2.0`

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-01-17 | BD 특화 22종 EntityType 지원 |
| 1.0 | 2026-01-15 | 초기 버전 |
