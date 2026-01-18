# 프로젝트 개발 문서

> Claude와의 개발 협업을 위한 프로젝트 핵심 문서

**현재 버전**: 0.6.0 | **상태**: ✅ PoC Complete | **방법론**: SSDD
**변경 내역**:

---

## 🎯 개발 방법론

**SSDD (Skillful Spec-Driven Development)** = SDD + Claude Skills Integration

| Skill | 용도 | 산출물 |
|-------|------|--------|
| ax-scorecard | Signal 정량 평가 | Scorecard JSON (100점 만점, 5개 차원) |
| ax-brief | 1-Page Brief 자동 생성 | Brief JSON + Confluence 페이지 |
| ax-seminar | 세미나 Activity 생성 | Activity + AAR 템플릿 |
| ax-sprint | 5-day Sprint 플랜 수립 | Sprint 체크리스트 |
| ax-confluence | Confluence 동기화 규칙 | DB/Live doc 업데이트 |
| ax-wrap-up | 작업 정리 + 테스트 + 커밋 | 문서 업데이트 + Git commit |
| ax-todo | ToDo 관리 + Confluence 동기화 | 진행현황 리포트 + 차이점 분석 |
| ax-health-check | 프로젝트 점검 | 의존성/타입/린트/빌드/버전 체크 리포트 |

**문서 인덱스**: [docs/INDEX.md](docs/INDEX.md)

---

## 📜 프로젝트 헌법

핵심 가치:
기술 원칙: TDD, 컴포넌트 단일 책임

**상세 원칙**: [constitution.md](constitution.md)

---

## 🤖 AI 협업 규칙

### 언어 원칙

- **모든 출력은 한글로 작성**: 코드 주석, 커밋 메시지, 문서, 대화 응답
- **예외**: 코드 변수명, 함수명, 기술 용어는 영문 유지

### 날짜/시간 원칙

- **기준 시간대**: KST (Korea Standard Time, UTC+9)
- **날짜 표기**: YYYY-MM-DD 형식
- **마이그레이션 파일명**: YYYYMMDDHHMMSS 형식 (UTC 기준)
- **현재 날짜 확인**: 시스템 프롬프트의 `Today's date` 참조 (예: 2026-01-17)
- **문서 업데이트 시**: 반드시 현재 날짜로 `마지막 업데이트` 갱신

### 컨텍스트 관리

- **태스크마다 새 대화 시작**: 이전 대화의 오염 방지
- **명세 참조로 컨텍스트 제공**: 대화 히스토리 대신 명세 파일 공유
- **관련 파일만 공유**: 전체 코드베이스가 아닌 필요한 파일만

### 작업 체크리스트

**작업 전**: 관련 명세 검토, 아키텍처 확인, 작업 분해
**작업 후**: CLAUDE.md 업데이트, project-todo.md 체크, 버그 시 bug-fixes-log.md 기록

### 작업 실행 원칙

- **병렬 작업 우선**: 독립적인 작업은 항상 병렬로 진행
- **효율성 극대화**: 의존성 없는 도구 호출은 동시에 실행

### 문서 효율화 원칙

- **중복 금지**: 정보는 한 곳에만 기록, 다른 곳에서는 링크 참조
- **링크 우선**: 상세 내용은 별도 문서로 분리 후 링크
- **헤더 통합**: 버전/상태/방법론 등 메타데이터는 문서 헤더에 통합
- **아카이브 활용**: 히스토리는 `docs/archive/`로 이동, 최신 요약만 유지
- **단일 책임**: 각 문서는 하나의 명확한 목적만 가짐

### 주기적 정리 원칙 (월 1회 권장)

**문서 정리**:

- changelog.md: 1000줄 초과 시 이전 버전 → `docs/archive/changelog-YYYY-MM.md`
- project-todo.md: 완료 항목 3개월 경과 시 → `docs/archive/completed-todos-vX.X.X.md`
- 날짜별 리포트: `docs/archive/daily-summaries/`로 이동

**버전 동기화 체크**:

- package.json, CLAUDE.md, project-todo.md, docs/INDEX.md 버전 일치 확인
- Git 태그와 package.json 버전 일치 확인

**코드 품질 체크**:

- `npm run lint` 경고 0개 유지
- `npm run build` 성공 확인
- 불필요한 `@ts-ignore` → `@ts-expect-error` 변환

---

## 🔧 Sub Agent & Skills 시스템

### 사용 가능한 Sub Agent

| Agent | 용도 | 자동 호출 조건 |
|-------|------|----------------|
| orchestrator | 워크플로 실행 및 서브에이전트 조율 | 모든 Command 실행 시 |
| external_scout | 외부 세미나/리포트/뉴스 수집 | WF-01 Seminar Pipeline |
| scorecard_evaluator | Signal 정량 평가 (100점) | /ax:triage 또는 WF-02/04 |
| brief_writer | 1p Brief 생성 + Confluence 페이지 | /ax:brief 또는 Scorecard GO 시 |
| confluence_sync | Confluence DB/Live doc 업데이트 | 모든 워크플로 종료 시 |
| governance | 위험 도구 차단/승인/감사 | 민감한 도구 호출 시 |

### 사용 가능한 Skills

| Skill | 용도 | 키워드 |
|-------|------|--------|
| ax-scorecard | Signal 정량 평가 | Scorecard JSON (100점 만점, 5개 차원) |
| ax-brief | 1-Page Brief 자동 생성 | Brief JSON + Confluence 페이지 |
| ax-seminar | 세미나 Activity 생성 | Activity + AAR 템플릿 |
| ax-sprint | 5-day Sprint 플랜 수립 | Sprint 체크리스트 |
| ax-confluence | Confluence 동기화 규칙 | DB/Live doc 업데이트 |
| ax-wrap-up | 작업 정리 + 테스트 + 커밋 | 문서 업데이트 + Git commit |
| ax-todo | ToDo 관리 + Confluence 동기화 | 진행현황 리포트 + 차이점 분석 |
| ax-health-check | 프로젝트 점검 | 의존성/타입/린트/빌드/버전 체크 |

### 관리 및 사용법

---

## 🔢 버전 관리

**형식**: Major.Minor.Patch (Semantic Versioning)

| 버전 | 변경 기준 | 승인 |
|------|-----------|------|
| Major (X.0.0) | Breaking Changes | ⚠️ 사용자 승인 필수 |
| Minor (0.X.0) | 새로운 기능 추가 | 자동 |
| Patch (0.0.X) | 버그 수정, Hotfix | 자동 |

```bash
npm run release:patch  # 패치 버전
npm run release:minor  # 마이너 버전
npm run release:major  # 메이저 버전
```

### 버전 동기화 원칙 ⚠️ 필수

**package.json 버전과 GitHub Tag/Release는 반드시 일치해야 합니다.**

| 항목 | 위치 | 동기화 |
|------|------|--------|
| 시스템 버전 | `package.json` → `version` | 기준값 |
| GitHub Tag | `git tag vX.X.X` | 자동 동기화 |
| GitHub Release | `gh release create` | 자동 동기화 |

**버전 업데이트 체크리스트**:

1. `package.json` 버전 변경
2. `git tag -a vX.X.X -m "메시지"` 태그 생성
3. `git push origin vX.X.X` 태그 푸시
4. `gh release create vX.X.X` 릴리스 생성

**자동화 명령**:

```bash
# 버전 범프 + 태그 + 푸시 + 릴리스 (권장)
npm run release:patch && git push --follow-tags && gh release create v$(node -p "require('./package.json').version")
```

---

## 📋 프로젝트 개요

**AX Discovery Portal**은 Claude Agent SDK를 활용한 멀티에이전트 기반 사업기회 포착 엔진입니다.

**핵심 가치 제안**:
- Activity → Signal → Scorecard → Brief → Validation(S2) → Pilot-ready(S3) 파이프라인 자동화
- 3원천(KT/그룹사/대외) × 5채널(데스크리서치/자사활동/영업PM/인바운드/아웃바운드)에서 수집한 정보를 자동으로 정제/평가/문서화
- Confluence를 System-of-Record로 활용 (Play DB + Live doc)
- 멀티에이전트 협업으로 BD팀 업무 효율 극대화

**PoC 목표 (6주)**:
- 주간 목표: Activity 20+, Signal 30+, Brief 6+, S2 2~4
- 리드타임: Signal→Brief ≤7일, Brief→S2 ≤14일

---

## 🛠️ 기술 스택

| 레이어 | 기술 | 버전 | 용도 |
|--------|------|------|------|
| **Runtime** | Python | 3.11+ | 백엔드/에이전트 런타임 |
| **Backend** | FastAPI | 0.115.0+ | REST API 서버 |
| **Agent SDK** | Anthropic Claude Agent SDK | 0.1.19+ | 멀티에이전트 오케스트레이션 |
| **AI Model** | Claude Sonnet 4 | 20250514 | LLM 추론 엔진 |
| **Integration** | MCP (Model Context Protocol) | - | 외부 도구 연동 (Confluence/Teams) |
| **Database** | PostgreSQL | (계획) | Signal/Scorecard/Brief 저장 |
| **Confluence** | atlassian-python-api | 3.41.0+ | Confluence API 클라이언트 |
| **Logging** | structlog | 24.4.0+ | 구조화 로깅 |
| **Testing** | pytest | 8.3.0+ | 단위/통합 테스트 |
| **Linting** | ruff | 0.8.0+ | 코드 품질 검사 |
| **Type Checking** | mypy | 1.13.0+ | 정적 타입 검사 |
| **Frontend** | Next.js | (계획) | 웹 UI |

---

## 🚀 배포 ⚠️ 중요

| 항목 | 값 |
|------|-----|
| **현재 환경** | 로컬 개발 환경 (uvicorn) |
| **프로덕션 배포** | 미정 (PoC 완료 후 결정) |
| **API 엔드포인트** | http://localhost:8000 |
| **Agent 실행 모드** | Claude Code CLI + MCP 서버 |

### 배포 방식

- **개발 모드**: `uvicorn backend.api.main:app --reload` (포트 8000)
- **프로덕션**: TBD (Cloudflare Workers/Pages, AWS Lambda 등 검토 중)

---

## 📁 프로젝트 구조

```
ax-discovery-portal/
├── .claude/              # Claude Code 설정
│   ├── agents/          # 6개 에이전트 정의
│   ├── skills/          # 8개 Skills
│   ├── commands/        # 7개 Commands
│   └── hooks/           # Tool use 훅
├── backend/              # FastAPI 백엔드
│   ├── api/             # REST API 라우터 (4개)
│   ├── agent_runtime/   # 에이전트 실행 환경 + 워크플로 (6개)
│   └── integrations/    # MCP 서버 (Confluence, Teams)
├── app/                  # 클라이언트 (계획 중)
│   ├── web/             # Next.js 웹앱
│   └── mobile/          # React Native 모바일앱
├── tests/                # pytest 테스트
├── docs/                 # 문서
├── pyproject.toml        # 프로젝트 설정
├── project-todo.md       # 작업 추적
├── changelog.md          # 변경 이력
└── README.md             # 프로젝트 개요
```

**상세 구조**: [README.md](README.md)의 "Project Structure" 섹션 참조

---

## 📝 참고사항

- **Import Alias**: `@/` → `src/`
- **코드 컨벤션**: PascalCase (컴포넌트), camelCase (함수/훅), kebab-case (파일)
- **문서 인덱스**: [docs/INDEX.md](docs/INDEX.md)

---

# important-instruction-reminders

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files.

# Context Engineering

당신은 최신 스택이 빠르게 변하는 프로젝트에서 작업하는 AI 개발자입니다.

1. **환경 파악**: package.json, 구성 파일을 읽고 프레임워크·라이브러리 버전 확인
2. **버전 차이 대응**: 릴리스 노트 참조, 최신 권장사항 확인
3. **설계 시 체크**: 네트워크 리소스, 인증/데이터 레이어 호환성 고려
4. **구현 중 검증**: 린트/타입/빌드 명령 실행, 예상 오류 미리 보고
5. **결과 전달**: 버전 차이 반영 사항, 추가 확인 항목 명시
