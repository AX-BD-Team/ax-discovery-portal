# AX Wrap-up Skill (작업 정리)

SSDD 원칙에 따라 작업 내용을 정리하고, 테스트 검증 후 Git 커밋을 수행합니다.

## 트리거

- `/ax:wrap-up` 명령
- "작업 정리" 프롬프트

## 실행 단계

### 1단계: 변경 사항 수집

```bash
git status
git diff --stat
```

- 수정된 파일 목록 확인
- 스테이징 상태 확인

### 2단계: 문서 업데이트 확인

SSDD 원칙에 따라 다음 문서들의 업데이트 필요 여부를 확인합니다:

| 문서 | 업데이트 조건 | 체크 항목 |
|------|--------------|----------|
| `changelog.md` | 기능 추가/변경/수정 시 | 변경 내역 기록 |
| `project-todo.md` | 작업 완료/추가 시 | 완료 항목 체크, 새 항목 추가 |
| `CLAUDE.md` | 구조/규칙 변경 시 | 버전, 기술 스택 정보 |
| `docs/specs/*.md` | 스펙 변경 시 | API/모델 스펙 |

### 3단계: 테스트 실행

프로젝트 타입에 따라 적절한 테스트를 실행합니다:

**Python (백엔드)**:
```bash
# Linting
ruff check backend/

# Type checking
mypy backend/

# Unit tests
pytest tests/ -v --tb=short
```

**TypeScript (프론트엔드)**:
```bash
# Type checking
pnpm typecheck

# Linting
pnpm lint

# Unit tests
pnpm test
```

### 4단계: 테스트 결과 처리

| 결과 | 동작 |
|------|------|
| ✅ 모든 테스트 통과 | 5단계(커밋)로 진행 |
| ❌ 테스트 실패 | 실패 내용 보고, 수정 제안 |
| ⚠️ 경고만 있음 | 경고 목록 표시 후 사용자 확인 |

### 5단계: Git 커밋

테스트 통과 시:

```bash
# 변경 파일 스테이징
git add -A

# 커밋 메시지 생성 (Conventional Commits)
git commit -m "<type>: <description>

<body>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**커밋 타입**:
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드/설정 변경

## 자동 판단 로직

### 문서 업데이트 필요 여부

1. **changelog.md 업데이트 필요**:
   - `backend/` 또는 `app/` 디렉토리 변경 시
   - 새 기능 추가 또는 버그 수정 시

2. **project-todo.md 업데이트 필요**:
   - 기존 TODO 항목 완료 시
   - 새로운 작업 항목 발견 시

3. **CLAUDE.md 업데이트 필요**:
   - 버전 변경 시
   - 새로운 에이전트/스킬 추가 시

### 커밋 메시지 자동 생성

변경 내용을 분석하여 적절한 커밋 메시지를 생성합니다:

```
변경 파일 분석 → 변경 유형 판단 → 메시지 초안 생성 → 사용자 확인
```

## 출력 예시

```
🔄 작업 정리 시작...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 1. 변경 사항 수집
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

수정된 파일 (3개):
  M backend/api/routes/inbox.py
  M backend/agent_runtime/workflows/wf_01_seminar.py
  A tests/test_wf_01.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 2. 문서 업데이트 확인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ changelog.md - 업데이트됨
✅ project-todo.md - 업데이트됨
⏭️ CLAUDE.md - 변경 불필요

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 3. 테스트 실행
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ruff] ✅ 0 errors, 0 warnings
[mypy] ✅ Success: no issues found
[pytest] ✅ 15 passed, 0 failed (2.3s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💾 4. Git 커밋
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 커밋 메시지 (자동 생성):

  feat: WF-01 Seminar Pipeline 워크플로 구현

  - Activity 생성 로직 추가
  - Signal 추출 기능 구현
  - AAR 템플릿 자동 생성
  - 단위 테스트 15개 추가

커밋을 진행할까요? [Y/n]:

✅ 커밋 완료!
   commit abc1234: feat: WF-01 Seminar Pipeline 워크플로 구현
```

## 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--skip-docs` | 문서 업데이트 건너뛰기 | false |
| `--skip-test` | 테스트 건너뛰기 (비권장) | false |
| `--auto` | 모든 확인 자동 승인 | false |
| `--dry-run` | 실제 커밋 없이 미리보기 | false |

## 에러 처리

| 에러 | 메시지 | 해결 방법 |
|------|--------|----------|
| 테스트 실패 | "테스트 실패로 커밋이 중단되었습니다" | 실패 테스트 수정 후 재실행 |
| 충돌 | "Git 충돌이 감지되었습니다" | 충돌 해결 후 재실행 |
| 변경 없음 | "커밋할 변경 사항이 없습니다" | 작업 확인 |

## 사용법

```
/ax:wrap-up                    # 기본 실행
/ax:wrap-up --dry-run          # 미리보기 (커밋 없음)
/ax:wrap-up --skip-docs        # 문서 업데이트 건너뛰기
/ax:wrap-up --auto             # 자동 모드 (모든 확인 자동 승인)
```

## 관련 문서

- [CLAUDE.md](../../../CLAUDE.md) - 프로젝트 개발 문서
- [changelog.md](../../../changelog.md) - 변경 이력
- [project-todo.md](../../../project-todo.md) - 작업 추적
