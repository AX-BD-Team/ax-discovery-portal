# 프로젝트 개발 문서

> Claude와의 개발 협업을 위한 프로젝트 핵심 문서

**현재 버전**: 0.1.0 | **상태**: 🚧 Development | **방법론**: SSDD

---

## 🎯 개발 방법론

**SSDD (Skillful Spec-Driven Development)** = SDD + Claude Skills Integration

| Skill | 용도 | 산출물 |
|-------|------|--------|
| {{skill-name}} | {{skill-description}} | {{skill-output}} |

**문서 인덱스**: [docs/INDEX.md](docs/INDEX.md)

---

## 📜 프로젝트 헌법

<!-- 프로젝트별 핵심 가치와 기술 원칙을 정의하세요 -->

핵심 가치:
- {{core-value-1}}
- {{core-value-2}}

기술 원칙:
- TDD (Test-Driven Development)
- 컴포넌트 단일 책임 원칙

---

## 🤖 AI 협업 규칙

### 언어 원칙

- **모든 출력은 한글로 작성**: 코드 주석, 커밋 메시지, 문서, 대화 응답
- **예외**: 코드 변수명, 함수명, 기술 용어는 영문 유지

### 날짜/시간 원칙

- **기준 시간대**: KST (Korea Standard Time, UTC+9)
- **날짜 표기**: YYYY-MM-DD 형식
- **마이그레이션 파일명**: YYYYMMDDHHMMSS 형식 (UTC 기준)
- **현재 날짜 확인**: 시스템 프롬프트의 `Today's date` 참조
- **문서 업데이트 시**: 반드시 현재 날짜로 `마지막 업데이트` 갱신

### 컨텍스트 관리

- **태스크마다 새 대화 시작**: 이전 대화의 오염 방지
- **명세 참조로 컨텍스트 제공**: 대화 히스토리 대신 명세 파일 공유
- **관련 파일만 공유**: 전체 코드베이스가 아닌 필요한 파일만

### 작업 체크리스트

**작업 전**: 관련 명세 검토, 아키텍처 확인, 작업 분해
**작업 후**: CLAUDE.md 업데이트, project-todo.md 체크

### 작업 실행 원칙

- **병렬 작업 우선**: 독립적인 작업은 항상 병렬로 진행
- **효율성 극대화**: 의존성 없는 도구 호출은 동시에 실행

### 문서 효율화 원칙

- **중복 금지**: 정보는 한 곳에만 기록, 다른 곳에서는 링크 참조
- **링크 우선**: 상세 내용은 별도 문서로 분리 후 링크
- **헤더 통합**: 버전/상태/방법론 등 메타데이터는 문서 헤더에 통합
- **아카이브 활용**: 히스토리는 `docs/archive/`로 이동, 최신 요약만 유지
- **단일 책임**: 각 문서는 하나의 명확한 목적만 가짐

---

## 🔧 Sub Agent & Skills 시스템

### 사용 가능한 Sub Agent

<!-- 프로젝트에 맞게 에이전트 정의 -->

| Agent | 용도 | 자동 호출 조건 |
|-------|------|----------------|
| orchestrator | 워크플로 실행 및 서브에이전트 조율 | 모든 Command 실행 시 |
| {{agent-name}} | {{agent-purpose}} | {{trigger-condition}} |

### 사용 가능한 Skills

<!-- 프로젝트에 맞게 스킬 정의 -->

| Skill | 용도 | 키워드 |
|-------|------|--------|
| {{skill-name}} | {{skill-purpose}} | {{skill-keyword}} |

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

### 버전 동기화 원칙

**package.json/pyproject.toml 버전과 GitHub Tag/Release는 반드시 일치해야 합니다.**

| 항목 | 위치 | 동기화 |
|------|------|--------|
| 시스템 버전 | `package.json` / `pyproject.toml` | 기준값 |
| GitHub Tag | `git tag vX.X.X` | 자동 동기화 |
| GitHub Release | `gh release create` | 자동 동기화 |

---

## 📋 프로젝트 개요

<!-- 프로젝트별 개요 작성 -->

**{{PROJECT_NAME}}**은 {{PROJECT_DESCRIPTION}}입니다.

**핵심 가치 제안**:
- {{value-proposition-1}}
- {{value-proposition-2}}

---

## 🛠️ 기술 스택

<!-- 프로젝트에 맞게 기술 스택 정의 -->

| 레이어 | 기술 | 버전 | 용도 |
|--------|------|------|------|
| **Runtime** | Python | 3.11+ | 백엔드/에이전트 런타임 |
| **Backend** | FastAPI | 0.115.0+ | REST API 서버 |
| **Agent SDK** | Claude Agent SDK | 0.1.19+ | 멀티에이전트 오케스트레이션 |
| **AI Model** | Claude Sonnet 4 | 20250514 | LLM 추론 엔진 |
| **Database** | PostgreSQL | 16+ | 데이터 저장소 |
| **Testing** | pytest | 8.3.0+ | 단위/통합 테스트 |
| **Linting** | ruff | 0.8.0+ | 코드 품질 검사 |
| **Type Checking** | mypy | 1.13.0+ | 정적 타입 검사 |

---

## 📁 프로젝트 구조

```
{{project-name}}/
├── .claude/              # Claude Code 설정
│   ├── agents/          # 에이전트 정의
│   ├── skills/          # Skills
│   ├── commands/        # Commands
│   ├── hooks/           # Tool use 훅
│   └── prompts/         # LLM 프롬프트
├── backend/              # FastAPI 백엔드
│   ├── api/             # REST API 라우터
│   ├── agent_runtime/   # 에이전트 실행 환경
│   │   ├── ontology/    # Ontology-LLM 구조
│   │   └── workflows/   # 워크플로
│   ├── database/        # DB 모델/리포지토리
│   ├── evals/           # AI 에이전트 평가 시스템
│   └── core/            # 설정, 로깅
├── evals/                # 평가 정의 (YAML)
│   ├── schemas/         # JSON Schema
│   ├── suites/          # 평가 스위트
│   ├── tasks/           # 평가 과제
│   └── rubrics/         # LLM Judge 루브릭
├── tests/                # pytest 테스트
├── docs/                 # 문서
├── pyproject.toml        # Python 프로젝트 설정
└── README.md             # 프로젝트 개요
```

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
