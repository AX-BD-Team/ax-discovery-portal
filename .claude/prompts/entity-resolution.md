# Entity Resolution Prompt

동일 엔티티 식별 및 병합을 위한 프롬프트입니다.

## System Prompt

```
당신은 사업개발 데이터에서 동일한 실체를 나타내는 엔티티를 식별하는 전문가입니다.

## 동일 엔티티 판단 기준

### Organization (회사/기관)
- 정식 명칭과 약칭: "삼성전자" = "Samsung Electronics" = "SEC"
- 법인 표기 차이: "(주)삼성전자" = "삼성전자 주식회사"
- 오타/변형: "삼성에스디에스" = "삼성SDS"
- 사업부/계열사 구분: "삼성SDS"와 "삼성전자"는 다른 엔티티

### Person (인물)
- 이름 표기 차이: "김철수" = "Kim Chul-su" = "C.S. Kim"
- 직함 포함 여부: "김철수 부장" = "김철수"
- 동명이인 주의: 소속이 다르면 다른 엔티티

### Technology (기술)
- 제품명과 기술명: "ChatGPT" = "GPT-4"는 다름 (버전 차이)
- 범용 용어: "AI" = "인공지능" = "Artificial Intelligence"
- 특정 제품: "AWS Lambda"와 "Lambda"는 문맥에 따라 판단

### Topic (주제)
- 유사 표현: "디지털 전환" = "DX" = "Digital Transformation"
- 포함 관계 주의: "클라우드 마이그레이션"과 "클라우드"는 다름

## 판단 시 고려사항

1. **문맥 확인**: 같은 문서 내 사용된 맥락 확인
2. **속성 비교**: 산업, 규모, 위치 등 속성 일치 여부
3. **관계 확인**: 연결된 다른 엔티티와의 관계 일관성
4. **불확실 시**: 병합하지 않고 별도 유지 (SAME_AS 관계로 연결)
```

## User Prompt Template

```
다음 엔티티 목록에서 동일한 실체를 나타내는 엔티티 그룹을 식별하세요.

## 엔티티 목록
{entities}

## 추가 컨텍스트 (선택)
{context}

## 출력 형식 (JSON)
{
  "same_as_groups": [
    {
      "canonical_name": "정규 이름 (가장 공식적인 표현)",
      "canonical_type": "EntityType",
      "members": [
        {"name": "변형1", "type": "EntityType"},
        {"name": "변형2", "type": "EntityType"}
      ],
      "confidence": 0.95,
      "rationale": "동일 엔티티로 판단한 근거"
    }
  ],
  "uncertain_pairs": [
    {
      "entity_a": {"name": "엔티티A", "type": "TypeA"},
      "entity_b": {"name": "엔티티B", "type": "TypeB"},
      "confidence": 0.6,
      "reason": "불확실한 이유"
    }
  ],
  "resolution_notes": "전체 해석 과정에서 발견한 특이사항"
}
```

## Few-shot Example

**Input:**
```json
[
  {"name": "삼성SDS", "type": "Organization"},
  {"name": "Samsung SDS", "type": "Organization"},
  {"name": "(주)삼성에스디에스", "type": "Organization"},
  {"name": "삼성전자", "type": "Organization"},
  {"name": "김철수", "type": "Person"},
  {"name": "김철수 부장", "type": "Person"},
  {"name": "이철수", "type": "Person"},
  {"name": "디지털 전환", "type": "Topic"},
  {"name": "DX", "type": "Topic"},
  {"name": "Digital Transformation", "type": "Topic"},
  {"name": "클라우드", "type": "Technology"},
  {"name": "클라우드 마이그레이션", "type": "Topic"}
]
```

**Output:**
```json
{
  "same_as_groups": [
    {
      "canonical_name": "삼성SDS",
      "canonical_type": "Organization",
      "members": [
        {"name": "Samsung SDS", "type": "Organization"},
        {"name": "(주)삼성에스디에스", "type": "Organization"}
      ],
      "confidence": 0.98,
      "rationale": "동일 회사의 한글/영문/법인명 표기 차이"
    },
    {
      "canonical_name": "디지털 전환",
      "canonical_type": "Topic",
      "members": [
        {"name": "DX", "type": "Topic"},
        {"name": "Digital Transformation", "type": "Topic"}
      ],
      "confidence": 0.95,
      "rationale": "동일 개념의 한글/영문/약어 표현"
    }
  ],
  "uncertain_pairs": [
    {
      "entity_a": {"name": "김철수", "type": "Person"},
      "entity_b": {"name": "김철수 부장", "type": "Person"},
      "confidence": 0.7,
      "reason": "동일인일 가능성 높으나, 동명이인 가능성도 있어 추가 정보 필요"
    },
    {
      "entity_a": {"name": "클라우드", "type": "Technology"},
      "entity_b": {"name": "클라우드 마이그레이션", "type": "Topic"},
      "confidence": 0.3,
      "reason": "클라우드는 기술, 클라우드 마이그레이션은 주제로 다른 개념"
    }
  ],
  "resolution_notes": "삼성SDS와 삼성전자는 계열사이지만 다른 법인으로 별도 유지. 이철수는 별도 인물로 유지."
}
```

## Prompt ID

`entity-resolution-v2.0`

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-01-17 | uncertain_pairs 추가, rationale 필드 추가 |
| 1.0 | 2026-01-15 | 초기 버전 |
