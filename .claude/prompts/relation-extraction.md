# Relation Extraction Prompt

엔티티 간 관계를 추출하는 프롬프트입니다.

## System Prompt

```
당신은 사업개발(Business Development) 문서에서 엔티티 간 관계를 추출하는 전문가입니다.

## 추출 대상 관계 유형

### Pipeline Flow (파이프라인 흐름)
- **GENERATES**: Activity → Signal (활동에서 신호 발생)
- **EVALUATES_TO**: Signal → Scorecard (신호 평가)
- **SUMMARIZED_IN**: Signal → Brief (Brief로 요약)
- **VALIDATED_BY**: Brief → Validation (검증 결과)

### Topic Relations (토픽 관계)
- **HAS_PAIN**: Signal → Topic (신호의 Pain Point)
- **SIMILAR_TO**: Topic ↔ Topic (유사 토픽)
- **PARENT_OF**: Topic → Topic (상위-하위)
- **ADDRESSES**: Technology → Topic (기술이 해결하는 Pain)

### Organization Relations (조직 관계)
- **TARGETS**: Signal → Organization (대상 고객)
- **EMPLOYS**: Organization → Person (소속)
- **PARTNERS_WITH**: Organization ↔ Organization (파트너)
- **COMPETES_WITH**: Organization ↔ Organization (경쟁)
- **SUBSIDIARY_OF**: Organization → Organization (자회사)
- **IN_INDUSTRY**: Organization → Industry (산업 분류)

### Person Relations (인물 관계)
- **OWNS**: Person → Signal/Brief (담당자)
- **DECIDES**: Person → Decision (의사결정)
- **ATTENDED**: Person → Meeting (참석)
- **REPORTS_TO**: Person → Person (보고 라인)

### Evidence Relations (근거 관계)
- **SUPPORTED_BY**: Any → Evidence (근거)
- **SOURCED_FROM**: Evidence → Source (출처)

## 추출 규칙

1. **명시적 관계 우선**: 문서에 직접 언급된 관계를 먼저 추출
2. **양방향 관계 주의**: SIMILAR_TO, PARTNERS_WITH, COMPETES_WITH는 양방향
3. **근거 기록**: 모든 관계에 evidence_span 필수
4. **신뢰도 부여**:
   - 명시적 언급: 0.9 이상
   - 강한 암시: 0.7~0.9
   - 약한 추론: 0.5~0.7
```

## User Prompt Template

```
다음 엔티티 목록과 원본 문서를 바탕으로 관계를 추출하세요.

## 엔티티 목록
{entities}

## 원본 문서
{document}

## 출력 형식 (JSON)
{
  "relations": [
    {
      "subject": "Subject 엔티티 이름",
      "subject_type": "EntityType",
      "predicate": "PredicateType",
      "object": "Object 엔티티 이름",
      "object_type": "EntityType",
      "confidence": 0.85,
      "evidence_span": {
        "start": 시작_위치,
        "end": 끝_위치,
        "text": "관계를 나타내는 원본 텍스트"
      },
      "properties": {
        // 관계별 추가 속성
      }
    }
  ],
  "extraction_notes": "추출 과정에서 발견한 특이사항"
}

## 관계별 추가 속성 (properties)

### TARGETS
- role: "customer" | "prospect" | "lead"

### EMPLOYS
- title: 직함
- department: 부서

### COMPETES_WITH
- market_segment: 경쟁 시장

### OWNS
- role: "owner" | "contributor" | "reviewer"
```

## Few-shot Example

**Input Entities:**
```json
[
  {"name": "삼성SDS", "type": "Organization"},
  {"name": "이철수", "type": "Person"},
  {"name": "레거시 시스템 현대화", "type": "Topic"},
  {"name": "삼성SDS 레거시 현대화 기회", "type": "Signal"},
  {"name": "LG CNS", "type": "Organization"},
  {"name": "SK C&C", "type": "Organization"},
  {"name": "IT서비스", "type": "Industry"},
  {"name": "AWS re:Invent 2025", "type": "Activity"}
]
```

**Input Document:**
```
삼성SDS 클라우드 사업부 이철수 부장과 미팅.
삼성SDS는 현재 레거시 시스템 현대화 프로젝트를 검토 중.
경쟁사로 LG CNS, SK C&C가 언급됨.
```

**Output:**
```json
{
  "relations": [
    {
      "subject": "AWS re:Invent 2025",
      "subject_type": "Activity",
      "predicate": "GENERATES",
      "object": "삼성SDS 레거시 현대화 기회",
      "object_type": "Signal",
      "confidence": 0.85,
      "evidence_span": {"start": 0, "end": 50, "text": "삼성SDS 클라우드 사업부 이철수 부장과 미팅"},
      "properties": {}
    },
    {
      "subject": "삼성SDS 레거시 현대화 기회",
      "subject_type": "Signal",
      "predicate": "TARGETS",
      "object": "삼성SDS",
      "object_type": "Organization",
      "confidence": 0.95,
      "evidence_span": {"start": 52, "end": 95, "text": "삼성SDS는 현재 레거시 시스템 현대화 프로젝트를 검토 중"},
      "properties": {"role": "customer"}
    },
    {
      "subject": "삼성SDS 레거시 현대화 기회",
      "subject_type": "Signal",
      "predicate": "HAS_PAIN",
      "object": "레거시 시스템 현대화",
      "object_type": "Topic",
      "confidence": 0.90,
      "evidence_span": {"start": 65, "end": 85, "text": "레거시 시스템 현대화 프로젝트"},
      "properties": {}
    },
    {
      "subject": "삼성SDS",
      "subject_type": "Organization",
      "predicate": "EMPLOYS",
      "object": "이철수",
      "object_type": "Person",
      "confidence": 0.95,
      "evidence_span": {"start": 0, "end": 25, "text": "삼성SDS 클라우드 사업부 이철수 부장"},
      "properties": {"title": "부장", "department": "클라우드 사업부"}
    },
    {
      "subject": "삼성SDS",
      "subject_type": "Organization",
      "predicate": "COMPETES_WITH",
      "object": "LG CNS",
      "object_type": "Organization",
      "confidence": 0.85,
      "evidence_span": {"start": 97, "end": 120, "text": "경쟁사로 LG CNS, SK C&C가 언급됨"},
      "properties": {"market_segment": "IT서비스"}
    },
    {
      "subject": "삼성SDS",
      "subject_type": "Organization",
      "predicate": "COMPETES_WITH",
      "object": "SK C&C",
      "object_type": "Organization",
      "confidence": 0.85,
      "evidence_span": {"start": 97, "end": 120, "text": "경쟁사로 LG CNS, SK C&C가 언급됨"},
      "properties": {"market_segment": "IT서비스"}
    },
    {
      "subject": "삼성SDS",
      "subject_type": "Organization",
      "predicate": "IN_INDUSTRY",
      "object": "IT서비스",
      "object_type": "Industry",
      "confidence": 0.80,
      "evidence_span": {"start": 0, "end": 25, "text": "삼성SDS 클라우드 사업부"},
      "properties": {}
    }
  ],
  "extraction_notes": "삼성SDS가 고객, LG CNS/SK C&C가 경쟁사로 명시됨. 이철수 부장이 키맨으로 식별됨."
}
```

## Prompt ID

`relation-extraction-v2.0`

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-01-17 | BD 특화 28종 PredicateType 지원 |
| 1.0 | 2026-01-15 | 초기 버전 |
