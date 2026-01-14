# AX Confluence Skill

Confluence를 System-of-Record로 사용하기 위한 기록 규칙입니다.

## 입력
- Play ID
- 단계 (Activity/Signal/Brief/S2/S3)
- 산출물 링크/데이터

## 출력
- Confluence 페이지 업데이트
- Play DB 행 업데이트
- Action Log 기록

## Confluence 구조

```
AX-BD Space
├── Play 진행현황 DB (QTD)          ← 주간 집계
├── Action Log DB                  ← 실시간 기록
├── Plays/
│   ├── EXT_Desk_D01_Seminar/
│   │   └── Live doc              ← 이벤트별 append
│   ├── KT_Sales_S01_Interview/
│   │   └── Live doc
│   └── ...
├── Briefs/
│   ├── BRF-2025-001/
│   └── ...
└── Sprints/
    ├── SPR-2025-001/
    └── ...
```

## Play 진행현황 DB 필드

| 필드 | 타입 | 설명 | 업데이트 주기 |
|------|------|------|-------------|
| play_id | text | Play 고유 ID | 고정 |
| play_name | text | Play 이름 | 고정 |
| owner | user | 담당자 | 변경 시 |
| status | select | G/Y/R | 주간 |
| activity_qtd | number | 분기 Activity 수 | 실시간 |
| signal_qtd | number | 분기 Signal 수 | 실시간 |
| brief_qtd | number | 분기 Brief 수 | 실시간 |
| s2_qtd | number | 분기 S2(Validated) 수 | 실시간 |
| s3_qtd | number | 분기 S3(Pilot-ready) 수 | 실시간 |
| next_action | text | 다음 액션 | 주간 |
| due_date | date | 마감일 | 변경 시 |
| last_updated | date | 최종 수정일 | 자동 |

## Action Log DB 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| log_id | text | 로그 ID |
| play_id | text | Play ID |
| action_type | select | Activity/Signal/Brief/S2/S3 |
| title | text | 제목 |
| url | url | 링크 |
| actor | user | 수행자 |
| created_at | date | 생성일시 |

## Live doc Append 규칙

각 이벤트 발생 시 해당 Play의 Live doc에 append:

### Activity 생성 시
```markdown
---
### {날짜} Activity: {제목}
- **출처**: {source} / {channel}
- **링크**: {url}
- **담당**: {owner}
- **상태**: 등록됨
```

### Signal 생성 시
```markdown
---
### {날짜} Signal: {제목}
- **ID**: {signal_id}
- **Pain**: {pain}
- **근거**: {evidence_links}
- **Confidence**: {confidence}
```

### Brief 생성 시
```markdown
---
### {날짜} Brief 생성: {제목}
- **ID**: {brief_id}
- **Signal**: {signal_id}
- **Scorecard**: {total_score}점 / {decision}
- **문서**: {confluence_url}
```

### Validation 완료 시
```markdown
---
### {날짜} Validation 완료: {brief_id}
- **방법**: {method}
- **결과**: {decision}
- **주요 발견**: {findings}
- **다음 단계**: {next_actions}
```

## MCP Tools 사용

```python
# 페이지 append
confluence.append_to_page(
    page_id="LIVE_DOC_PAGE_ID",
    append_md="### 2025-01-14 Signal: 콜센터 AHT 최적화..."
)

# DB 행 업데이트 (QTD +1)
confluence.db_upsert_row(
    database_id="PLAY_DB_ID",
    row_id="EXT_Desk_D01",
    data={"signal_qtd": 15}  # 기존값 + 1
)

# Action Log 추가
confluence.db_insert_row(
    database_id="ACTION_LOG_DB_ID",
    data={
        "log_id": "LOG-2025-0142",
        "play_id": "EXT_Desk_D01",
        "action_type": "Signal",
        "title": "콜센터 AHT 최적화"
    }
)
```

## 업데이트 타이밍

| 이벤트 | 즉시 | 주간(금 EOD) |
|--------|------|-------------|
| Activity 생성 | ✅ Live doc | |
| Signal 생성 | ✅ Live doc, Action Log | ✅ Play DB QTD |
| Brief 생성 | ✅ Live doc, Action Log | ✅ Play DB QTD |
| Validation 완료 | ✅ Live doc | ✅ Play DB Status |
| Pilot 착수 | ✅ Live doc | ✅ Play DB S3 |

## 사용법

```
# 자동 (워크플로 내부에서 호출)
ConfluenceSync.record_signal(signal_data)

# 수동
/ax:sync --play-id EXT_Desk_D01 --refresh
```
