# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- **WF-06 Confluence Sync 워크플로 구현** ✨
  - 데이터 모델 (SyncTargetType, SyncAction, SyncTarget, SyncInput, SyncResult, SyncOutput)
  - 페이지 포맷터 (Signal, Scorecard, Brief, Activity Markdown 페이지)
  - MockConfluenceClient (create/update/append 페이지)
  - ConfluenceSyncPipeline (5단계: 검증 → 콘텐츠 준비 → 동기화 → 테이블 업데이트 → 확인)
  - ConfluenceSyncPipelineWithEvents (AG-UI 실시간 이벤트)
  - ConfluenceSyncPipelineWithDB (DB 연동, page_id 캐싱, sync_from_db)
  - API 엔드포인트 5개 (`/confluence-sync`, `/confluence-sync/signal`, `/confluence-sync/brief`, `/confluence-sync/activity-log`, `/confluence-sync/preview`)
  - workflows.py 병합 충돌 해결
  - 단위 테스트 45개 통과

- **WF-03 VoC Mining 워크플로 구현** ✨
  - 다양한 데이터 소스 지원 (CSV, Excel, API, 텍스트)
  - VoC 데이터 핸들러 (`voc_data_handlers.py`)
  - 3단계 파이프라인 계층 (기본, Events, DB)
  - 5단계 처리 흐름 (로딩 → 전처리 → 테마 추출 → Signal 생성 → Brief 후보)
  - API 엔드포인트 (`/voc-mining`, `/voc-mining/preview`)
  - Runner 연동 (`_run_voc_mining`)
  - 단위 테스트 24개 통과

- **Vector Search API** ✨
  - `/api/search/similar`: 유사 엔티티 검색
  - `/api/search/query`: RAG 기반 자연어 검색
  - OntologyService: 인덱싱 및 벡터 검색 통합
  - RAGService: 검색 + LLM 답변 생성
  - CLI 스크립트: `ax-index-entities` 엔티티 인덱싱

### Fixed

- **Render 배포 빌드 호환성 개선** 🔧
  - `asyncpg` → `psycopg[binary]` 교체 (C 빌드 불필요)
  - PostgreSQL 드라이버 URL 변경 (`postgresql+psycopg`)
  - Render 무료 플랜에서 빌드 실패 문제 해결

### Added

- **Teams MCP 서버** ✨
  - `teams.send_message`: 채널에 텍스트 메시지 전송
  - `teams.send_notification`: 알림 전송 (info/success/warning/error 레벨)
  - `teams.send_card`: Adaptive Card 전송
  - `teams.request_approval`: 승인 요청 카드 전송
  - `teams.send_kpi_digest`: KPI Digest 카드 전송
  - AgentRuntime 연동 (12개 MCP 도구: Confluence 7개 + Teams 5개)
  - 단위 테스트 28개

- **Cloudflare Pages 정적 배포** ✨
  - Next.js static export 설정 (`output: 'export'`)
  - wrangler.toml Pages 배포 설정
  - 동적 라우트를 모달 기반으로 전환 (Cloudflare Pages 호환)

- **상세 보기 모달 컴포넌트** ✨
  - `SignalDetailModal`: Signal 상세 정보, Triage/Brief 액션
  - `ScorecardDetailModal`: Scorecard 점수, 5개 차원 분석
  - `BriefDetailModal`: Brief 전체 내용, Approve/Validation 액션
  - `PlayDetailModal`: Play 상세 정보, Timeline, Sync 액션

- **ax-wrap-up Skill 추가** ✨
  - 작업 정리 자동화 Skill (`/ax:wrap-up`)
  - SSDD 원칙에 따른 문서 업데이트 확인
  - 테스트 실행 후 통과 시 Git 커밋
  - `.claude/skills/ax-wrap-up/SKILL.md`
  - `.claude/commands/ax_wrap_up.md`

- **CI/CD 파이프라인 구축** ✨
  - GitHub Actions 워크플로우 3개 (frontend.yml, ci-backend.yml, cd-backend.yml)
  - Cloudflare Pages 프로젝트 (`ax-discovery-portal.pages.dev`)
  - Cloudflare D1 데이터베이스 (`ax-discovery-db`, APAC/ICN 리전)
  - D1 마이그레이션 (5개 테이블, 10개 인덱스)
  - Render 백엔드 배포 설정 (`render.yaml`)
  - wrangler.toml 설정
  - D1 HTTP API 클라이언트 (`backend/integrations/cloudflare_d1/client.py`)
- GitHub Flow 브랜치 전략 적용
  - main: 프로덕션 브랜치
  - feature/*: 기능 개발 브랜치
  - PR 기반 코드 리뷰

- **Ontology 기반 Knowledge Graph 구조** ✨
  - Entity 모델 (12종 EntityType: Signal, Topic, Scorecard, Brief, Customer, Technology, Competitor, Industry, Evidence, Source, ReasoningStep, Play)
  - Triple 모델 (15종 PredicateType: has_pain, has_scorecard, similar_to, targets, supported_by, leads_to 등)
  - SPO (Subject-Predicate-Object) 구조 Triple Store
  - 3방향 인덱스 (SPO, POS, OSP) 최적화
- Ontology API 라우터 (`/api/ontology`)
  - `POST /entities`: 엔티티 생성
  - `GET /entities/{id}`: 엔티티 조회
  - `GET /entities`: 엔티티 목록 (타입/검색 필터)
  - `POST /triples`: 관계 생성
  - `GET /triples`: SPO 패턴 쿼리
  - `GET /graph/{id}`: 그래프 탐색 (depth 지정)
  - `GET /path/{src}/{dst}`: 경로 탐색 (BFS)
  - `GET /similar/{id}`: 유사 엔티티 검색
  - `GET /stats`: 온톨로지 통계
- XAI (설명가능한 AI) API 라우터 (`/api/xai`)
  - `GET /explain/scorecard/{id}`: Scorecard 평가 근거 설명
  - `GET /trace/signal/{id}`: Signal 출처 추적
  - `GET /confidence/{id}`: 신뢰도 분석
  - `GET /evidence-chain/{id}`: Evidence Chain 조회
  - `GET /reasoning-path/{id}`: 추론 경로 조회
- OntologyRepository: Entity/Triple CRUD + 그래프 탐색 기능
  - `get_entity_graph()`: 엔티티 중심 그래프 조회
  - `find_path()`: BFS 최단 경로 탐색
  - `get_similar_entities()`: similar_to 관계 기반 유사 엔티티
  - `get_reasoning_path()`: leads_to 관계 역추적
- Alembic 마이그레이션 (entities, triples 테이블)

- Scorecard API 라우터 DB 연동
  - `GET /api/scorecard`: 목록 조회 (decision, min_score, max_score 필터)
  - `GET /api/scorecard/{signal_id}`: Signal의 Scorecard 조회
  - `POST /api/scorecard`: 수동 Scorecard 생성 (DB 저장)
  - `POST /api/scorecard/evaluate/{signal_id}`: 평가 시작 (AI/수동)
  - `GET /api/scorecard/stats/distribution`: 점수 분포 통계
- Scorecard 리포지토리 확장
  - `get_multi_filtered()`: 필터링된 목록 조회
  - `get_distribution_stats()`: GO/PIVOT/HOLD/NO_GO 분포 및 Red-flag 비율
- Brief API 라우터 DB 연동
  - `GET /api/brief`: 목록 조회 (status, owner 필터)
  - `GET /api/brief/{brief_id}`: Brief 상세 조회
  - `POST /api/brief`: 수동 Brief 생성 (DB 저장)
  - `POST /api/brief/generate/{signal_id}`: Brief 자동 생성 (AI)
  - `POST /api/brief/{brief_id}/approve`: Brief 승인 + Confluence 게시
  - `POST /api/brief/{brief_id}/start-validation`: Validation 시작
  - `POST /api/brief/{brief_id}/complete-validation`: Validation 완료 (S3 전환)
  - `GET /api/brief/stats`: 상태별 통계
- Brief 리포지토리 확장
  - `update_status()`: 상태 업데이트 + Confluence URL 설정

- PlayDashboard API 라우터 DB 연동
  - `GET /api/play`: 목록 조회 (status, owner 필터, 페이지네이션)
  - `GET /api/play/{play_id}`: Play 상세 조회
  - `GET /api/play/{play_id}/timeline`: Play 타임라인 조회
  - `POST /api/play`: Play 생성 (DB 저장)
  - `PATCH /api/play/{play_id}`: Play 업데이트 (status, next_action, due_date, owner)
  - `POST /api/play/{play_id}/increment/{metric}`: 지표 증가 (activity, signal, brief, s2, s3)
  - `POST /api/play/{play_id}/sync`: Confluence 동기화 (TODO)
  - `GET /api/play/kpi/digest`: KPI 요약 리포트 (period별 목표 대비 실적)
  - `GET /api/play/kpi/alerts`: 지연/병목 경고 (Yellow/Red, 기한초과, 7일 비활동)
  - `GET /api/play/leaderboard`: Play 성과 순위
- PlayRecord 리포지토리 확장
  - `get_multi_filtered()`: 필터링된 목록 조회 (status, owner, 페이지네이션)
  - `get_stats()`: 전체 통계 (Play수, Activity/Signal/Brief/S2/S3 합계)
  - `get_kpi_digest()`: KPI 요약 (주간/월간 목표 대비 실적, 상태별 분포)
  - `get_alerts()`: 경고 조회 (Yellow/Red Play, 기한초과, 비활동)
  - `update_status()`: 상태 업데이트 (next_action, due_date 포함)
  - `get_timeline()`: 타임라인 조회 (TODO: ActionLog 연동)
  - `get_leaderboard()`: 성과 순위 (Signal 기준 상위 Play)

- WF-02 Interview-to-Brief 워크플로 구현
  - `InterviewToBriefPipeline`: 기본 파이프라인 클래스
  - `InterviewToBriefPipelineWithEvents`: AG-UI 이벤트 발행 버전
  - `InterviewToBriefPipelineWithDB`: DB 연동 버전
  - Signal 추출 로직 (Pain Point 키워드 기반)
  - Scorecard 평가 로직 (5차원 100점 평가)
  - Brief 초안 생성 로직 (승인 대기)
  - Red Flag 탐지 (데이터 접근불가, Buyer 부재, 규제 이슈)
  - 4단계 워크플로: Signal 추출 → Scorecard 평가 → Brief 생성 → DB 저장
- WF-02 API 엔드포인트
  - `POST /api/stream/workflow/WF-02`: SSE 스트리밍 실행
  - `POST /api/workflows/interview-to-brief`: REST API 실행 (DB 저장 포함)
  - `POST /api/workflows/interview-to-brief/preview`: Signal 추출 미리보기

- WF-04 Inbound Triage 워크플로 구현
  - `InboundTriagePipeline`: 기본 파이프라인 클래스
  - `InboundTriagePipelineWithEvents`: AG-UI 이벤트 발행 버전
  - `InboundTriagePipelineWithDB`: DB 연동 버전
  - Signal 생성 로직 (Intake Form → Signal)
  - 중복 체크 알고리즘 (Jaccard 유사도 기반, 임계값 0.7)
  - Play 라우팅 로직 (키워드 기반 자동 배정)
  - Scorecard 초안 생성 (5차원 100점 평가 재사용)
  - SLA 트래킹 (URGENT: 24h, NORMAL: 48h, LOW: 72h)
  - 5단계 워크플로: Signal 생성 → 중복 체크 → Play 라우팅 → Scorecard 생성 → SLA 설정
- WF-04 API 엔드포인트
  - `POST /api/stream/workflow/WF-04`: SSE 스트리밍 실행
  - `POST /api/workflows/inbound-triage`: REST API 실행 (DB 저장 포함)
  - `POST /api/workflows/inbound-triage/preview`: Play 라우팅/SLA 미리보기

- WF-05 KPI Digest 워크플로 구현
  - `KPIDigestPipeline`: 기본 파이프라인 클래스
  - `KPIDigestPipelineWithEvents`: AG-UI 이벤트 발행 버전
  - `KPIDigestPipelineWithDB`: DB 연동 버전
  - 주간/월간 기간 계산 (calculate_period_range)
  - PoC 목표 기준 정의 (Activity 20+/주, Signal 30+/주, Brief 6+/주, S2 2~4/주)
  - KPI 메트릭 집계 (Activity, Signal, Brief, S2, S3, 원천/채널별 분포)
  - 리드타임 계산 (Signal→Brief ≤7일, Brief→S2 ≤14일)
  - 경고 생성 (UNDER_TARGET, LEAD_TIME_EXCEEDED, PLAY_DELAYED)
  - 경고 심각도 (INFO: ≥80%, YELLOW: ≥50%, RED: <50%)
  - Top Plays 선정 (성과 우수 Play 순위)
  - 추천 사항 자동 생성 (경고 기반 개선 권고)
  - Play 상태 요약 (Green/Yellow/Red 분포)
  - 6단계 워크플로: 기간 계산 → 메트릭 집계 → 리드타임 계산 → 경고 생성 → Top Plays → 추천 사항
- WF-05 API 엔드포인트
  - `GET /api/stream/workflow/WF-05`: SSE 스트리밍 실행
  - `GET /api/workflows/kpi-digest`: REST API 실행 (DB 연동)
  - `GET /api/workflows/kpi-digest/summary`: 요약 미리보기 (Mock 데이터)
- WF-05 단위 테스트 31개 추가
  - TestPeriodRangeCalculation (3개)
  - TestAchievementCalculation (5개)
  - TestSeverityDetermination (3개)
  - TestPOCTargets (2개)
  - TestKPITarget (1개)
  - TestAlertGeneration (3개)
  - TestTopPlays (2개)
  - TestRecommendationsGeneration (4개)
  - TestKPIDigestPipeline (6개)
  - TestKPIDigestPipelineIntegration (2개)

### In Planning
- Confluence Database API 구현 (db_query, db_upsert_row)
- AI Agent 기반 Scorecard 평가 (LLM 활용)
- AI Agent 기반 Brief 생성 (LLM 활용)
- 모바일 앱 (PWA/React Native)

---

## [0.3.0] - 2026-01-14

### Added - PostgreSQL 데이터베이스 연동

- SQLAlchemy 2.0 비동기 ORM 통합
- 5개 테이블 정의 (signals, scorecards, opportunity_briefs, play_records, action_logs)
- Enum 타입 (SignalSource, SignalChannel, SignalStatus, Decision, NextStep 등)
- JSON/JSONB 필드 (evidence, kpi_hypothesis, dimension_scores 등)
- 외래키 관계 및 인덱스 설정
- TimestampMixin (created_at, updated_at 자동 관리)

### Added - Alembic 마이그레이션 시스템

- 비동기 마이그레이션 환경 설정
- 초기 스키마 마이그레이션 준비
- Enum 타입 자동 생성 지원

### Added - CRUD 저장소 패턴

- CRUDBase 제네릭 클래스
- Signal, Scorecard, Brief, PlayRecord 저장소 구현
- ID 자동 생성 (SIG-YYYY-NNN, SCR-YYYY-NNN, BRF-YYYY-NNN 형식)
- 필터링 및 페이지네이션 지원
- 통계 쿼리 (get_stats)

### Added - Agent Runtime 단위 테스트 (80%+ 커버리지 목표)

- 17개 Runner 테스트 (에이전트 로딩, MCP 연결, 세션 관리, 워크플로 라우팅)
- 12개 EventManager 테스트 (이벤트 발행/구독, 싱글톤, 스트리밍)
- 12개 Workflow 테스트 (메타데이터 추출, Activity 생성, AAR 템플릿, Confluence 업데이트)
- pytest fixtures (mock_env, sample_agent_markdown, mock_confluence_mcp 등)
- AsyncMock 및 httpx Mock 패턴

### Added - AXIS 디자인 시스템 (SSDD 완료)

#### Phase 1: 타입/이벤트 스키마 정의

- `packages/shared/types/src/agui-events.ts` - AG-UI 이벤트 타입 (18종)
- `packages/shared/types/src/a2ui-surfaces.ts` - A2UI Surface 타입 (10종)

#### Phase 2: 백엔드 SSE 구현

- `backend/agent_runtime/event_manager.py` - 세션 이벤트 관리자
- `backend/agent_runtime/event_types.py` - Python 이벤트 dataclass
- `backend/api/routers/stream.py` - SSE 엔드포인트 (`/api/stream/workflow/WF-01`)
- `pyproject.toml`에 `sse-starlette>=2.2.1` 의존성 추가

#### Phase 3: Agentic UI 컴포넌트 (8종)

- `AgentRunContainer` - 워크플로 실행 컨테이너
- `StepIndicator` - 단계 진행률 표시
- `StreamingText` - 실시간 텍스트 스트리밍
- `SurfaceRenderer` - A2UI Surface 렌더링
- `ActivityPreviewCard` - Activity 미리보기 (WF-01)
- `AARTemplateCard` - AAR 템플릿 표시
- `ApprovalDialog` - Human-in-the-Loop 승인
- `ToolCallCard` - 도구 호출 상태

#### Phase 4: 프론트엔드 통합

- `packages/shared/api-client/src/hooks/useAgentStream.ts` - SSE 구독 훅
- `apps/web/src/stores/agentStore.ts` - Zustand 상태 관리
- `apps/web/src/app/seminar/page.tsx` - 세미나 등록 페이지

#### Phase 5: WF-01 이벤트 통합

- `wf_seminar_pipeline.py`에 `SeminarPipelineWithEvents` 클래스 추가
- 단계별 이벤트 발행 (run_started, step_started/finished, surface, run_finished)

#### Phase 6: Human-in-the-Loop

- `ApprovalDialog` - 위험도 4단계 표시 + 변경사항 diff
- `ToolCallCard` - 도구 호출 상태 표시 + 인자/결과

### Added - 모노레포 구조

- pnpm + Turbo 기반 모노레포 설정
- `apps/web` - Next.js 15 웹앱
- `packages/ui` - @ax/ui 컴포넌트 라이브러리
- `packages/shared/types` - @ax/types 타입 정의
- `packages/shared/api-client` - @ax/api-client API 클라이언트
- `packages/shared/utils` - @ax/utils 유틸리티
- `packages/shared/config` - @ax/config 설정

### Added - CI/CD

- `.github/workflows/frontend.yml` - 프론트엔드 CI/CD
- `.github/workflows/ci-backend.yml` - 백엔드 CI
- `.github/workflows/cd-backend.yml` - 백엔드 CD

### Added - 웹 페이지

- `/` - 메인 대시보드
- `/inbox` - Signal 관리 (Triage)
- `/seminar` - 세미나 등록 (WF-01)
- `/scorecard` - Scorecard 평가
- `/brief` - Brief 관리
- `/plays` - Play 대시보드

### Changed

- API 라우터 DB 연동
  - `backend/api/routers/inbox.py`: ACTIVITY_STORE 제거, Signal CRUD 연동
  - GET /api/inbox: 실제 DB 조회 및 필터링
  - POST /api/inbox: DB 저장 및 Signal ID 자동 생성
  - GET /api/inbox/stats/summary: 실제 통계 쿼리
- Pydantic 모델 개선
  - SignalCreate: pain 필수 필드 추가, kpi_hypothesis 지원
  - SignalResponse: from_attributes 설정으로 ORM 호환
- 의존성 추가
  - `asyncpg>=0.30.0` (PostgreSQL 비동기 드라이버)
  - `sqlalchemy[asyncio]>=2.0.0` (비동기 ORM)
  - `alembic>=1.14.0` (마이그레이션)
  - `pytest-mock>=3.12.0` (Mock 지원)
  - `pytest-httpx>=0.30.0` (httpx Mock)

### Fixed

- Signal 생성 API 스키마 정합성 (description → pain)
- DB 세션 의존성 주입 (get_db)

### Removed

- ACTIVITY_STORE 인메모리 저장소 (DB로 대체)

---

## [0.2.0] - 2026-01-14

### Added

- Claude Agent SDK 통합 완료
  - `claude-agent-sdk>=0.1.19` 의존성 추가
  - Agent 로딩 시스템 구현 (.claude/agents/*.md 파싱)
  - MCP 서버 연동 (Confluence 도구 7개 래핑)
  - 세션 관리 개선 (ClaudeSDKClient 인스턴스 포함)
  - 자동 세션 정리 (1시간 타임아웃)
  - FastAPI lifespan에 Agent Runtime 초기화 통합
- WF-01 Seminar Pipeline 완전 구현
  - `backend/agent_runtime/workflows/wf_seminar_pipeline.py` 구현
  - Pydantic 모델 기반 입력/출력 정의
  - Confluence Live doc 업데이트 기능
  - Signal 추출 및 AAR 템플릿 생성

### Changed

- `backend/agent_runtime/runner.py` 대폭 수정 (SDK 통합)
  - `_load_agents()` 메서드 구현
  - `_connect_mcp_servers()` 메서드 추가
  - `create_session()` 메서드 SDK 연동
  - `_cleanup_old_sessions()` 메서드 추가
- `backend/api/main.py` lifespan 함수 수정
  - Agent Runtime 초기화 코드 추가
  - stream router 임시 제거 (dataclass 오류 해결)
- `pyproject.toml` 빌드 설정 개선
  - Hatchling packages 경로 명시

### Fixed

- pip install 실패 문제 해결 (Hatchling 패키지 경로 설정)
- FastAPI 서버 시작 실패 문제 해결 (stream router 제거)
- JSON 파싱 실패 시 fallback 로직 추가 (graceful degradation)

### Removed

- stream router 임시 제거 (event_types.py dataclass 오류)

---

## [0.1.0] - 2025-01-14

### Added

- 프로젝트 초기 스캐폴딩
- 6개 에이전트 정의 (orchestrator, external_scout, scorecard_evaluator, brief_writer, confluence_sync, governance)
- 5개 Skills (ax-scorecard, ax-brief, ax-sprint, ax-seminar, ax-confluence)
- 4개 Commands (/ax:seminar-add, /ax:triage, /ax:brief, /ax:kpi-digest)
- 7개 JSON Schema 데이터 모델 (signal, scorecard, brief, validation, pilot_ready, play_record, action_log)
- 6개 워크플로우 골격 (WF-01~06)
- FastAPI 백엔드 API 라우터 (inbox, scorecard, brief, play_dashboard)
- Confluence MCP 서버 (페이지 CRUD 기능)
- pytest 테스트 케이스
- 프로젝트 문서 (README.md, CLAUDE.md, docs/scaffold.md)

### Known Issues

- Claude Agent SDK 미연동 (import 주석 처리)
- 데이터베이스 미연동 (API 더미 응답)
- Confluence Database API 미구현 (스텁 상태)
- Teams 연동 미구현
- 웹/모바일 UI 미구현
