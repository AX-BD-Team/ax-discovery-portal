# AX Discovery Portal - Ontology v2 설계 문서

> 사업개발(BD) 특화 Knowledge Graph 온톨로지 상세 설계

**버전**: 2.0.0-draft
**작성일**: 2026-01-17
**상태**: 설계 검토 중

---

## 1. 개요

### 1.1 목적

AX Discovery Portal의 사업기회 포착 파이프라인을 지원하는 Knowledge Graph 온톨로지를 정의합니다. LLM 기반 정보 추출과 GraphRAG 검색에 최적화된 구조를 제공합니다.

### 1.2 설계 원칙

| 원칙 | 설명 |
|------|------|
| **Competency Questions 기반** | 도메인 핵심 질문에 답할 수 있는 구조 |
| **Evidence Traceability** | 모든 관계에 근거 연결 (hallucination 방지) |
| **Entity Consistency** | 동일 실체 정규화 (alias 관리) |
| **LLM Extraction 친화적** | 추출 메타데이터 및 신뢰도 계층화 |
| **Schema.org/FIBO 호환** | 표준 온톨로지와 상호운용성 |

### 1.3 참조 온톨로지

- [Schema.org](https://schema.org/) - Organization, Product, Service
- [FIBO](https://spec.edmcouncil.org/fibo/) - Financial Industry Business Ontology
- [Dublin Core](https://www.dublincore.org/) - 메타데이터 표준
- [GoodRelations](http://www.heppnetz.de/projects/goodrelations/) - E-commerce 온톨로지

---

## 2. 도메인 핵심 질문 (Competency Questions)

온톨로지 설계의 기준이 되는 핵심 질문입니다.

### 2.1 파이프라인 추적

```
CQ-01: 이 Signal은 어떤 Activity에서 발생했는가?
CQ-02: 이 Brief가 S2 승인을 받은 근거는 무엇인가?
CQ-03: Signal에서 Pilot까지 전체 히스토리는?
CQ-04: 이 Scorecard 점수의 각 차원별 근거는?
```

### 2.2 조직/인물 관계

```
CQ-05: A 고객과 관련된 모든 Signal과 Brief는?
CQ-06: B 담당자가 참여한 모든 미팅과 의사결정은?
CQ-07: C 조직의 경쟁사와 파트너사는?
CQ-08: 특정 Play에서 가장 활발한 고객은?
```

### 2.3 시장/기술 분석

```
CQ-09: D 산업에서 가장 많이 언급된 Pain Point는?
CQ-10: E 기술을 사용하는 잠재 고객은?
CQ-11: 최근 30일 내 유사한 Pain Point를 가진 Signal은?
CQ-12: F 트렌드와 관련된 사업 기회는?
```

### 2.4 의사결정 지원

```
CQ-13: GO/NOGO 결정의 근거와 결정자는?
CQ-14: 지연되고 있는 Brief의 병목 원인은?
CQ-15: 특정 Play의 성공률과 실패 패턴은?
CQ-16: 추천할 만한 유사 성공 사례는?
```

---

## 3. 3-Layer 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 3: BD Application Schema               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │Activity │→│ Signal  │→│Scorecard│→│  Brief  │→ ...       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │
│  Pipeline Flow, Play Management, KPI Tracking                  │
├─────────────────────────────────────────────────────────────────┤
│                    Layer 2: Business Domain                     │
│  ┌────────────┐  ┌────────┐  ┌──────────┐  ┌─────────┐        │
│  │Organization│  │ Person │  │Technology│  │Industry │        │
│  └────────────┘  └────────┘  └──────────┘  └─────────┘        │
│  Schema.org/FIBO 호환, 범용 비즈니스 개념                        │
├─────────────────────────────────────────────────────────────────┤
│                    Layer 1: Foundation                          │
│  ┌────────┐  ┌────────┐  ┌──────────────┐  ┌────────┐         │
│  │Evidence│  │ Source │  │ReasoningStep │  │Decision│         │
│  └────────┘  └────────┘  └──────────────┘  └────────┘         │
│  근거 추적, 추론 경로, 의사결정 이력                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Entity Types (22종)

### 4.1 Pipeline Entities (7종)

BD 파이프라인의 각 단계를 표현하는 핵심 엔티티입니다.

| Type | 설명 | Schema.org 매핑 | 예시 |
|------|------|----------------|------|
| `ACTIVITY` | 사업개발 활동 | Event | 세미나 참석, 고객 미팅, 인바운드 문의 |
| `SIGNAL` | 사업 기회 신호 | Thing | "삼성SDS AI 플랫폼 구축 니즈" |
| `TOPIC` | Pain Point / Trend | Thing | "레거시 시스템 현대화", "생성AI 도입" |
| `SCORECARD` | 100점 평가 | Rating | 5차원 평가 (Pain, Fit, Budget, Timeline, Access) |
| `BRIEF` | 1-Page 요약 | CreativeWork | 사업기회 요약 문서 |
| `VALIDATION` | S2 검증 결과 | Review | BD리더/사업부 검증 |
| `PILOT` | S3 파일럿 프로젝트 | Project | PoC/MVP 프로젝트 |

```python
# Pipeline Stage Enum
class PipelineStage(enum.Enum):
    S0_ACTIVITY = "S0"      # Activity 수집
    S1_SIGNAL = "S1"        # Signal 식별
    S1_5_SCORECARD = "S1.5" # Scorecard 평가
    S2_BRIEF = "S2"         # Brief 작성 + 검증
    S3_PILOT = "S3"         # Pilot 진행
    S4_DEAL = "S4"          # Deal 전환
```

### 4.2 Organization Entities (3종)

조직과 인물을 표현하는 엔티티입니다.

| Type | 설명 | Schema.org 매핑 | 속성 |
|------|------|----------------|------|
| `ORGANIZATION` | 회사/기관 | Organization | canonical_name, aliases, industry, size |
| `PERSON` | 담당자/의사결정자 | Person | name, title, department, contact |
| `TEAM` | BD팀/고객팀 | Organization | team_type, members |

```python
# Organization Role (Triple properties로 표현)
class OrganizationRole(enum.Enum):
    CUSTOMER = "customer"           # 잠재 고객
    COMPETITOR = "competitor"       # 경쟁사
    PARTNER = "partner"             # 파트너사
    VENDOR = "vendor"               # 벤더
    INVESTOR = "investor"           # 투자자
    SUBSIDIARY = "subsidiary"       # 자회사
    PARENT = "parent"               # 모회사
```

### 4.3 Market Context Entities (4종)

시장 컨텍스트를 표현하는 엔티티입니다.

| Type | 설명 | Schema.org 매핑 | 속성 |
|------|------|----------------|------|
| `TECHNOLOGY` | 기술/솔루션 | Product | tech_category, maturity, vendors |
| `INDUSTRY` | 산업/버티컬 | Industry | industry_code, sub_sectors |
| `MARKET_SEGMENT` | 시장 세그먼트 | Audience | segment_criteria, tam_size |
| `TREND` | 시장 트렌드 | Thing | trend_type, momentum, horizon |

```python
# Trend Type
class TrendType(enum.Enum):
    TECHNOLOGY = "technology"   # 기술 트렌드 (AI, Cloud 등)
    REGULATORY = "regulatory"   # 규제 트렌드 (데이터 보호 등)
    MARKET = "market"           # 시장 트렌드 (M&A, 투자 등)
    SOCIAL = "social"           # 사회 트렌드 (ESG, 원격근무 등)
```

### 4.4 Evidence & Reasoning Entities (4종)

근거와 추론을 추적하는 엔티티입니다.

| Type | 설명 | 용도 | 속성 |
|------|------|------|------|
| `EVIDENCE` | 근거 자료 | 주장의 근거 | content_hash, snippet, word_count |
| `SOURCE` | 출처 | 정보 원천 | source_type, url, credibility |
| `REASONING_STEP` | 추론 단계 | 논리 전개 | premise, conclusion, logic_type |
| `DECISION` | 의사결정 | GO/NOGO | decision_type, rationale, decider |

```python
# Source Type
class SourceType(enum.Enum):
    CONFLUENCE = "confluence"       # Confluence 페이지
    MEETING_NOTE = "meeting_note"   # 미팅 노트
    NEWS_ARTICLE = "news_article"   # 뉴스 기사
    RESEARCH_REPORT = "research_report"  # 리서치 리포트
    CUSTOMER_INTERVIEW = "customer_interview"  # 고객 인터뷰
    INTERNAL_DOC = "internal_doc"   # 내부 문서
    EMAIL = "email"                 # 이메일
    CRM = "crm"                     # CRM 데이터

# Decision Type
class DecisionType(enum.Enum):
    GO = "go"                       # 진행
    NOGO = "nogo"                   # 중단
    HOLD = "hold"                   # 보류
    PIVOT = "pivot"                 # 방향 전환
    ESCALATE = "escalate"           # 상위 결재
```

### 4.5 Operational Entities (4종)

운영/실행을 표현하는 엔티티입니다.

| Type | 설명 | Schema.org 매핑 | 속성 |
|------|------|----------------|------|
| `PLAY` | BD Play | Thing | play_category, owner, kpi_targets |
| `MEETING` | 미팅 기록 | Event | meeting_type, attendees, outcomes |
| `TASK` | 후속 조치 | Action | assignee, due_date, status |
| `MILESTONE` | 주요 이정표 | Event | milestone_type, target_date, achieved |

```python
# Play Category
class PlayCategory(enum.Enum):
    KT_INTERNAL = "kt_internal"     # KT 내부
    GROUP_AFFILIATE = "group"       # 그룹사
    EXTERNAL_ENTERPRISE = "external_enterprise"  # 대외 기업
    PUBLIC_SECTOR = "public_sector" # 공공
    SMB = "smb"                     # 중소기업
```

---

## 5. Predicate Types (28종)

### 5.1 Pipeline Flow Relations (6종)

파이프라인 단계 간 흐름을 표현합니다.

| Predicate | Domain | Range | 설명 |
|-----------|--------|-------|------|
| `GENERATES` | Activity | Signal | 활동에서 신호 발생 |
| `EVALUATES_TO` | Signal | Scorecard | 신호에 대한 평가 |
| `SUMMARIZED_IN` | Signal | Brief | 신호를 Brief로 요약 |
| `VALIDATED_BY` | Brief | Validation | Brief 검증 결과 |
| `PILOTS_AS` | Validation | Pilot | 검증 후 파일럿 |
| `PROGRESSES_TO` | Entity | Entity | 단계 전환 (일반) |

```
Activity --[GENERATES]--> Signal --[EVALUATES_TO]--> Scorecard
                              |
                              +--[SUMMARIZED_IN]--> Brief --[VALIDATED_BY]--> Validation
                                                                |
                                                                +--[PILOTS_AS]--> Pilot
```

### 5.2 Topic Relations (4종)

토픽(Pain Point) 간 관계를 표현합니다.

| Predicate | Domain | Range | 설명 |
|-----------|--------|-------|------|
| `HAS_PAIN` | Signal | Topic | 신호의 Pain Point |
| `SIMILAR_TO` | Topic | Topic | 유사 토픽 (양방향) |
| `PARENT_OF` | Topic | Topic | 상위-하위 토픽 |
| `ADDRESSES` | Technology | Topic | 기술이 해결하는 Pain |

### 5.3 Organization Relations (6종)

조직 간 관계를 표현합니다.

| Predicate | Domain | Range | Properties |
|-----------|--------|-------|------------|
| `TARGETS` | Signal | Organization | role: customer |
| `EMPLOYS` | Organization | Person | title, department |
| `PARTNERS_WITH` | Organization | Organization | partnership_type |
| `COMPETES_WITH` | Organization | Organization | market_segment |
| `SUBSIDIARY_OF` | Organization | Organization | ownership_pct |
| `IN_INDUSTRY` | Organization | Industry | primary: bool |

### 5.4 Person Relations (4종)

인물 관련 관계를 표현합니다.

| Predicate | Domain | Range | Properties |
|-----------|--------|-------|------------|
| `OWNS` | Person | Signal/Brief | role: owner/contributor |
| `DECIDES` | Person | Decision | decision_date |
| `ATTENDED` | Person | Meeting | role: host/participant |
| `REPORTS_TO` | Person | Person | - |

### 5.5 Evidence Relations (4종)

근거 추적 관계를 표현합니다.

| Predicate | Domain | Range | 필수 여부 |
|-----------|--------|-------|----------|
| `SUPPORTED_BY` | Any | Evidence | observed 필수 |
| `SOURCED_FROM` | Evidence | Source | 필수 |
| `INFERRED_FROM` | Any | ReasoningStep | inferred 시 |
| `CONTRADICTS` | Evidence | Evidence | 선택 |

### 5.6 Operational Relations (4종)

운영 관련 관계를 표현합니다.

| Predicate | Domain | Range | 설명 |
|-----------|--------|-------|------|
| `BELONGS_TO_PLAY` | Signal | Play | 담당 Play |
| `SCHEDULED_FOR` | Task | Meeting | 미팅 예정 |
| `ACHIEVES` | Task | Milestone | 이정표 달성 |
| `SAME_AS` | Entity | Entity | 동일 실체 |

---

## 6. Entity 상세 스키마

### 6.1 공통 필드

모든 Entity가 가지는 공통 필드입니다.

```python
class Entity(Base):
    """Entity 기본 스키마"""

    # ===== 식별자 =====
    entity_id: str              # 고유 ID (PREFIX-UUID8)
    entity_type: EntityType     # 엔티티 유형

    # ===== 기본 정보 =====
    name: str                   # 표시 이름
    canonical_name: str         # 정규화된 이름 (검색용)
    aliases: list[str]          # 별칭 목록
    description: str            # 설명
    natural_description: str    # 자연어 설명 (LLM 컨텍스트용)

    # ===== 분류 =====
    tags: list[str]             # 태그
    category: str               # 카테고리

    # ===== 신뢰도 =====
    confidence: float           # 신뢰도 (0.0 ~ 1.0)
    confidence_level: str       # gold/silver/bronze/hypothesis

    # ===== 벡터 =====
    embedding: list[float]      # 1536차원 벡터

    # ===== 외부 참조 =====
    external_ref_id: str        # 외부 시스템 ID
    external_ref_type: str      # 외부 시스템 유형

    # ===== 시간 (Recency) =====
    published_at: datetime      # 외부 발행 시각
    observed_at: datetime       # 내부 관측 시각
    ingested_at: datetime       # 시스템 수집 시각

    # ===== 동기화 =====
    last_synced_at: datetime    # 마지막 동기화
    sync_status: SyncStatus     # ok/stale/error

    # ===== LLM 추출 메타 =====
    extraction_prompt_id: str   # 추출 프롬프트 ID
    extraction_model: str       # 추출 모델
    extraction_confidence: float # LLM 자체 신뢰도
    human_verified: bool        # 사람 검증 여부
    human_verified_by: str      # 검증자
    human_verified_at: datetime # 검증 시각

    # ===== 메타데이터 =====
    properties: dict            # 유형별 추가 속성

    # ===== 감사 =====
    created_at: datetime
    updated_at: datetime
    created_by: str
```

### 6.2 Pipeline Entity 상세

#### 6.2.1 Activity

```python
class ActivityProperties:
    """Activity 추가 속성"""

    activity_type: str          # seminar, meeting, inbound, outbound, research
    activity_date: datetime     # 활동 일시
    location: str               # 장소/채널
    duration_minutes: int       # 소요 시간
    participants: list[str]     # 참석자
    source_channel: str         # 수집 채널 (3원천 x 5채널)
    raw_content: str            # 원본 내용
    summary: str                # 요약
```

#### 6.2.2 Signal

```python
class SignalProperties:
    """Signal 추가 속성"""

    signal_type: str            # opportunity, threat, trend, event
    urgency: str                # urgent, normal, low
    stage: str                  # S1, S1.5, S2, S3
    sla_deadline: datetime      # SLA 마감

    # 고객 정보
    target_org_id: str          # 대상 조직 ID
    target_industry: str        # 대상 산업

    # Pain Point
    pain_summary: str           # Pain 요약
    pain_severity: int          # 1-5

    # 기회 규모
    estimated_value: float      # 추정 규모 (원)
    estimated_timeline: str     # 예상 일정
```

#### 6.2.3 Scorecard

```python
class ScorecardProperties:
    """Scorecard 추가 속성"""

    total_score: int            # 총점 (0-100)
    recommendation: str         # GO, NOGO, HOLD, PIVOT

    # 5차원 점수
    dimensions: dict = {
        "pain": {
            "score": int,       # 0-20
            "evidence_ids": list,
            "rationale": str
        },
        "fit": {
            "score": int,       # 0-20
            "evidence_ids": list,
            "rationale": str
        },
        "budget": {
            "score": int,       # 0-20
            "evidence_ids": list,
            "rationale": str
        },
        "timeline": {
            "score": int,       # 0-20
            "evidence_ids": list,
            "rationale": str
        },
        "access": {
            "score": int,       # 0-20
            "evidence_ids": list,
            "rationale": str
        }
    }

    # 메타
    evaluator: str              # 평가자 (agent/user)
    evaluated_at: datetime
```

#### 6.2.4 Brief

```python
class BriefProperties:
    """Brief 추가 속성"""

    brief_type: str             # standard, express, deep_dive
    status: str                 # draft, review, approved, rejected

    # 구조화된 내용
    executive_summary: str      # 핵심 요약
    opportunity_description: str # 기회 설명
    customer_context: str       # 고객 컨텍스트
    solution_approach: str      # 솔루션 접근
    competitive_landscape: str  # 경쟁 상황
    financial_projection: str   # 재무 전망
    risk_assessment: str        # 리스크 평가
    next_steps: list[str]       # 후속 조치

    # 검증
    validation_status: str      # pending, approved, rejected
    validated_by: str
    validated_at: datetime
    validation_comments: str

    # Confluence 연동
    confluence_page_id: str
    confluence_url: str
```

### 6.3 Organization Entity 상세

#### 6.3.1 Organization

```python
class OrganizationProperties:
    """Organization 추가 속성"""

    # 식별
    business_registration_no: str   # 사업자등록번호
    stock_code: str                 # 주식 코드

    # 분류
    organization_type: str          # corporation, government, ngo, startup
    size: str                       # enterprise, mid, smb
    employee_count: int
    annual_revenue: float

    # 산업
    primary_industry: str
    secondary_industries: list[str]

    # 연락처
    headquarters_address: str
    website: str

    # 관계사
    parent_org_id: str
    subsidiary_org_ids: list[str]
```

#### 6.3.2 Person

```python
class PersonProperties:
    """Person 추가 속성"""

    # 소속
    organization_id: str
    department: str
    title: str

    # 역할
    role_in_deal: str           # decision_maker, influencer, user, blocker
    seniority: str              # c_level, vp, director, manager, staff

    # 연락처
    email: str
    phone: str
    linkedin: str

    # 관계
    reports_to_id: str
    direct_reports: list[str]
```

---

## 7. Triple 상세 스키마

### 7.1 기본 스키마

```python
class Triple(Base):
    """Triple 기본 스키마"""

    # ===== 식별자 =====
    triple_id: str              # TRP-UUID12

    # ===== SPO 구조 =====
    subject_id: str             # 출발 엔티티
    predicate: PredicateType    # 관계 유형
    object_id: str              # 도착 엔티티

    # ===== Lifecycle =====
    status: TripleStatus        # proposed/verified/deprecated/rejected
    assertion_type: AssertionType # observed/inferred

    # ===== 신뢰도 =====
    weight: float               # 관계 강도 (0.0 ~ 1.0)
    confidence: float           # 신뢰도 (0.0 ~ 1.0)
    confidence_level: str       # gold/silver/bronze/hypothesis

    # ===== 근거 추적 =====
    evidence_ids: list[str]     # 근거 Evidence ID 목록
    evidence_span: dict         # 근거 텍스트 위치
    # {
    #   "source_id": "src-001",
    #   "start": 100,
    #   "end": 200,
    #   "text": "..."
    # }

    # ===== 추론 추적 =====
    reasoning_path_id: str      # 추론 경로 ID

    # ===== LLM 추출 메타 =====
    extractor_run_id: str       # 추출기 실행 ID
    extraction_prompt_id: str   # 추출 프롬프트
    extraction_model: str       # 추출 모델

    # ===== 관계별 속성 =====
    properties: dict            # Predicate별 추가 속성

    # ===== 검증 =====
    verified_by: str
    verified_at: datetime
    rejection_reason: str

    # ===== 감사 =====
    created_at: datetime
    updated_at: datetime
    created_by: str
```

### 7.2 신뢰도 계층

GraphRAG 쿼리 시 사용되는 신뢰도 계층입니다.

```python
class ConfidenceLevel(enum.Enum):
    """신뢰도 계층"""

    GOLD = "gold"           # confidence >= 0.95, human_verified=True
    SILVER = "silver"       # confidence >= 0.80, status=verified
    BRONZE = "bronze"       # confidence >= 0.50, status=proposed
    HYPOTHESIS = "hypothesis" # confidence < 0.50 or no evidence
```

#### 쿼리 모드별 사용

| 모드 | 사용 계층 | 용도 |
|------|----------|------|
| `SAFE` | GOLD, SILVER | 프로덕션 답변 |
| `NORMAL` | GOLD, SILVER, BRONZE | 탐색적 분석 |
| `FULL` | 전체 | 디버깅/연구 |

### 7.3 Predicate별 제약 조건

```python
PREDICATE_CONSTRAINTS = {
    PredicateType.GENERATES: {
        "subject_types": {EntityType.ACTIVITY},
        "object_types": {EntityType.SIGNAL},
        "requires_evidence": True,
        "min_confidence": 0.7,
    },
    PredicateType.EVALUATES_TO: {
        "subject_types": {EntityType.SIGNAL},
        "object_types": {EntityType.SCORECARD},
        "requires_evidence": True,
        "cardinality": "one_to_one",  # 1:1 관계
    },
    PredicateType.TARGETS: {
        "subject_types": {EntityType.SIGNAL},
        "object_types": {EntityType.ORGANIZATION},
        "required_properties": ["role"],  # customer, competitor 등
    },
    PredicateType.SUPPORTED_BY: {
        "subject_types": set(EntityType),  # 모든 타입
        "object_types": {EntityType.EVIDENCE},
        "is_required_for_observed": True,  # observed 시 필수
    },
    PredicateType.SAME_AS: {
        "symmetric": True,  # 양방향
        "transitive": True,  # A=B, B=C → A=C
    },
    # ... 나머지 Predicate
}
```

---

## 8. LLM 추출 파이프라인

### 8.1 Entity Extraction

```yaml
# Entity 추출 프롬프트 템플릿
entity_extraction:
  system: |
    당신은 사업개발 문서에서 엔티티를 추출하는 전문가입니다.
    다음 유형의 엔티티를 식별하세요:
    - Organization: 회사, 기관, 조직
    - Person: 담당자, 의사결정자
    - Technology: 기술, 솔루션, 제품
    - Topic: Pain Point, 과제, 트렌드

  user: |
    다음 문서에서 엔티티를 추출하세요:

    {document}

    JSON 형식으로 응답:
    {
      "entities": [
        {
          "name": "엔티티 이름",
          "type": "엔티티 유형",
          "aliases": ["별칭1", "별칭2"],
          "description": "설명",
          "confidence": 0.9,
          "evidence_span": {"start": 10, "end": 50, "text": "..."}
        }
      ]
    }
```

### 8.2 Relation Extraction

```yaml
# Relation 추출 프롬프트 템플릿
relation_extraction:
  system: |
    당신은 사업개발 문서에서 엔티티 간 관계를 추출하는 전문가입니다.
    다음 관계 유형을 식별하세요:
    - TARGETS: Signal이 특정 Organization을 대상으로 함
    - HAS_PAIN: Signal이 특정 Pain Point(Topic)를 가짐
    - USES_TECHNOLOGY: Organization이 Technology를 사용함
    - COMPETES_WITH: Organization이 다른 Organization과 경쟁

  user: |
    엔티티 목록:
    {entities}

    원본 문서:
    {document}

    엔티티 간 관계를 추출하세요.
    JSON 형식으로 응답:
    {
      "relations": [
        {
          "subject": "엔티티 ID/이름",
          "predicate": "관계 유형",
          "object": "엔티티 ID/이름",
          "confidence": 0.85,
          "evidence_span": {"start": 100, "end": 150, "text": "..."},
          "properties": {}
        }
      ]
    }
```

### 8.3 Entity Resolution

```yaml
# 동일 엔티티 병합 프롬프트
entity_resolution:
  system: |
    다음 엔티티 목록에서 동일한 실체를 나타내는 엔티티를 식별하세요.
    - 회사명 변형: 삼성SDS, Samsung SDS, (주)삼성에스디에스
    - 약어: SK텔레콤, SKT, SK Telecom
    - 오타/변형 처리

  user: |
    엔티티 목록:
    {entities}

    동일 엔티티 그룹을 식별하세요:
    {
      "same_as_groups": [
        {
          "canonical": "정규 이름",
          "members": ["변형1", "변형2"],
          "confidence": 0.95
        }
      ]
    }
```

---

## 9. GraphRAG 쿼리 패턴

### 9.1 Pipeline Trace 쿼리

```cypher
-- Signal의 전체 파이프라인 히스토리
MATCH path = (a:Activity)-[:GENERATES]->(s:Signal)-[:EVALUATES_TO]->(sc:Scorecard)
             -[:SUMMARIZED_IN]->(b:Brief)-[:VALIDATED_BY]->(v:Validation)
WHERE s.entity_id = $signal_id
RETURN path

-- Brief의 근거 체인
MATCH (b:Brief)-[:SUPPORTED_BY*1..3]->(e:Evidence)-[:SOURCED_FROM]->(src:Source)
WHERE b.entity_id = $brief_id
RETURN b, e, src
```

### 9.2 Organization 360° View

```cypher
-- 조직 관련 모든 관계
MATCH (o:Organization {entity_id: $org_id})
OPTIONAL MATCH (o)-[:IN_INDUSTRY]->(i:Industry)
OPTIONAL MATCH (o)<-[:TARGETS]-(s:Signal)
OPTIONAL MATCH (o)-[:EMPLOYS]->(p:Person)
OPTIONAL MATCH (o)-[:PARTNERS_WITH]-(partner:Organization)
OPTIONAL MATCH (o)-[:COMPETES_WITH]-(comp:Organization)
RETURN o, i, collect(s), collect(p), collect(partner), collect(comp)
```

### 9.3 Similar Signal 탐색

```cypher
-- 유사 Pain Point를 가진 Signal 검색
MATCH (s1:Signal)-[:HAS_PAIN]->(t:Topic)<-[:HAS_PAIN]-(s2:Signal)
WHERE s1.entity_id = $signal_id AND s1 <> s2
WITH s2, count(t) as common_topics
ORDER BY common_topics DESC
LIMIT 10
RETURN s2, common_topics
```

### 9.4 Decision Trail

```cypher
-- 의사결정 이력 추적
MATCH (b:Brief)-[:VALIDATED_BY]->(v:Validation)
MATCH (p:Person)-[:DECIDES]->(d:Decision)
MATCH (d)-[:SUPPORTED_BY]->(e:Evidence)
WHERE b.entity_id = $brief_id
RETURN b, v, p, d, e
ORDER BY d.created_at
```

---

## 10. 인덱스 전략

### 10.1 Entity 인덱스

```sql
-- 기본 인덱스
CREATE INDEX idx_entity_type ON entities(entity_type);
CREATE INDEX idx_entity_name ON entities(name);
CREATE INDEX idx_entity_canonical ON entities(canonical_name);
CREATE INDEX idx_entity_external_ref ON entities(external_ref_id);

-- Recency 인덱스
CREATE INDEX idx_entity_published ON entities(published_at);
CREATE INDEX idx_entity_observed ON entities(observed_at);
CREATE INDEX idx_entity_ingested ON entities(ingested_at);

-- 신뢰도 인덱스
CREATE INDEX idx_entity_confidence ON entities(confidence);
CREATE INDEX idx_entity_confidence_level ON entities(confidence_level);

-- 복합 인덱스 (타입 + 신뢰도)
CREATE INDEX idx_entity_type_confidence ON entities(entity_type, confidence);
```

### 10.2 Triple 인덱스

```sql
-- SPO 패턴 인덱스 (6가지 조합)
CREATE INDEX idx_triple_spo ON triples(subject_id, predicate, object_id);
CREATE INDEX idx_triple_pos ON triples(predicate, object_id, subject_id);
CREATE INDEX idx_triple_osp ON triples(object_id, subject_id, predicate);
CREATE INDEX idx_triple_sp ON triples(subject_id, predicate);
CREATE INDEX idx_triple_po ON triples(predicate, object_id);
CREATE INDEX idx_triple_so ON triples(subject_id, object_id);

-- Lifecycle 인덱스
CREATE INDEX idx_triple_status ON triples(status);
CREATE INDEX idx_triple_assertion ON triples(assertion_type);
CREATE INDEX idx_triple_confidence ON triples(confidence);

-- 복합 인덱스 (안전모드 쿼리용)
CREATE INDEX idx_triple_status_pred ON triples(status, predicate);
CREATE INDEX idx_triple_status_conf ON triples(status, confidence);
CREATE INDEX idx_triple_status_assertion ON triples(status, assertion_type);
```

---

## 11. 마이그레이션 계획

### 11.1 Phase 1: 스키마 확장 (v2.1)

```
1. EntityType enum 확장 (13 → 22종)
2. PredicateType enum 확장 (17 → 28종)
3. 새 컬럼 추가 (canonical_name, aliases, extraction_*)
4. 기존 데이터 마이그레이션
```

### 11.2 Phase 2: 데이터 정규화 (v2.2)

```
1. Organization Role 분리 (CUSTOMER/COMPETITOR → HAS_ROLE)
2. Entity Resolution 실행 (SAME_AS 관계 생성)
3. Evidence 연결 보강
```

### 11.3 Phase 3: LLM 파이프라인 (v2.3)

```
1. Entity Extraction 프롬프트 적용
2. Relation Extraction 프롬프트 적용
3. Confidence Scoring 적용
4. Human-in-the-loop 검증 UI
```

---

## 12. 참고 문헌

- [NVIDIA: LLM-Driven Knowledge Graphs](https://developer.nvidia.com/blog/insights-techniques-and-evaluation-for-llm-driven-knowledge-graphs/)
- [GoodData: From RAG to GraphRAG](https://www.gooddata.com/blog/from-rag-to-graphrag-knowledge-graphs-ontologies-and-smarter-ai/)
- [deepsense.ai: Ontology-Driven KG for GraphRAG](https://deepsense.ai/resource/ontology-driven-knowledge-graph-for-graphrag/)
- [Wipro: Ontology Grounded RAG](https://wiprotechblogs.medium.com/ontology-grounded-rag-a-blueprint-for-truly-factual-llm-d09d28ff5502)
- [Schema.org](https://schema.org/)
- [FIBO - EDM Council](https://spec.edmcouncil.org/fibo/)

---

## 부록 A: EntityType ID Prefix 매핑

| EntityType | Prefix | 예시 |
|------------|--------|------|
| ACTIVITY | ACT | ACT-A1B2C3D4 |
| SIGNAL | SIG | SIG-E5F6G7H8 |
| TOPIC | TOP | TOP-I9J0K1L2 |
| SCORECARD | SCR | SCR-M3N4O5P6 |
| BRIEF | BRF | BRF-Q7R8S9T0 |
| VALIDATION | VAL | VAL-U1V2W3X4 |
| PILOT | PLT | PLT-Y5Z6A7B8 |
| ORGANIZATION | ORG | ORG-C9D0E1F2 |
| PERSON | PER | PER-G3H4I5J6 |
| TEAM | TEM | TEM-K7L8M9N0 |
| TECHNOLOGY | TEC | TEC-O1P2Q3R4 |
| INDUSTRY | IND | IND-S5T6U7V8 |
| MARKET_SEGMENT | MKT | MKT-W9X0Y1Z2 |
| TREND | TRD | TRD-A3B4C5D6 |
| EVIDENCE | EVD | EVD-E7F8G9H0 |
| SOURCE | SRC | SRC-I1J2K3L4 |
| REASONING_STEP | RST | RST-M5N6O7P8 |
| DECISION | DEC | DEC-Q9R0S1T2 |
| PLAY | PLY | PLY-U3V4W5X6 |
| MEETING | MTG | MTG-Y7Z8A9B0 |
| TASK | TSK | TSK-C1D2E3F4 |
| MILESTONE | MLS | MLS-G5H6I7J8 |

---

## 부록 B: 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0.0 | 2026-01-15 | 초기 온톨로지 (13 Entity, 17 Predicate) |
| 2.0.0-draft | 2026-01-17 | BD 특화 확장 설계 (22 Entity, 28 Predicate) |
