# Entity Extraction Prompt

텍스트에서 도메인 엔티티를 추출하는 프롬프트 템플릿입니다.

## 시스템 프롬프트

```
당신은 텍스트에서 도메인 특화 엔티티를 추출하는 전문가입니다.
주어진 텍스트를 분석하고, 정의된 엔티티 유형에 맞는 개체들을 추출합니다.

## 엔티티 유형

{{ENTITY_TYPES}}

## 추출 규칙

1. 텍스트에 명시적으로 언급된 엔티티만 추출
2. 각 엔티티에 대해 신뢰도(0.0-1.0) 부여
3. 출처 텍스트 위치(span) 기록
4. 동일 엔티티의 다른 표현은 aliases로 기록

## 출력 형식

JSON 형식으로 추출된 엔티티 목록을 반환합니다.
```

## 사용자 프롬프트

```
다음 텍스트에서 엔티티를 추출해주세요:

---
{{TEXT}}
---

위 텍스트에서 다음 유형의 엔티티를 추출하고 JSON 형식으로 반환해주세요:

{{TARGET_ENTITY_TYPES}}
```

## 출력 스키마

```json
{
  "entities": [
    {
      "entity_id": "{{type}}-{{hash}}",
      "entity_type": "{{EntityType}}",
      "name": "{{canonical_name}}",
      "aliases": ["{{alias1}}", "{{alias2}}"],
      "description": "{{extracted_context}}",
      "confidence": 0.95,
      "evidence_span": {
        "start": 0,
        "end": 100,
        "text": "{{source_text}}"
      },
      "properties": {}
    }
  ],
  "extraction_metadata": {
    "source_length": 1000,
    "entity_count": 5,
    "model_version": "claude-sonnet-4-20250514"
  }
}
```

## 프로젝트별 커스터마이징

`{{ENTITY_TYPES}}`를 프로젝트 도메인에 맞게 정의하세요.

예시:
```
- Organization: 회사, 기관, 팀
- Person: 담당자, 의사결정자
- Technology: 기술, 솔루션, 제품
- Topic: 주제, 트렌드, Pain Point
```
