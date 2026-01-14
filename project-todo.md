# AX Discovery Portal - Project TODO

> 프로젝트 진행 상황 및 다음 단계

**현재 버전**: 0.4.0
**마지막 업데이트**: 2026-01-15

---

## ✅ Phase 1: Scaffolding (완료)

### 완료 항목
- [x] 프로젝트 구조 생성
- [x] 6개 에이전트 정의 (orchestrator, external_scout, scorecard_evaluator, brief_writer, confluence_sync, governance)
- [x] 5개 Skills 정의 (ax-scorecard, ax-brief, ax-sprint, ax-seminar, ax-confluence)
- [x] 4개 Commands 정의 (/ax:seminar-add, /ax:triage, /ax:brief, /ax:kpi-digest)
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

### 우선순위 3: 고급 기능

- [x] **Ontology 기반 Knowledge Graph** ✅ v0.4.0
  - [x] Entity 모델 (12종 EntityType)
  - [x] Triple 모델 (15종 PredicateType, SPO 구조)
  - [x] OntologyRepository (CRUD + 그래프 탐색)
  - [x] Ontology API 라우터 (9개 엔드포인트)
  - [x] XAI API 라우터 (5개 엔드포인트)
  - [x] Alembic 마이그레이션
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
- [ ] Teams 연동 (MCP 서버)

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

### 미완료 항목
- [ ] 페이지별 API 연동 완성 (Scorecard, Brief, Play)
- [ ] 모바일 앱 (PWA/React Native)

---

## 🐛 알려진 이슈

1. **Stream Router**: event_types.py dataclass 오류로 임시 제거 (비우선 기능)
2. **Confluence Database API**: Confluence Cloud API의 Database 기능 제약 → 대안 필요 (페이지 테이블 우회 또는 Postgres 사용)
3. **Markdown to Confluence 변환**: 현재 간단한 HTML 래핑만 구현 → 완전한 변환 라이브러리 필요
4. **인증/권한**: 현재 mock 구현, 프로덕션용 JWT 인증 필요
5. **Alembic 마이그레이션**: 초기 스키마 생성 필요 (`alembic revision --autogenerate -m "Initial schema"`)

---

## 📝 다음 스프린트 (Week 4)

**목표**: 나머지 API 라우터 DB 연동 및 WF-02/04 구현

**작업 항목**:

1. PostgreSQL 마이그레이션 실행 (`alembic upgrade head`)
2. Scorecard, Brief, PlayDashboard API 라우터 DB 연동
3. 통합 테스트 작성 (API + DB)
4. WF-02 Interview-to-Brief 워크플로 구현
5. WF-04 Inbound Triage 워크플로 구현
6. Scorecard 평가 로직 구현
7. Brief 생성 로직 구현

**성공 조건**:

- [x] 데이터베이스에 Signal 저장 ✅ v0.3.0
- [x] 웹 UI 기본 페이지 구현 ✅ v0.3.0
- [x] AXIS 디자인 시스템 타입 정의 ✅ v0.3.0
- [x] 데이터베이스에 Scorecard 저장 ✅ v0.3.0
- [x] 데이터베이스에 Brief 저장 ✅ v0.3.0
- [x] `/ax:triage` 실행 시 WF-04 성공 ✅ v0.3.0
- [x] Scorecard 100점 만점 평가 동작 ✅ v0.3.0
- [x] Brief 1-Page 포맷 자동 생성 ✅ v0.3.0
- [ ] pytest 전체 테스트 통과 (80%+ 커버리지)
