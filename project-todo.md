# AX Discovery Portal - Project TODO

> 프로젝트 진행 상황 및 다음 단계

**현재 버전**: 0.6.0
**마지막 업데이트**: 2026-01-18

---

## 📌 현재 스프린트 (Week 6 - 2026-01-17)

**목표**: PoC 완료 및 데모 준비
**테마**: v0.5.0 릴리스 - PoC 6주 목표 달성 검증 및 최종 발표

### 미완료 항목

#### 1. PoC 목표 달성 검증 📊
- [ ] 실제 데이터 수집 시작 (Activity 20+, Signal 30+/주)
- [x] WF-01~06 전체 파이프라인 E2E 테스트 ✅ 80 passed, 2 skipped
- [x] KPI Digest 리포트 생성 테스트 (`/ax:kpi-digest`) ✅ v0.6.0
- [x] 리드타임 측정 (Signal→Brief ≤7일, Brief→S2 ≤14일) ✅ 목표 달성

#### 2. 안정화 및 최적화 🔧
- [ ] 프로덕션 환경 모니터링 설정 (Sentry 알림)
- [ ] 성능 병목 점검 (느린 API 최적화)
- [ ] 마지막 버그 수정

#### 3. 릴리스 🚀
- [x] PoC 주간 목표 달성 검증 (Activity 20+, Signal 30+, Brief 6+, S2 2~4/주) ✅ KPI Digest 확인
- [ ] 데모 시연 성공 (3개 시나리오)
- [x] v0.6.0 릴리스 및 태그 ✅ (외부 세미나 기능 확장)

### 완료 항목 ✅

#### 데모 준비 🎬
- [x] 데모 시나리오 작성 (3개 핵심 플로우) ✅
- [x] 데모 데이터 준비 (샘플 Activity, Signal, Brief) ✅
- [x] 발표 자료 초안 (PoC 결과 요약) ✅

#### 문서화 완성 📚
- [x] 사용자 가이드 작성 (주요 워크플로 사용법) ✅ v0.4.0
- [x] Quick Start 가이드 (5분 내 시작) ✅
- [x] FAQ 문서 (자주 묻는 질문) ✅

#### UI/UX 마무리 🎨
- [x] 대시보드 KPI 위젯 실데이터 연동 ✅
- [x] 에러 핸들링 UX 개선 (Toast 알림, 글로벌 에러 페이지) ✅
- [x] 모바일 반응형 레이아웃 확인 ✅

### 일정

| 일자 | 작업 |
|------|------|
| Day 1-2 | PoC 목표 달성 검증, 데이터 수집 |
| Day 3 | 데모 시나리오 작성, 데모 데이터 준비 |
| Day 4 | 사용자 가이드 작성, UI/UX 마무리 |
| Day 5 | 최종 점검, v0.5.0 릴리스, PoC 발표 |

---

## 🚧 진행 중인 Phase

### Phase 5: AI 에이전트 평가(Evals) 플랫폼 (0% 완료) - 신규

> **근거**: RosettaLens 번역본 'AI 에이전트를 위한 평가(evals) 쉽게 이해하기' 및 Anthropic Engineering
> **목적**: 에이전트 품질을 개발 단계에서 자동 검증, 프로덕션 반응적 루프 감소

#### Phase 5.0: MVP (4-6주 목표)

| # | 항목 | 상태 | 예상 일정 |
|---|------|------|----------|
| 1 | Task/Suite YAML 스키마 정의 (`evals/` 디렉토리) | 🔲 | Week 7 |
| 2 | 핵심 엔터티 모델 구현 (Task, Trial, Transcript, GraderResult) | 🔲 | Week 7 |
| 3 | DB 마이그레이션 (eval_suites, eval_tasks, eval_runs, eval_trials) | 🔲 | Week 7 |
| 4 | Eval Harness 기본 구현 (단일 프로세스 실행기) | 🔲 | Week 8 |
| 5 | Deterministic Graders (pytest, ruff, mypy 기반) | 🔲 | Week 8 |
| 6 | Transcript/Outcome 저장 + 간단 뷰어 API | 🔲 | Week 9 |
| 7 | CI 게이팅 (regression suite 자동 실행) | 🔲 | Week 9 |
| 8 | 기존 6개 에이전트 기본 Task 작성 (각 3-5개) | 🔲 | Week 10 |

#### Phase 5.1: 신뢰성 강화 (Phase 5.0 완료 후)

| # | 항목 | 상태 |
|---|------|------|
| 1 | LLM-as-Judge grader 구현 (Claude 루브릭 기반) | 🔲 |
| 2 | 인간 보정 워크플로 (SME 스팟체크, IAA 관리) | 🔲 |
| 3 | pass@k / pass^k 공식 리포트 | 🔲 |
| 4 | 비용/지연/토큰 대시보드 | 🔲 |
| 5 | Trial 격리 환경 (컨테이너 기반 샌드박스) | 🔲 |

#### Phase 5.2: 에이전트 유형 확장 + 거버넌스 (Phase 5.1 완료 후)

| # | 항목 | 상태 |
|---|------|------|
| 1 | 대화형 에이전트 평가 (사용자 시뮬레이터 LLM) | 🔲 |
| 2 | 리서치 에이전트 평가 (groundedness/coverage/source quality) | 🔲 |
| 3 | Eval saturation 모니터링 + capability→regression 자동 전환 | 🔲 |
| 4 | 도메인팀 Task PR 기여 모델 + 오너십 정책 | 🔲 |
| 5 | Anti-cheat grader 설계 가이드 | 🔲 |

#### 핵심 개념 모델

| 개념 | 설명 |
|------|------|
| **Task** | 입력 + 성공 기준이 정의된 단일 테스트 케이스 |
| **Trial** | 한 Task에 대한 1회 실행 시도 (비결정성 → 복수 트라이얼) |
| **Transcript** | Trial의 전체 기록 (출력, 도구 호출, 중간 상태) |
| **Outcome** | Trial 종료 시 환경의 최종 상태 ("말"이 아닌 "상태" 검증) |
| **Grader** | 성능 특정 측면을 점수화하는 로직 |
| **Eval Suite** | 특정 역량/행동을 측정하는 Task 묶음 |

#### 채점 전략 (에이전트별)

| 에이전트 | Eval 유형 | 채점 전략 |
|---------|----------|----------|
| orchestrator | capability | outcome + 워크플로 완료율 |
| external_scout | regression | 수집 데이터 품질 + 소스 다양성 |
| scorecard_evaluator | capability | Scorecard 정확도 + 인간 보정 |
| brief_writer | capability | Brief 품질 루브릭 (LLM judge) |
| confluence_sync | regression | 동기화 성공률 + 데이터 무결성 |
| voc_analyst | capability | 테마 추출 정확도 + coverage |

---

### Phase 3: Advanced Features (97% 완료)

**미완료 항목**:
- [ ] Confluence Database API 구현 (db_query, db_upsert_row) - *PoC 이후 검토*

**완료 항목** (36개):
- [x] Scorecard API 라우터 DB 연동 ✅ v0.3.0
- [x] Brief API 라우터 DB 연동 ✅ v0.3.0
- [x] PlayDashboard API 라우터 DB 연동 ✅ v0.3.0
- [x] WF-02 Interview-to-Brief 구현 ✅ v0.3.0
- [x] WF-04 Inbound Triage 구현 ✅ v0.3.0
- [x] WF-03 VoC Mining 구현 ✅ v0.4.0
- [x] Opportunity Stage 파이프라인 시스템 ✅ v0.5.0
- [x] Ontology 기반 Knowledge Graph ✅ v0.4.0 → v0.5.1 강화
- [x] 중복 Signal 체크 알고리즘 ✅ v0.3.0
- [x] WF-05 KPI Digest 구현 ✅ v0.4.0
- [x] WF-06 Confluence Sync 구현 ✅ v0.4.0
- [x] Teams 연동 (MCP 서버) ✅ v0.4.0
- [x] Slack 연동 (MCP 서버) ✅ v0.4.0
- [x] Vector RAG 파이프라인 ✅ v0.4.0

### Phase 4: UI & UX (94% 완료)

**미완료 항목**:
- [ ] 모바일 앱 (PWA/React Native) - *PoC 이후 검토*

**완료 항목** (17개):
- [x] 모노레포 구조 (pnpm + Turborepo) ✅ v0.3.0
- [x] 웹 UI (Next.js 15) - 6개 페이지 ✅ v0.3.0
- [x] AXIS 디자인 시스템 ✅ v0.3.0
- [x] 공유 패키지 5개 ✅ v0.3.0
- [x] 페이지별 API 연동 완성 ✅ v0.4.0

---

## 🐛 알려진 이슈

| # | 이슈 | 상태 | 해결 방법 |
|---|------|------|----------|
| 1 | Stream Router dataclass 오류 | ✅ 해결 | datetime deprecation 수정 |
| 2 | Confluence Database API 제약 | ✅ 해결 | PostgreSQL PlayRecordRepository 사용 |
| 3 | Markdown to Confluence 변환 | ✅ 해결 | markdown2 라이브러리 도입 |
| 4 | 인증/권한 mock 구현 | ✅ 해결 | JWT 인증 시스템 구현 |
| 5 | Alembic 마이그레이션 미완성 | ✅ 해결 | 3개 마이그레이션 체인 완성 |
| 6 | Render 배포 email-validator 누락 | ✅ 해결 | 명시적 의존성 추가 |

---

## ✅ 완료된 스프린트 (역순)

### Week 5 - 2026-01-16

**목표**: WF-06 스테이징 배포 및 검증 ✅ 달성

| 항목 | 상태 |
|------|------|
| CD 워크플로 staging 브랜치 지원 추가 | ✅ |
| email-validator 의존성 오류 해결 | ✅ |
| WF-06 Confluence Sync 스테이징 배포 성공 | ✅ |
| 9개 Confluence API 엔드포인트 테스트 통과 | ✅ |

**주요 성과**: v0.4.0 릴리스, WF-03/06 구현 완료, E2E 테스트 49개

---

### Week 4

**목표**: API 라우터 DB 연동 및 WF-02/04 구현 ✅ 달성

| 항목 | 상태 |
|------|------|
| 데이터베이스에 Signal 저장 | ✅ v0.3.0 |
| 웹 UI 기본 페이지 구현 | ✅ v0.3.0 |
| AXIS 디자인 시스템 타입 정의 | ✅ v0.3.0 |
| 데이터베이스에 Scorecard 저장 | ✅ v0.3.0 |
| 데이터베이스에 Brief 저장 | ✅ v0.3.0 |
| `/ax:triage` 실행 시 WF-04 성공 | ✅ v0.3.0 |
| Scorecard 100점 만점 평가 동작 | ✅ v0.3.0 |
| Brief 1-Page 포맷 자동 생성 | ✅ v0.3.0 |
| pytest 전체 테스트 통과 (80%+ 커버리지) | ✅ v0.4.0 |

---

## ✅ 완료된 Phase (역순)

### Phase 2.5: CI/CD & Infrastructure (완료) - v0.4.0

| 카테고리 | 완료 항목 |
|----------|----------|
| GitHub Actions | frontend.yml, ci-backend.yml, cd-backend.yml |
| Cloudflare | Pages, D1 데이터베이스, 마이그레이션 |
| Render | render.yaml, Deploy Hook |
| GitHub Secrets | 4개 설정 완료 |
| 기타 | 로컬 .env, GitHub Flow 브랜치 전략 |

---

### Phase 2: Core Integration (완료) - v0.2.0 ~ v0.3.0

| 카테고리 | 완료 항목 |
|----------|----------|
| Claude Agent SDK | Agent 인스턴스, MCP 도구 연동, 세션 관리 |
| WF-01 Seminar | Pydantic 모델, Activity/Signal 생성, AAR, Confluence |
| 데이터베이스 | PostgreSQL, SQLAlchemy 5개 테이블, Alembic, CRUD |
| 테스트 | Runner 17개, EventManager 12개, Workflow 12개 |

---

### Phase 1: Scaffolding (완료)

| 카테고리 | 완료 항목 |
|----------|----------|
| 프로젝트 구조 | 에이전트 8개, Skills 6개, Commands 5개 |
| 스키마 | JSON Schema 모델 7개, 워크플로우 골격 6개 |
| 백엔드 | FastAPI API 라우터 4개, Confluence MCP, pytest |

---

## 📊 전체 진행률

| Phase | 완료 | 미완료 | 완료율 |
|-------|------|--------|--------|
| Phase 1 | 9 | 0 | 100% |
| Phase 2 | 19 | 0 | 100% |
| Phase 2.5 | 11 | 0 | 100% |
| Phase 3 | 36 | 1 | 97% |
| Phase 4 | 17 | 1 | 94% |
| **Phase 5 (Evals)** | **0** | **18** | **0%** |
| Week 6 | 14 | 5 | 74% |
| **전체 (PoC)** | **106** | **7** | **94%** |
| **전체 (Evals 포함)** | **106** | **25** | **81%** |

---

## 📅 Evals 플랫폼 로드맵

```
Week 7-8: Phase 5.0 MVP 시작
├── Task/Suite YAML 스키마 정의
├── 핵심 엔터티 모델 (Pydantic + SQLAlchemy)
├── DB 마이그레이션
└── Eval Harness 기본 구현

Week 9-10: Phase 5.0 MVP 완료
├── Deterministic Graders (pytest/ruff/mypy)
├── Transcript 저장 + 뷰어 API
├── CI 게이팅 (regression suite)
└── 에이전트별 기본 Task 작성

Week 11+: Phase 5.1 신뢰성 강화
├── LLM-as-Judge grader
├── 인간 보정 워크플로
├── pass@k / pass^k 리포트
└── 비용/지연 대시보드
```
