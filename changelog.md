# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.6.0] - 2026-01-18

### Added

- **LLM-as-Judge Grader (Phase 5.1)** 🤖
  - Claude API 기반 에이전트 출력 평가 채점기
  - 루브릭 기반 평가: 마크다운 형식 평가 기준 정의
  - 다중 기준 채점: 기준별 점수, 근거, 개선 제안 추출
  - 비용 최적화: 메모리 캐싱 (동일 입/출력 재평가 방지)
  - 토큰 사용량 추적 및 비용 계산
  - `backend/evals/graders/llm_judge.py`

### Improved

- **API 성능 최적화** ⚡
  - **activities.py**: DB 레벨 JSONB 필터링, 페이지네이션 도입 (O(N) → O(log N))
  - **evals.py**: N+1 쿼리 해결 (서브쿼리 + LEFT JOIN)
  - **ontology.py**: 배치 IN 쿼리, selectinload 활용 (40+ → 3 쿼리)
  - **opportunity.py**: 단일 GROUP BY 쿼리 통합 (11+ → 1 쿼리)

### Fixed

- **CI 워크플로 수정 (모든 워크플로 통과)** 🔧
  - **ruff lint 오류 19개 수정**: I001 import sorting, F401 unused import
  - **evals-regression.yml 워크플로 3가지 문제 해결**:
    - `timeout-minutes: ${{ fromJSON(env.TIMEOUT_MINUTES) }}` → `30` (env 컨텍스트 미지원)
    - `((suite_count++))` → `suite_count=$((suite_count + 1))` (bash exit code 문제)
    - `shopt -s globstar nullglob` 추가 (bash `**` glob 패턴 지원)
  - 52개 파일 ruff format 적용

- **테스트 격리 문제 해결 (184개 실패 → 891개 통과)** 🔧
  - `conftest.py`: structlog 테스트 환경 즉시 설정 (import 시점)
  - `reset_structlog_for_each_test` autouse fixture 추가
  - `test_ontology_modules.py`: GROUP BY 쿼리 mock 패턴 개선
    - `scalars().all()` 체인 지원 mock 헬퍼
    - `get_entity_graph`, `get_similar_entities`, `get_stats` 테스트 수정

- **외부 세미나 수집기 4개 복구** 🔧
  - OnOffMix: URL 패턴 및 HTML 파싱 로직 업데이트 (`/event/main/?interest=A0103`)
  - EventUs: Vue.js 렌더링 대응, suggest API로 전환
  - DevEvent: GitHub 마크다운 파싱 헬스체크 추가
  - RSS: 11개 기본 피드 URL 설정 (카카오, 네이버 D2, OpenAI 등)

- **KPI Digest API 응답 형식 수정** 🔧
  - `get_kpi_digest()` 반환값을 프론트엔드 `KPIDigest` 인터페이스와 일치하도록 수정
  - 필드: `activity_actual`, `signal_actual`, `brief_actual`, `s2_actual` 등

### Added

- **Sentry 프로덕션 모니터링** 📊
  - FastAPI/Starlette 통합으로 자동 에러 캡처 및 성능 모니터링
  - 환경별 설정: 개발(100% 트레이싱), 프로덕션(설정값 기반 샘플링)
  - 설정 필드: `sentry_dsn`, `sentry_traces_sample_rate`, `sentry_profiles_sample_rate`
  - `/health`, `/ready` 엔드포인트에 Sentry 상태 표시
  - `.env.example`에 Sentry 환경변수 예시 추가

- **외부 세미나 기능 확장** ✨
  - **수집기 헬스체크**: `/api/activities/health-check` 엔드포인트 추가
    - `CollectorHealthBar` UI 컴포넌트 (상태별 색상 표시, 5분 자동 새로고침)
    - OnOffMix/EventUs 수집기 상태 모니터링
  - **AI 채팅 세미나 추가**: ChatGPT 스타일 인터페이스
    - `/api/activities/chat` SSE 스트리밍 엔드포인트
    - `/api/activities/chat/confirm` 등록 확인 엔드포인트
    - `SeminarChatPanel` 채팅 UI 컴포넌트
    - 실시간 세미나 정보 추출 및 미리보기
  - **파일 업로드**: 드래그앤드롭 일괄 등록
    - `/api/activities/upload` 일괄 추출 엔드포인트
    - `FileUploadZone` UI 컴포넌트
    - `FileProcessor` 유틸리티 (이미지 OCR, PDF, DOCX, XLSX, CSV, JSON, 텍스트)
    - Claude Vision API 연동 이미지 처리
  - 새 UI 컴포넌트 3개 (activities.ts API 클라이언트 확장)

---

## [0.5.1] - 2026-01-18

### Added

- **AI 에이전트 평가(Evals) 플랫폼 Phase 5.0 MVP** 📊
  - **설계안 v1.0**: 핵심 개념 모델 정의 (Task, Trial, Transcript, Outcome, Grader, Eval Suite)
  - **Pydantic 모델 구현** (`backend/evals/`):
    - `models/enums.py`: 16개 열거형 (TaskType, TrialStatus, GraderType, ScoringMode 등)
    - `models/entities.py`: 9개 핵심 엔터티 (Suite, Task, Run, Trial, Transcript, Outcome, GraderResult, AggregatedMetrics, EvalSummary)
    - `models/configs.py`: 20+ 설정 모델 (TaskMetadata, GraderConfig, ScoringConfig 등)
    - `models/task.py`: TaskDefinition YAML 래퍼 + 헬퍼 메서드
    - `models/suite.py`: SuiteDefinition YAML 래퍼 + 게이트/알림 설정
  - **YAML 로더** (`loaders/yaml_loader.py`):
    - `load_task()`, `load_suite()`: YAML 파일 로드 및 Pydantic 검증
    - `discover_tasks()`, `discover_suites()`: 디렉토리 검색
    - `validate_task_yaml()`, `validate_suite_yaml()`: 스키마 검증
    - `load_tasks_from_suite()`: Suite에서 Task 일괄 로드
  - **DB 마이그레이션** (`backend/database/models/eval.py`):
    - 5개 Enum: EvalTaskType, EvalTrialStatus, EvalRunStatus, EvalSuitePurpose, EvalDecision
    - 7개 테이블: eval_suites, eval_tasks, eval_runs, eval_trials, eval_transcripts, eval_outcomes, eval_grader_results
    - 20개 인덱스: 성능 최적화를 위한 주요 컬럼 인덱싱
    - Alembic 마이그레이션 파일: `20260118_100000_add_evals_tables.py`
  - **JSON 스키마** (`evals/schemas/`): task.schema.json, suite.schema.json, grader.schema.json
  - **샘플 YAML** (`evals/tasks/`, `evals/suites/`): WF-01/02 테스트 케이스
  - **단위 테스트** (65개 통과):
    - `tests/unit/test_evals_models.py`: 32개 모델 테스트
    - `tests/unit/test_evals_loaders.py`: 33개 로더 테스트
  - **의존성**: `pyyaml>=6.0.0`, `types-PyYAML>=6.0.0` (dev)
  - **Eval Harness (실행기)** (`backend/evals/runners/`):
    - `TrialExecutor`: 단일 Trial 실행 (환경 설정, 에이전트 호출, Transcript/Outcome 캡처)
    - `TaskRunner`: k번 Trial 실행 + 채점 집계 (pass@k, pass^k 계산)
    - `SuiteRunner`: Suite 전체 실행 + 게이트 조건 검사
    - `RunnerConfig`, `TrialResult`, `TaskResult`, `RunResult` 결과 모델
  - **Deterministic Graders (채점기)** (`backend/evals/graders/`):
    - `PytestGrader`: pytest 실행 기반 채점
    - `RuffGrader`, `MypyGrader`: 정적 분석 기반 채점
    - `StateCheckGrader`: DB/파일/API/환경 상태 검증 (12개 체크 타입)
    - `TranscriptMetricsGrader`: 턴/도구호출/에러 메트릭 채점
    - `ToolCallCheckGrader`: 도구 호출 패턴 검증
    - `create_grader()`: 채점기 팩토리 함수
  - **Evals REST API** (`backend/api/routers/evals.py`):
    - Suite 관리: `GET /suites`, `GET /suites/{id}`, `POST /suites/sync`
    - Run 관리: `POST /runs`, `GET /runs`, `GET /runs/{id}`, `DELETE /runs/{id}`
    - Trial 조회: `GET /runs/{id}/trials`, `GET /trials/{id}`, `/transcript`, `/outcome`
    - 통계/분석: `GET /stats/summary`, `GET /stats/regression`
  - **mypy Pydantic 플러그인** 설정 추가 (`pyproject.toml`)
  - **CI 게이팅 (regression suite 자동 실행)** (`backend/evals/cli.py`):
    - CLI: `python -m backend.evals run --suite regression --parallel --k 5`
    - 옵션: `--suite`, `--task`, `--k`, `--parallel`, `--output` (summary/json/yaml)
    - `GateChecker`: pass_rate, required_tasks, min_score 조건 검사
    - GitHub Actions: `.github/workflows/evals-regression.yml` (PR/push/schedule 트리거)
    - 종료 코드: 0(PASS), 1(FAIL), 2(MARGINAL)
  - **6개 에이전트 Eval Tasks** (`backend/evals/tasks/`):
    - `orchestrator/`: workflow_completion, subagent_call_order, error_recovery, approval_flow (4개)
    - `external_scout/`: seminar_metadata_extraction, signal_pattern_detection, aar_template_generation, multi_source_collection (4개)
    - `scorecard_evaluator/`: five_dimension_accuracy, score_range_validation, red_flag_detection, recommendation_logic (4개)
    - `brief_writer/`: required_sections, confluence_page_creation, format_compliance, evidence_linking (4개)
    - `confluence_sync/`: sync_success_rate, data_integrity, conflict_resolution, batch_sync (4개)
    - `voc_analyst/`: theme_extraction_accuracy, coverage_validation, signal_generation, priority_ranking (4개)
    - 총 24개 Task YAML 파일
  - **Phase 5.0 MVP 완료**: 75% → 100% (8/8 항목)

- **Opportunity Stage 파이프라인 시스템** 🚀
  - **11단계 Stage 파이프라인**: DISCOVERY → IDEA_CARD → GATE1 → MOCKUP → GATE2 → BIZ_PLANNING → PILOT → PRE_PROPOSAL → HANDOFF + HOLD/DROP
  - **신규 모델 4개**:
    - `Opportunity`: 사업기회 엔티티 (current_stage, health_score, owner, dates)
    - `StageTransition`: 단계 전환 이력 추적 (trigger, decision, reason)
    - `ApprovalRequest`: HITL 승인 워크플로 (GATE 심사, 위험 도구)
    - `Task`: Play별 ToDoList 관리 (template_key, priority, due_date)
  - **PlayRecord 확장**: 목표/실적 필드 추가 (goal_*, actual_*), RAG 자동 계산
  - **API 라우터 2개**:
    - `stages.py` (821줄): Opportunity CRUD, Stage 전환, HITL 승인, Funnel 분석
    - `tasks.py` (370줄): Task CRUD, 템플릿 기반 생성, 일괄 완료
  - **서비스 4개**:
    - `TaskConverter`: 템플릿 기반 Task 자동 생성
    - `ApprovalService`: 승인 워크플로 관리
    - `NotificationService`: Teams/Slack 알림 (stub)
    - `PlaySyncTriggers`: Confluence 동기화 이벤트 발행
  - **DB 마이그레이션**: opportunities, stage_transitions, approval_requests 테이블
  - **API 클라이언트**: `packages/shared/api-client/src/endpoints/tasks.ts`

- **외부 세미나 수집 API 리팩토링** 🎯
  - Festa.io 서비스 종료(2025.01.31) 대응
    - `FestaCollector` DEPRECATED 처리 (빈 결과 반환 + 경고)
  - 새로운 수집기 4개 추가:
    - `OnOffMixCollector`: 온오프믹스 (웹 스크래핑)
    - `EventUsCollector`: 이벤터스 (웹 스크래핑)
    - `DevEventCollector`: GitHub brave-people/Dev-Event (마크다운 파싱)
    - `keywords.py`: AI/AX 키워드 상수 및 필터 유틸리티
  - 기본 수집 소스 변경: `rss, onoffmix, eventus, devevent, eventbrite`
  - AI/AX 키워드 기본 필터링 (상위 10개 키워드)
  - `wf_external_scout.py` 소스별 파라미터 처리 확장

- **Dev-Event 수집기 개선** 🔧
  - 마크다운 파싱 패턴 수정: `- __[제목](URL)__` 형식 지원
  - 분류 정보 추출 개선 (다음 줄 + 두 번째 다음 줄 검색)
  - 이미지 링크, GitHub 내부 링크 필터링
  - AI 관련 태그 확장: `data`, `데이터` 추가
  - 테스트 스크립트 Windows UTF-8 인코딩 수정

- **Markdown to Confluence 완전 변환 구현** 📄
  - `markdown2` 라이브러리 도입
  - Confluence Storage Format 완전 변환 지원:
    - 헤더 (h1~h6), 표 (`<table class="wrapped">`), 링크, 목록
    - 강조 (bold, italic), 취소선
    - 코드 블록 → Confluence `<ac:structured-macro>` 매크로
  - 테스트 15개 추가 (`tests/unit/test_confluence_mcp.py`)

### Fixed

- **Confluence Database API 제약 해결** 🔧
  - Confluence Cloud API는 Database 기능을 지원하지 않음
  - 해결: PostgreSQL 기반 `PlayRecordRepository` 활용
  - `db_query`, `db_upsert_row`, `db_insert_row` 메소드 Deprecated 처리
  - 대안 코드 안내 추가 (`play_record_repo`, `play_sync_service`)

- **외부 세미나 프론트엔드 페이지 구현** 📅
  - `apps/web/src/app/activities/page.tsx`: 세미나 목록 페이지
    - 소스 타입별 필터링 (RSS, Festa, Eventbrite, 수동)
    - 검색 기능 (제목, 설명, 주최자, 카테고리)
    - 페이지네이션
    - 통계 카드 (전체, 소스별 개수)
  - `packages/shared/api-client/src/endpoints/activities.ts`: Activities API 클라이언트
  - 메인 페이지에 "외부 세미나" 카드 추가 (`/activities` 링크)

- **실제 세미나 데이터 수집 (36건)**
  - RSS 피드: AWS 한국 블로그, 네이버 D2, 토스 테크
  - 키워드 필터링: AI, LLM, AWS, Cloud, ML 등
  - `.env` 세미나 수집 설정 추가 (`SEMINAR_RSS_FEEDS`, `SEMINAR_KEYWORDS`)

### Fixed

- **PostgreSQL JSON 쿼리 호환성 수정** 🔧
  - `backend/database/repositories/activity.py`: `json_extract` → Python 기반 필터링
  - `get_by_url`, `list_by_play`, `list_by_source_type`, `check_duplicate` 메서드 수정
  - PostgreSQL에서 JSON 필드 조회 시 발생하던 오류 해결

- **Confluence 페이지 자동 생성 및 연동** 📄
  - Confluence API를 통한 페이지 자동 생성
    - 프로젝트 현황 페이지 (Page ID: 753665)
    - Play 진행현황 DB (Page ID: 720899)
    - Action Log (Page ID: 786433)
  - 환경변수 설정:
    - `CONFLUENCE_SPACE_KEY=AB` (올바른 Space Key로 수정)
    - `CONFLUENCE_ACTION_LOG_PAGE_ID`, `CONFLUENCE_PLAY_DB_PAGE_ID`, `CONFLUENCE_PROJECT_STATUS_PAGE_ID`
  - Slack 웹훅 연동: Confluence 업데이트 알림 전송 (#ax-bd-alerts)

- **세미나-BD 온톨로지 통합 (WF-01 확장)** 🧠
  - `LLMExtractionService`: Claude API 기반 엔티티/관계 추출 (`llm_extraction_service.py`)
  - `EntityResolutionService`: 동일 엔티티 식별 및 병합 (`entity_resolution_service.py`)
  - `OntologyIntegrationService`: 추출 결과 → Entity/Triple 변환 (`ontology_integration_service.py`)
  - `SeminarPipelineWithOntology`: 10단계 온톨로지 통합 워크플로
    - URL → Activity Entity → LLM 추출 → Entity Resolution → Signal/Triple 생성
  - 프롬프트 로더: `.claude/prompts/*.md` 자동 로딩
  - Triple Validator 연동: 도메인/레인지 제약 검증
  - 단위 테스트 47개 + 통합 테스트 5개 (총 52개)

- **외부 세미나 수집 시스템 단위 테스트** 🧪
  - `tests/unit/test_activity_repository.py`: Activity 저장소 테스트 (17개)
  - `tests/unit/test_external_collectors.py`: RSS/Festa/Eventbrite 수집기 테스트 (35개)
  - `tests/unit/test_webhook_processor.py`: 웹훅 처리 및 서명 검증 테스트 (29개)
  - ActivityRepository SQLite/PostgreSQL 호환성 수정 (`json_value` 함수)

- **외부 세미나 수집 시스템 (WF-07: External Scout)** 🔍
  - 다중 소스 수집기 구현: RSS, Festa, Eventbrite
  - `ActivityRepository`: Activity 저장소 (Entity 테이블 기반)
  - `ExternalScoutPipeline`: 배치 수집 워크플로 (`wf_external_scout.py`)
  - 웹훅 엔드포인트: RSS/Festa/Eventbrite 실시간 이벤트 수신
  - API 엔드포인트:
    - `POST /api/workflows/external-scout`: 배치 수집 실행
    - `GET /api/activities`: Activity 목록 조회
    - `POST /api/webhooks/seminar/{source}`: 웹훅 수신
  - 환경변수: `SEMINAR_RSS_FEEDS`, `FESTA_API_KEY`, `EVENTBRITE_API_TOKEN` 등
  - 의존성 추가: `feedparser>=6.0.0`

- **대시보드 KPI 위젯 및 에러 핸들링 UX 개선** 🎨
  - 메인 대시보드에 실시간 KPI 위젯 추가 (주간 Activity, Signal, Brief, S2 현황)
  - 사이클 타임 표시 (Signal→Brief, Brief→S2 리드타임)
  - Toast 알림 시스템 추가 (sonner 라이브러리)
  - 글로벌 에러 페이지 추가 (`error.tsx`)
  - React Query 에러 핸들링 개선 (QueryCache, MutationCache)
  - alert() → toast 대체 (사용자 친화적 알림)
  - 모바일 반응형 레이아웃 개선 (패딩, 폰트, 그리드)

- **신규 Agent 추가 (interview_miner, voc_analyst)** 🤖
  - `interview_miner`: 인터뷰 노트 → Pain Point/니즈 추출 → Signal 생성
  - `voc_analyst`: VoC 데이터 클러스터링 → 테마화 → Signal/Brief 후보
  - WF-02 (Interview to Brief), WF-03 (VoC Mining) 파이프라인 완전 자동화

- **Ontology P0 필드 마이그레이션** 🗃️
  - Entity 테이블: Recency 필드 (`published_at`, `observed_at`, `ingested_at`)
  - Entity 테이블: Source Sync 필드 (`last_synced_at`, `sync_status`)
  - Triple 테이블: Lifecycle 필드 (`status`, `assertion_type`, `evidence_span`, `extractor_run_id`, `verified_by`, `verified_at`, `updated_at`)
  - 복합 인덱스 추가 (`idx_triple_status_predicate`, `idx_triple_status_assertion`)
  - ORGANIZATION 엔티티 ID 접두사 `ORG-` 매핑 추가

### Fixed

- **Agent 설정 JSON 파싱 오류 수정** 🔧
  - `scorecard_evaluator.md`: 입력 예시 JSON 수정, model 필드 추가
  - `brief_writer.md`: 입력 예시 JSON 주석 제거, model 필드 추가
  - 에이전트 로드 시 경고 메시지 제거됨

- **mypy 타입 오류 85개 수정** 🔧
  - Claude Agent SDK `@tool` 데코레이터 타입 호환성 처리
  - SQLAlchemy 모델 forward reference 수정 (`from __future__ import annotations`)
  - Repository 반환 타입 수정 (`Sequence` → `list` 변환)
  - 워크플로 파일 변수 타입 어노테이션 추가
  - Pydantic v2 `@computed_field` + `@property` 데코레이터 스택 처리

### Changed

- **Claude Agent SDK @tool API 리팩토링** 🔄
  - SDK 0.1.19 API 호환: `@tool(name, description, input_schema)` 형식 적용
  - 도구 함수 시그니처 변경: 개별 파라미터 → `args: dict` 통일

---

## [0.5.0] - 2026-01-16

### 🎉 PoC 6주 완료 릴리스

**목표 달성**:
- Activity 23/주 (목표 20+) ✅ 115%
- Signal 35/주 (목표 30+) ✅ 117%
- Brief 8/주 (목표 6+) ✅ 133%
- S2 승인 3/주 (목표 2~4) ✅ 100%
- Signal→Brief 리드타임 4.2일 (목표 ≤7일) ✅

### Added

- **PoC 발표 자료** 📊
  - `docs/POC_PRESENTATION.md`: 50분 발표용 8개 섹션
  - Executive Summary, 핵심 성과, 시스템 아키텍처
  - 데모 시나리오, KPI 달성, 향후 계획

- **데모 시나리오 및 샘플 데이터** 🎬
  - `docs/DEMO_SCENARIOS.md`: 3개 핵심 시나리오 상세 스크립트
  - `docs/demo-data/`: 시나리오별 JSON/CSV 샘플 데이터
  - `api_calls.sh`: 데모용 API 호출 스크립트

- **사용자 가이드** 📚
  - `docs/USER_GUIDE.md`: Quick Start, 워크플로 사용법, FAQ
  - `docs/OPERATIONS_GUIDE.md`: 배포, 모니터링, 트러블슈팅

- **CD 워크플로 staging 브랜치 지원** 🚀
  - staging 브랜치 푸시 시에도 스테이징 배포 트리거
  - 프로덕션 배포는 main 브랜치에서만 실행
  - 헬스체크 재시도 로직 추가 (5회, 30초 간격)

- **WF-06 스테이징/프로덕션 배포 완료** ✅
  - Render 스테이징/프로덕션 환경 배포 성공
  - 68개 API 엔드포인트 (9개 Confluence, 2개 VoC 포함)
  - 645개 단위 테스트 통과

### Fixed

- **email-validator 의존성 수정** 🐛
  - Render 배포 오류 해결 (`pydantic[email]` extras 미작동 문제)
  - `email-validator>=2.0.0` 명시적 의존성 추가

### Changed

- **Pydantic V2 스타일 마이그레이션** ✨
  - `class Config` → `model_config = ConfigDict(...)` 변환 (9개 파일)
  - `pydantic_settings.SettingsConfigDict` 사용 (deps.py)
  - deprecation 경고 완전 제거

---

## [0.4.0] - 2026-01-15

### Added

- **E2E 테스트 스위트** 🧪
  - `tests/e2e/test_e2e_flows.py`: 25개 E2E 워크플로 테스트
  - `tests/e2e/test_api_integration.py`: 26개 API 통합 테스트
  - Signal → Scorecard → Brief 플로우 검증
  - WF-01~06 전체 워크플로 커버리지

- **InboundOutput 매핑 버그 수정** 🐛
  - `workflows.py`: InboundOutput → InboundTriageResponse 필드 매핑 수정
  - `signal_id`, `play_id`, `sla_deadline`, `next_action` 올바른 매핑

- **Auto-fix CI 워크플로우** 🤖
  - CI 실패 시 Claude Code Action으로 자동 수정 시도
  - ruff check --fix, ruff format 자동 실행
  - PR 코멘트로 결과 알림
  - main 브랜치 제외 (feature 브랜치만 대상)

- **WF-06 Confluence Sync 워크플로 구현** ✨
  - 데이터 모델 (SyncTargetType, SyncAction, SyncTarget, SyncInput, SyncResult, SyncOutput)
  - 페이지 포맷터 (Signal, Scorecard, Brief, Activity Markdown 페이지)
  - MockConfluenceClient (create/update/append/get/search 페이지)
  - ConfluenceSyncPipeline (5단계: 검증 → 콘텐츠 준비 → 동기화 → 테이블 업데이트 → 확인)
  - ConfluenceSyncPipelineWithEvents (AG-UI 실시간 이벤트)
  - ConfluenceSyncPipelineWithDB (DB 연동, page_id 캐싱, sync_from_db)
  - **양방향 동기화 구현** 🔄
    - 페이지 파서 (parse_signal_page, parse_scorecard_page, parse_brief_page)
    - 페이지 타입 자동 감지 (detect_page_type)
    - Confluence → DB import (import_from_confluence)
    - 양방향 동기화 (bidirectional_sync)
  - API 엔드포인트 9개 (`/confluence-sync`, `/signal`, `/brief`, `/activity-log`, `/preview`, `/import`, `/from-db`, `/bidirectional`, `/parse-preview`)
  - workflows.py 병합 충돌 해결
  - 단위 테스트 67개 통과

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

#### Phase 5: AI 에이전트 평가(Evals) 플랫폼
- Phase 5.0 MVP: Task/Suite YAML 스키마, Eval Harness, Deterministic Graders, CI 게이팅
- Phase 5.1 신뢰성 강화: LLM-as-Judge, 인간 보정 워크플로, pass@k/pass^k 리포트
- Phase 5.2 확장: 사용자 시뮬레이터, saturation 모니터링, 도메인팀 기여 모델

#### 기타
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
