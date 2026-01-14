# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

---

## [0.3.0] - 2026-01-14

### Added

- PostgreSQL 데이터베이스 연동 완료
  - SQLAlchemy 2.0 비동기 ORM 통합
  - 5개 테이블 정의 (signals, scorecards, opportunity_briefs, play_records, action_logs)
  - Enum 타입 (SignalSource, SignalChannel, SignalStatus, Decision, NextStep 등)
  - JSON/JSONB 필드 (evidence, kpi_hypothesis, dimension_scores 등)
  - 외래키 관계 및 인덱스 설정
  - TimestampMixin (created_at, updated_at 자동 관리)
- Alembic 마이그레이션 시스템
  - 비동기 마이그레이션 환경 설정
  - 초기 스키마 마이그레이션 준비
  - Enum 타입 자동 생성 지원
- CRUD 저장소 패턴
  - CRUDBase 제네릭 클래스
  - Signal, Scorecard, Brief, PlayRecord 저장소 구현
  - ID 자동 생성 (SIG-YYYY-NNN, SCR-YYYY-NNN, BRF-YYYY-NNN 형식)
  - 필터링 및 페이지네이션 지원
  - 통계 쿼리 (get_stats)
- Agent Runtime 단위 테스트 (80%+ 커버리지 목표)
  - 17개 Runner 테스트 (에이전트 로딩, MCP 연결, 세션 관리, 워크플로 라우팅)
  - 12개 EventManager 테스트 (이벤트 발행/구독, 싱글톤, 스트리밍)
  - 12개 Workflow 테스트 (메타데이터 추출, Activity 생성, AAR 템플릿, Confluence 업데이트)
  - pytest fixtures (mock_env, sample_agent_markdown, mock_confluence_mcp 등)
  - AsyncMock 및 httpx Mock 패턴

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

## [0.3.0] - 2026-01-14

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

### Added - 페이지

- `/` - 메인 대시보드
- `/inbox` - Signal 관리 (Triage)
- `/seminar` - 세미나 등록 (WF-01)
- `/plays` - Play 대시보드

---

## [Unreleased]

### In Planning

- PostgreSQL 데이터베이스 연동
- WF-02 Interview-to-Brief 구현
- WF-04 Inbound Triage 구현
- Scorecard 평가 로직 구현
- Brief 생성 로직 구현
