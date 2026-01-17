# /ax:confluence Command

Confluence 페이지를 동기화하고 업데이트합니다.

## 사용법

```
/ax:confluence [--action <sync|update|import|status>] [--target <page|db|all>] [--page-id <id>]
```

## 인자

| 인자 | 필수 | 설명 | 예시 |
|------|------|------|------|
| `--action` | | 실행할 작업 | sync (기본), update, import, status |
| `--target` | | 동기화 대상 | page, db, all |
| `--page-id` | | 특정 페이지 ID | 123456789 |
| `--title` | | 페이지 제목으로 검색 | "프로젝트 현황" |
| `--dry-run` | | 실제 실행 없이 미리보기 | |

## 액션 설명

| 액션 | 설명 |
|------|------|
| `sync` | DB → Confluence 단방향 동기화 |
| `update` | 프로젝트 현황 페이지 업데이트 |
| `import` | Confluence → DB 역방향 동기화 |
| `status` | 동기화 상태 확인 |

## 실행 워크플로

**WF-06 Confluence Sync**

```
1. 동기화 대상 식별 (Signal, Scorecard, Brief, Activity)
2. DB에서 최신 데이터 조회
3. Confluence 페이지 포맷팅
4. 페이지 생성/업데이트
5. Action Log 기록
6. Live doc 업데이트
```

## 사용 예시

### 프로젝트 현황 업데이트

```bash
/ax:confluence --action update

# 출력:
🔄 Confluence 동기화 시작...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 1. 동기화 대상 확인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

동기화 대상:
  📄 프로젝트 현황 페이지
  📄 기술 아키텍처 페이지
  📊 Play DB 테이블

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 2. 데이터 수집
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Signal: 35건
✅ Scorecard: 28건
✅ Brief: 12건
✅ Activity: 45건

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 3. Confluence 업데이트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 프로젝트 현황 업데이트 완료
✅ 기술 아키텍처 업데이트 완료
✅ Play DB 동기화 완료

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 동기화 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📎 프로젝트 현황: https://confluence.../ax-discovery-portal
📎 기술 아키텍처: https://confluence.../ax-tech-architecture
```

### 상태 확인

```bash
/ax:confluence --action status

# 출력:
📊 Confluence 동기화 상태
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────┬────────────┬─────────────────┐
│ 항목                │ DB         │ Confluence      │
├─────────────────────┼────────────┼─────────────────┤
│ Signal              │ 35건       │ 35건 ✅         │
│ Scorecard           │ 28건       │ 28건 ✅         │
│ Brief               │ 12건       │ 11건 ⚠️ (1건 미동기화) │
│ Activity            │ 45건       │ 45건 ✅         │
└─────────────────────┴────────────┴─────────────────┘

마지막 동기화: 2026-01-17 10:30:00 KST
다음 자동 동기화: 2026-01-17 18:00:00 KST (금요일 배치)
```

### 미리보기 모드

```bash
/ax:confluence --action sync --dry-run

# 실제 업데이트 없이 변경 사항만 표시
```

### 특정 페이지 업데이트

```bash
/ax:confluence --page-id 123456789 --action update
```

## 동기화 대상

### 자동 동기화 항목

| 항목 | 트리거 | Confluence 위치 |
|------|--------|----------------|
| Signal 생성 | `signal.created` | Action Log + Live doc |
| Scorecard 완료 | `signal.scored` | Live doc |
| Brief 생성 | `brief.created` | Action Log + Live doc + Play DB |
| Activity 등록 | `activity.created` | Action Log |
| S2 승인 | `validation.completed` | Play DB status |

### 배치 동기화 (주간)

```
매주 금요일 18:00 KST
- Play DB QTD 집계 업데이트
- 전체 데이터 정합성 검증
- 누락된 항목 동기화
```

## API 엔드포인트

내부적으로 다음 API를 호출합니다:

| 엔드포인트 | 용도 |
|-----------|------|
| `POST /api/workflows/confluence-sync` | 동기화 실행 |
| `POST /api/workflows/confluence-sync/preview` | 미리보기 |
| `POST /api/workflows/confluence-sync/import` | 역방향 동기화 |
| `GET /api/workflows/confluence-sync/status` | 상태 조회 |

## 에러 처리

| 에러 | 메시지 | 해결 방법 |
|------|--------|----------|
| 인증 실패 | "Confluence 인증 실패" | CONFLUENCE_API_TOKEN 확인 |
| 페이지 없음 | "페이지를 찾을 수 없습니다" | page_id 또는 title 확인 |
| 권한 부족 | "페이지 수정 권한 없음" | Confluence 권한 확인 |
| 버전 충돌 | "페이지가 수정되었습니다" | 최신 버전 확인 후 재시도 |

## 환경 변수

```env
CONFLUENCE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_API_TOKEN=your-api-token
CONFLUENCE_SPACE_KEY=AX
CONFLUENCE_PLAY_DB_ID=play-db-page-id
CONFLUENCE_ACTION_LOG_ID=action-log-page-id
```

## 관련 커맨드

- `/ax:kpi-digest` - KPI 리포트 생성 후 Confluence 공유
- `/ax:brief` - Brief 생성 후 자동 동기화
- `/ax:wrap-up` - 작업 완료 후 문서 업데이트
