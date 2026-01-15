# /ax:wrap-up Command (작업 정리)

SSDD 원칙에 따라 작업 내용을 정리하고, 테스트 검증 후 Git 커밋을 수행합니다.

## 사용법

```
/ax:wrap-up [--dry-run] [--skip-docs] [--skip-test] [--auto]
```

## 인자

| 인자 | 필수 | 설명 | 예시 |
|------|------|------|------|
| `--dry-run` | | 미리보기 모드 (실제 커밋 없음) | |
| `--skip-docs` | | 문서 업데이트 건너뛰기 | |
| `--skip-test` | | 테스트 실행 건너뛰기 (비권장) | |
| `--auto` | | 자동 승인 모드 | |

## 실행 워크플로

```
1. 변경 사항 수집 (git status, git diff)
2. 문서 업데이트 확인 (changelog, project-todo, CLAUDE.md)
3. 테스트 실행 (ruff, mypy, pytest / pnpm lint, typecheck, test)
4. 테스트 결과 검증
5. (통과 시) Git 커밋 생성
```

## 출력

```
🔄 작업 정리 시작...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 변경 사항 수집
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

수정된 파일 (3개):
  M backend/api/routes/inbox.py
  M backend/agent_runtime/workflows/wf_01_seminar.py
  A tests/test_wf_01.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 문서 업데이트 확인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ changelog.md - 업데이트 완료
✅ project-todo.md - 업데이트 완료
⏭️ CLAUDE.md - 변경 불필요

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 테스트 실행
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ruff] ✅ 통과
[mypy] ✅ 통과
[pytest] ✅ 15 passed (2.3s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💾 Git 커밋
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 커밋 메시지:

  feat: WF-01 Seminar Pipeline 워크플로 구현

  - Activity 생성 로직 추가
  - Signal 추출 기능 구현
  - 단위 테스트 15개 추가

  Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

✅ 커밋 완료!
   abc1234: feat: WF-01 Seminar Pipeline 워크플로 구현
```

## 테스트 실패 시

```
🔄 작업 정리 시작...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 테스트 실행
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ruff] ✅ 통과
[mypy] ❌ 실패

mypy 오류:
  backend/api/routes/inbox.py:45: error: Argument 1 to "create_signal"
  has incompatible type "str"; expected "SignalCreate"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 커밋 중단
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

테스트 실패로 커밋이 중단되었습니다.
위 오류를 수정한 후 다시 실행해주세요.

💡 수정 제안:
   SignalCreate 모델을 사용하여 타입을 맞춰주세요.
```

## 문서 업데이트 내용

### changelog.md

변경 유형에 따라 자동으로 항목 추가:

```markdown
## [v0.4.1] - 2026-01-15

### Added
- WF-01 Seminar Pipeline 워크플로 구현

### Changed
- Signal 추출 로직 개선

### Fixed
- Inbox API 타입 오류 수정
```

### project-todo.md

완료된 작업 항목 체크:

```markdown
- [x] WF-01 Seminar Pipeline 구현 ✅ v0.4.1
```

## 에러 처리

| 에러 | 메시지 | 해결 방법 |
|------|--------|----------|
| 테스트 실패 | "테스트 실패로 커밋이 중단되었습니다" | 실패 항목 수정 후 재실행 |
| Git 충돌 | "Git 충돌이 감지되었습니다" | 충돌 해결 후 재실행 |
| 변경 없음 | "커밋할 변경 사항이 없습니다" | - |
| 문서 누락 | "필수 문서 업데이트가 누락되었습니다" | 문서 업데이트 후 재실행 |

## 관련 커맨드

- `/ax:brief` - Brief 생성
- `/ax:triage` - Signal 평가
- `/ax:kpi-digest` - KPI 요약
