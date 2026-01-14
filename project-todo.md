# AX Discovery Portal - Project TODO

> 프로젝트 진행 상황 및 다음 단계

**현재 버전**: 0.2.0
**마지막 업데이트**: 2026-01-14

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

## 🚧 Phase 2: Core Integration (진행 중)

### 우선순위 1: 필수 기능

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
- [ ] 데이터베이스 연동
  - [ ] PostgreSQL 설정 및 연결
  - [ ] SQLAlchemy 모델 정의
  - [ ] Alembic 마이그레이션 설정
  - [ ] API 라우터에 DB 연동

### 우선순위 2: 핵심 워크플로
- [ ] WF-02 Interview-to-Brief 구현
- [ ] WF-04 Inbound Triage 구현
- [ ] Scorecard 평가 로직 구현
- [ ] Brief 생성 로직 구현

### 우선순위 3: 고급 기능
- [ ] Confluence Database API 구현 (db_query, db_upsert_row)
- [ ] 중복 Signal 체크 알고리즘
- [ ] WF-05 KPI Digest 구현
- [ ] Teams 연동 (MCP 서버)

---

## 📅 Phase 3: UI & UX (계획)

- [ ] 웹 UI (Next.js)
  - [ ] Inbox 페이지
  - [ ] Scorecard 페이지
  - [ ] Brief 페이지
  - [ ] Play Dashboard
- [ ] 모바일 앱 (PWA/React Native)

---

## 🐛 알려진 이슈

1. **Stream Router**: event_types.py dataclass 오류로 임시 제거 (비우선 기능)
2. **Confluence Database API**: Confluence Cloud API의 Database 기능 제약 → 대안 필요 (페이지 테이블 우회 또는 Postgres 사용)
3. **Markdown to Confluence 변환**: 현재 간단한 HTML 래핑만 구현 → 완전한 변환 라이브러리 필요
4. **인증/권한**: 현재 mock 구현, 프로덕션용 JWT 인증 필요

---

## 📝 다음 스프린트 (Week 3)

**목표**: WF-02/04 구현 및 데이터베이스 연동

**작업 항목**:

1. PostgreSQL 로컬 설정 및 SQLAlchemy 모델 정의
2. Alembic 마이그레이션 설정
3. WF-02 Interview-to-Brief 워크플로 구현
4. WF-04 Inbound Triage 워크플로 구현
5. Scorecard 평가 로직 구현
6. Brief 생성 로직 구현

**성공 조건**:

- [ ] 데이터베이스에 Signal/Scorecard/Brief 저장
- [ ] `/ax:triage` 실행 시 WF-04 성공
- [ ] Scorecard 100점 만점 평가 동작
- [ ] Brief 1-Page 포맷 자동 생성
