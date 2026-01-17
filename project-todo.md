# AX Discovery Portal - Project TODO

> 프로젝트 진행 상황 및 다음 단계

**현재 버전**: 0.5.0
**마지막 업데이트**: 2026-01-16

---

## ✅ Phase 1: Scaffolding (완료)

### 완료 항목
- [x] 프로젝트 구조 생성
- [x] 8개 에이전트 정의 (orchestrator, external_scout, interview_miner, voc_analyst, scorecard_evaluator, brief_writer, confluence_sync, governance)
- [x] 6개 Skills 정의 (ax-scorecard, ax-brief, ax-sprint, ax-seminar, ax-confluence, ax-wrap-up)
- [x] 5개 Commands 정의 (/ax:seminar-add, /ax:triage, /ax:brief, /ax:kpi-digest, /ax:wrap-up)
- [x] 7개 JSON Schema 모델 (signal, scorecard, brief, validation, pilot_ready, play_record, action_log)
- [x] 6개 워크플로우 골격 (WF-01~06)
- [x] FastAPI 백엔드 API 라우터 4개
- [x] Confluence MCP 서버 페이지 관리 기능
- [x] pytest 테스트 케이스

---

## ✅ Phase 2: Core Integration (완료)

### 우선순위 1: 필수 기능 ✅

- [x] Claude Agent SDK 통합 ✅ v0.2.0
  - [x] Agent 인스턴스 생성 및 초기화 (.claude/agents/*.md 파싱)
  - [x] MCP 도구 연동 (Confluence 7개 도구)
  - [x] 세션 관리 구현 (ClaudeSDKClient, 자동 정리)
- [x] WF-01 Seminar Pipeline 구현 ✅ v0.2.0
  - [x] Pydantic 모델 정의 (SeminarInput/Output)
  - [x] Activity 생성 로직
  - [x] Signal 추출 로직
  - [x] AAR 템플릿 생성
  - [x] Confluence Live doc 업데이트
- [x] 데이터베이스 연동 ✅ v0.3.0
  - [x] PostgreSQL 설정 및 연결 (asyncpg + SQLAlchemy 2.0)
  - [x] SQLAlchemy 모델 정의 (5개 테이블: Signal, Scorecard, Brief, PlayRecord, ActionLog)
  - [x] Alembic 마이그레이션 설정 (비동기 환경)
  - [x] CRUD 저장소 패턴 구현 (CRUDBase + 4개 repository)
  - [x] API 라우터 DB 연동 (inbox.py: ACTIVITY_STORE 제거)
- [x] Agent Runtime 단위 테스트 ✅ v0.3.0
  - [x] 테스트 기반 설정 (conftest.py + fixtures)
  - [x] Runner 테스트 (17개: 에이전트 로딩, MCP, 세션, 워크플로)
  - [x] EventManager 테스트 (12개: 발행/구독, 싱글톤, 스트리밍)
  - [x] Workflow 테스트 (12개: 메타데이터, Activity, AAR, Confluence)

---

## ✅ Phase 2.5: CI/CD & Infrastructure (완료)

### 완료 항목 ✅ v0.4.0

- [x] GitHub Actions 워크플로우 설정
  - [x] frontend.yml (CI + CD 통합, Cloudflare Pages 배포)
  - [x] ci-backend.yml (ruff, mypy, pytest)
  - [x] cd-backend.yml (Render Deploy Hook)
- [x] Cloudflare 리소스 생성
  - [x] Pages 프로젝트 (`ax-discovery-portal.pages.dev`)
  - [x] D1 데이터베이스 (`ax-discovery-db`, APAC/ICN)
  - [x] D1 마이그레이션 적용 (5개 테이블, 10개 인덱스)
- [x] Render 백엔드 배포 설정
  - [x] render.yaml (Blueprint)
  - [x] Deploy Hook 연동
- [x] GitHub Secrets 설정
  - [x] CLOUDFLARE_ACCOUNT_ID
  - [x] CLOUDFLARE_API_TOKEN
  - [x] RENDER_PRODUCTION_DEPLOY_HOOK
  - [x] RENDER_STAGING_DEPLOY_HOOK
- [x] 로컬 환경변수 설정 (.env)
- [x] GitHub Flow 브랜치 전략 적용

---

## 🚧 Phase 3: Advanced Features (진행 중)

### 우선순위 2: 핵심 워크플로
- [x] Scorecard API 라우터 DB 연동 ✅ v0.3.0
- [x] Brief API 라우터 DB 연동 ✅ v0.3.0
- [x] PlayDashboard API 라우터 DB 연동 ✅ v0.3.0
- [x] WF-02 Interview-to-Brief 구현 ✅ v0.3.0
  - [x] Signal 추출 로직 (휴리스틱 기반, LLM 확장 가능)
  - [x] Scorecard 평가 로직 (5차원 100점 평가)
  - [x] Brief 초안 생성 로직 (승인 대기)
- [x] WF-04 Inbound Triage 구현 ✅ v0.3.0
  - [x] Signal 생성 로직 (Intake Form → Signal)
  - [x] 중복 체크 알고리즘 (Jaccard 유사도 기반)
  - [x] Play 라우팅 로직 (키워드 기반)
  - [x] Scorecard 초안 생성 (5차원 100점 평가)
  - [x] SLA 트래킹 (URGENT: 24h, NORMAL: 48h, LOW: 72h)
- [x] WF-03 VoC Mining 구현 ✅ v0.4.0
  - [x] VoC 데이터 핸들러 (CSV, Excel, API, 텍스트)
  - [x] 3단계 파이프라인 계층 (기본, Events, DB)
  - [x] 5단계 처리 흐름 (로딩→전처리→테마추출→Signal→Brief후보)
  - [x] API 엔드포인트 (`/voc-mining`, `/voc-mining/preview`)
  - [x] Runner 연동 (`_run_voc_mining`)
  - [x] 단위 테스트 24개 통과

### 우선순위 3: 고급 기능

- [x] **Ontology 기반 Knowledge Graph** ✅ v0.4.0 → v0.5.1 강화
  - [x] Entity 모델 (13종 EntityType)
  - [x] Triple 모델 (17종 PredicateType, SPO 구조)
  - [x] OntologyRepository (CRUD + 그래프 탐색)
  - [x] Ontology API 라우터 (9개 엔드포인트)
  - [x] XAI API 라우터 (5개 엔드포인트)
  - [x] Alembic 마이그레이션
  - [x] **P0 필드 마이그레이션** ✅ v0.5.1
    - [x] Entity Recency 필드 (published_at, observed_at, ingested_at)
    - [x] Entity Sync 필드 (last_synced_at, sync_status)
    - [x] Triple Lifecycle 필드 (status, assertion_type, evidence_span 등)
    - [x] 복합 인덱스 (status+predicate, status+assertion_type)
    - [x] ORGANIZATION ID 접두사 ORG- 매핑
- [ ] Confluence Database API 구현 (db_query, db_upsert_row)
- [x] 중복 Signal 체크 알고리즘 ✅ v0.3.0 (Jaccard 유사도 기반)
- [x] WF-05 KPI Digest 구현 ✅ v0.4.0
  - [x] 주간/월간 기간 계산
  - [x] KPI 메트릭 집계 (Activity, Signal, Brief, S2, S3)
  - [x] 리드타임 계산 (Signal→Brief ≤7일, Brief→S2 ≤14일)
  - [x] 경고 생성 (목표 미달, 리드타임 초과, 지연 Play)
  - [x] Top Plays 선정 (성과 우수 Play 순위)
  - [x] 추천 사항 생성 (AI 기반 개선 권고)
  - [x] 단위 테스트 31개 통과
- [x] WF-06 Confluence Sync 구현 ✅ v0.4.0
  - [x] 데이터 모델 (SyncTargetType, SyncAction, SyncTarget, SyncInput, SyncResult, SyncOutput)
  - [x] 페이지 포맷터 (Signal, Scorecard, Brief, Activity 페이지)
  - [x] MockConfluenceClient (create/update/append/get/search 페이지)
  - [x] ConfluenceSyncPipeline (5단계 동기화)
  - [x] ConfluenceSyncPipelineWithEvents (AG-UI 이벤트)
  - [x] ConfluenceSyncPipelineWithDB (DB 연동 + page_id 캐싱)
  - [x] API 엔드포인트 5개 (sync, signal, brief, activity-log, preview)
  - [x] **양방향 동기화** ✅
    - [x] 페이지 파서 (parse_signal_page, parse_scorecard_page, parse_brief_page)
    - [x] 페이지 타입 자동 감지 (detect_page_type)
    - [x] Confluence → DB import (import_from_confluence)
    - [x] 양방향 동기화 (bidirectional_sync)
    - [x] API 엔드포인트 4개 추가 (/import, /from-db, /bidirectional, /parse-preview)
  - [x] 단위 테스트 67개 통과
- [x] Teams 연동 (MCP 서버) ✅ v0.4.0
  - [x] TeamsMCP 클래스 구현 (5개 도구)
  - [x] Incoming Webhook 메시지 전송
  - [x] Adaptive Card 지원
  - [x] 승인 요청 카드
  - [x] KPI Digest 카드
  - [x] AgentRuntime 연동
  - [x] 단위 테스트 28개 통과
- [x] Slack 연동 (MCP 서버) ✅ v0.4.0
  - [x] SlackMCP 클래스 구현 (5개 도구)
  - [x] Incoming Webhook 메시지 전송
  - [x] Block Kit 지원
  - [x] 승인 요청 메시지
  - [x] KPI Digest 메시지
  - [x] AgentRuntime 연동
  - [x] 실제 Webhook 연동 테스트 완료
- [x] **Vector RAG 파이프라인** ✅ v0.4.0
  - [x] EmbeddingService (OpenAI text-embedding-3-small, 1536차원)
  - [x] VectorizeClient (Cloudflare Vectorize HTTP API)
  - [x] RAGService (임베딩 + 벡터 검색 + 컨텍스트 생성)
  - [x] OntologyService (Entity CRUD + 자동 인덱싱 훅)
  - [x] Search API 라우터 (시맨틱 검색, 중복 검사, RAG 컨텍스트)
  - [x] 배치 인덱싱 스크립트 (`ax-index-entities`)
  - [x] 단위 테스트 95개 통과

---

## 🚧 Phase 4: UI & UX (부분 완료)

### 완료 항목 ✅ v0.3.0
- [x] 모노레포 구조 (pnpm + Turborepo)
- [x] 웹 UI (Next.js 15)
  - [x] 메인 대시보드 (`/`)
  - [x] Inbox 페이지 (`/inbox`)
  - [x] Scorecard 페이지 (`/scorecard`)
  - [x] Brief 페이지 (`/brief`)
  - [x] Play Dashboard (`/plays`)
  - [x] 세미나 등록 페이지 (`/seminar`)
- [x] AXIS 디자인 시스템
  - [x] AG-UI 이벤트 타입 (18종)
  - [x] A2UI Surface 타입 (10종)
  - [x] Agentic UI 컴포넌트 (8종)
  - [x] SSE 실시간 스트리밍
- [x] 공유 패키지
  - [x] @ax/api-client (FastAPI 클라이언트)
  - [x] @ax/types (TypeScript 타입 정의)
  - [x] @ax/utils (유틸리티 함수)
  - [x] @ax/config (공통 설정)
  - [x] @ax/ui (shadcn/ui 컴포넌트)

### 추가 완료 항목 ✅ v0.4.0
- [x] 페이지별 API 연동 완성 (Inbox, Scorecard, Brief, Play, Seminar)

### 미완료 항목
- [ ] 모바일 앱 (PWA/React Native)

---

## 🐛 알려진 이슈

1. ~~**Stream Router**: event_types.py dataclass 오류로 임시 제거~~ ✅ 해결됨 (datetime deprecation 수정)
2. **Confluence Database API**: Confluence Cloud API의 Database 기능 제약 → 대안 필요 (페이지 테이블 우회 또는 Postgres 사용)
3. **Markdown to Confluence 변환**: 현재 간단한 HTML 래핑만 구현 → 완전한 변환 라이브러리 필요
4. ~~**인증/권한**: 현재 mock 구현, 프로덕션용 JWT 인증 필요~~ ✅ 해결됨 (JWT 인증 시스템 구현)
5. ~~**Alembic 마이그레이션**: 초기 스키마 생성 필요~~ ✅ 해결됨 (3개 마이그레이션 체인 완성)
6. ~~**Render 배포 오류**: email-validator 의존성 누락~~ ✅ 해결됨 (명시적 의존성 추가)

---

## ✅ 완료된 스프린트 (Week 5) - 2026-01-16

**목표**: WF-06 스테이징 배포 및 검증 ✅ 달성

**성공 조건** (4/4 완료):
- [x] CD 워크플로 staging 브랜치 지원 추가
- [x] email-validator 의존성 오류 해결
- [x] WF-06 Confluence Sync 스테이징 배포 성공
- [x] 9개 Confluence API 엔드포인트 테스트 통과

---

## ✅ 완료된 스프린트 (Week 4)

**목표**: 나머지 API 라우터 DB 연동 및 WF-02/04 구현 ✅ 달성

**성공 조건** (9/9 완료):
- [x] 데이터베이스에 Signal 저장 ✅ v0.3.0
- [x] 웹 UI 기본 페이지 구현 ✅ v0.3.0
- [x] AXIS 디자인 시스템 타입 정의 ✅ v0.3.0
- [x] 데이터베이스에 Scorecard 저장 ✅ v0.3.0
- [x] 데이터베이스에 Brief 저장 ✅ v0.3.0
- [x] `/ax:triage` 실행 시 WF-04 성공 ✅ v0.3.0
- [x] Scorecard 100점 만점 평가 동작 ✅ v0.3.0
- [x] Brief 1-Page 포맷 자동 생성 ✅ v0.3.0
- [x] pytest 전체 테스트 통과 (80%+ 커버리지) ✅ v0.4.0

---

## 📝 다음 스프린트 (Week 6 - PoC 마지막 주)

**목표**: PoC 완료 및 데모 준비

**테마**: v0.5.0 릴리스 - PoC 6주 목표 달성 검증 및 최종 발표

### 작업 항목

#### 1. PoC 목표 달성 검증 📊
- [ ] 실제 데이터 수집 시작 (Activity 20+, Signal 30+/주)
- [ ] WF-01~06 전체 파이프라인 E2E 테스트
- [ ] KPI Digest 리포트 생성 테스트 (`/ax:kpi-digest`)
- [ ] 리드타임 측정 (Signal→Brief ≤7일, Brief→S2 ≤14일)

#### 2. 데모 준비 🎬
- [x] 데모 시나리오 작성 (3개 핵심 플로우) ✅
  - docs/DEMO_SCENARIOS.md 작성
  - 세미나 등록 → Signal 생성 → Scorecard 평가
  - VoC 분석 → Brief 자동 생성 → Confluence 동기화
  - Inbound 요청 → Triage → S2 승인
- [x] 데모 데이터 준비 (샘플 Activity, Signal, Brief) ✅
  - docs/demo-data/ 디렉토리 생성
  - scenario1_seminar.json, scenario2_voc.csv, scenario3_inbound.json
  - api_calls.sh 데모 스크립트
- [x] 발표 자료 초안 (PoC 결과 요약) ✅
  - docs/POC_PRESENTATION.md 작성
  - 8개 섹션: Executive Summary, 개요, 성과, 아키텍처, 데모, KPI, 기술, 향후계획

#### 3. 문서화 완성 📚
- [x] 사용자 가이드 작성 (주요 워크플로 사용법) ✅ v0.4.0
  - docs/USER_GUIDE.md 작성
  - Quick Start, 6개 워크플로, 웹 UI, API, Claude Code 명령어, FAQ
- [x] Quick Start 가이드 (5분 내 시작) ✅ USER_GUIDE.md 섹션 1
- [x] FAQ 문서 (자주 묻는 질문) ✅ USER_GUIDE.md 섹션 7

#### 4. UI/UX 마무리 🎨
- [x] 대시보드 KPI 위젯 실데이터 연동 ✅
- [x] 에러 핸들링 UX 개선 (Toast 알림, 글로벌 에러 페이지) ✅
- [x] 모바일 반응형 레이아웃 확인 ✅

#### 5. 안정화 및 최적화 🔧
- [ ] 프로덕션 환경 모니터링 설정 (Sentry 알림)
- [ ] 성능 병목 점검 (느린 API 최적화)
- [ ] 마지막 버그 수정

### 성공 조건

- [ ] PoC 주간 목표 달성 검증
  - Activity 20+/주
  - Signal 30+/주
  - Brief 6+/주
  - S2 2~4/주
- [ ] 데모 시연 성공 (3개 시나리오)
- [x] 사용자 가이드 문서 완성 ✅ docs/USER_GUIDE.md
- [ ] v0.5.0 릴리스 및 태그

### 일정

| 일자 | 작업 |
|------|------|
| Day 1-2 | PoC 목표 달성 검증, 데이터 수집 |
| Day 3 | 데모 시나리오 작성, 데모 데이터 준비 |
| Day 4 | 사용자 가이드 작성, UI/UX 마무리 |
| Day 5 | 최종 점검, v0.5.0 릴리스, PoC 발표 |

---

## ✅ 완료된 스프린트 (Week 5) - 2026-01-16

**목표**: Production Readiness ✅ 달성

**테마**: v0.4.0 릴리스 - 스테이징/프로덕션 배포 완료

**주요 성과**:
- WF-03 VoC Mining, WF-06 Confluence Sync 구현 완료
- E2E 테스트 10개 시나리오 (49개 테스트 케이스)
- 스테이징/프로덕션 배포 및 검증 완료
- v0.4.0 릴리스 태그 생성

**미완료 → Week 6 이월**:
- 사용자 가이드 작성
- 대시보드 KPI 위젯 실데이터 연동
- 모바일 반응형 레이아웃 개선
