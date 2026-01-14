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

## [Unreleased]

### In Planning

- PostgreSQL 데이터베이스 연동
- WF-02 Interview-to-Brief 구현
- WF-04 Inbound Triage 구현
- Scorecard 평가 로직 구현
- Brief 생성 로직 구현
