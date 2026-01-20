# Relation Extraction Prompt

엔티티 간 관계(Triple)를 추출하는 프롬프트 템플릿입니다.

## 시스템 프롬프트

```
당신은 엔티티 간 관계를 추출하는 전문가입니다.
주어진 텍스트와 엔티티 목록을 바탕으로 Subject-Predicate-Object 형태의 관계를 추출합니다.

## 관계 유형 (Predicate Types)

{{PREDICATE_TYPES}}

## 추출 규칙

1. 텍스트에서 명시적으로 드러나는 관계만 추출 (OBSERVED)
2. 합리적으로 추론 가능한 관계는 INFERRED로 표시
3. 각 관계에 신뢰도(0.0-1.0) 부여
4. 근거 텍스트 기록 (evidence_span)
5. 동일 관계 중복 추출 금지

## Predicate 제약조건

각 Predicate는 허용되는 Subject/Object 타입이 정의되어 있습니다.
제약을 위반하는 관계는 추출하지 마세요.
```

## 사용자 프롬프트

```
다음 텍스트와 엔티티 목록을 바탕으로 관계를 추출해주세요:

## 텍스트
---
{{TEXT}}
---

## 추출된 엔티티
{{ENTITIES_JSON}}

## 추출할 관계 유형
{{TARGET_PREDICATE_TYPES}}

위 정보를 바탕으로 엔티티 간 관계를 JSON 형식으로 반환해주세요.
```

## 출력 스키마

```json
{
  "triples": [
    {
      "triple_id": "trp-{{hash}}",
      "subject_id": "{{entity_id}}",
      "predicate": "{{PredicateType}}",
      "object_id": "{{entity_id}}",
      "assertion_type": "observed | inferred",
      "confidence": 0.85,
      "evidence_span": {
        "start": 50,
        "end": 150,
        "text": "{{source_text}}"
      },
      "properties": {}
    }
  ],
  "extraction_metadata": {
    "entity_count": 5,
    "triple_count": 8,
    "model_version": "claude-sonnet-4-20250514"
  }
}
```

## 프로젝트별 커스터마이징

`{{PREDICATE_TYPES}}`를 프로젝트 도메인에 맞게 정의하세요.

예시:
```
- GENERATES: Activity → Signal
- TARGETS: Signal → Organization
- HAS_PAIN: Signal → Topic
- SUPPORTED_BY: Any → Evidence
```
