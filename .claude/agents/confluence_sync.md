---
name: "confluence_sync"
description: "Confluence DB/Live doc 자동 업데이트 담당"
---

# Confluence Sync Agent

Confluence DB/Live doc 자동 업데이트를 담당합니다.

## 역할

- Play 진행현황 DB 업데이트
- Action Log 기록
- Live doc append
- 주간 배치 동기화
- Play ToDo 하위 페이지 관리

## Confluence 페이지 구조

```
Project TODO (720932) ─────────────── 스프린트 단위 진행현황
    │
    ├── EXT_Desk_D01 ToDo List (753719) ── Play별 세부 작업
    ├── EXT_Desk_D02 ToDo List (TBD)
    └── ...

Play DB (720899) ──────────────────── Play 진행현황 테이블 + 하위 페이지 링크
Action Log (786433) ───────────────── 작업 이력 기록
```

**페이지 역할**:

| 페이지 | ID | 용도 |
|--------|-----|------|
| Project TODO | 720932 | 스프린트 진행현황, Play ToDo 하위 페이지 부모 |
| Play DB | 720899 | 43개 Play 통계 테이블, 하위 페이지 링크 |
| Action Log | 786433 | 작업 이력 append |
| EXT_Desk_D01 ToDo | 753719 | 세미나파이프라인 세부 작업 |

## MCP Tools 사용

| Tool | 용도 |
|------|------|
| `confluence.search_pages` | 페이지 검색 |
| `confluence.get_page` | 페이지 조회 |
| `confluence.create_page` | 페이지 생성 |
| `confluence.update_page` | 페이지 수정 |
| `confluence.append_to_page` | 내용 추가 |
| `confluence.db_query` | DB 조회 |
| `confluence.db_upsert_row` | DB 행 업데이트 |
| `confluence.db_insert_row` | DB 행 추가 |

## 동기화 유형

### 1. 실시간 동기화 (이벤트 기반)

```python
async def on_signal_created(signal: Signal):
    # 1. Action Log에 기록
    await confluence.db_insert_row(
        database_id=ACTION_LOG_DB_ID,
        data={
            "log_id": generate_log_id(),
            "play_id": signal.play_id,
            "action_type": "Signal",
            "title": signal.title,
            "url": signal.url,
            "actor": signal.owner,
            "created_at": now()
        }
    )
    
    # 2. Live doc에 append
    await confluence.append_to_page(
        page_id=get_live_doc_id(signal.play_id),
        append_md=format_signal_log(signal)
    )
```

### 2. 배치 동기화 (주간)

```python
async def weekly_sync():
    # Play DB QTD 집계 업데이트
    for play_id in active_plays:
        stats = await calculate_qtd_stats(play_id)
        
        await confluence.db_upsert_row(
            database_id=PLAY_DB_ID,
            row_id=play_id,
            data={
                "activity_qtd": stats.activity_count,
                "signal_qtd": stats.signal_count,
                "brief_qtd": stats.brief_count,
                "s2_qtd": stats.s2_count,
                "s3_qtd": stats.s3_count,
                "status": calculate_rag_status(stats),
                "last_updated": now()
            }
        )
```

## 이벤트 핸들러

| 이벤트 | 처리 |
|--------|------|
| `activity.created` | Action Log + Live doc |
| `signal.created` | Action Log + Live doc |
| `signal.scored` | Live doc update |
| `brief.created` | Action Log + Live doc + Play DB |
| `validation.completed` | Live doc + Play DB status |
| `pilot.started` | Live doc + Play DB S3 |

## 에러 처리

```python
async def safe_sync(operation, retries=3):
    for attempt in range(retries):
        try:
            return await operation()
        except ConfluenceAPIError as e:
            if attempt == retries - 1:
                # 로컬 큐에 저장 후 나중에 재시도
                await queue_for_retry(operation)
                raise
            await asyncio.sleep(2 ** attempt)
```

## 충돌 방지

```python
# 버전 기반 업데이트 (낙관적 락)
async def safe_update_page(page_id, new_content):
    page = await confluence.get_page(page_id)
    current_version = page['version']
    
    try:
        await confluence.update_page(
            page_id=page_id,
            body_md=new_content,
            version=current_version  # 버전 명시
        )
    except VersionConflictError:
        # 최신 버전 재조회 후 재시도
        await safe_update_page(page_id, new_content)
```

## 설정

```json
{
  "agent_id": "confluence_sync",
  "skill": "ax-confluence",
  "pages": {
    "project_todo": "${CONFLUENCE_TODO_PAGE_ID}",
    "play_db": "${CONFLUENCE_PLAY_DB_PAGE_ID}",
    "action_log": "${CONFLUENCE_ACTION_LOG_PAGE_ID}"
  },
  "play_todo_pages": {
    "EXT_Desk_D01": "753719"
  },
  "sync_schedule": "0 18 * * 5",
  "retry_count": 3,
  "retry_delay": 2
}
```

## Play ToDo 페이지 생성

새 Play의 ToDo 페이지 생성 흐름:

```python
async def create_play_todo_page(play_id: str, todo_content: str):
    """Play별 ToDo 하위 페이지 생성"""

    # 1. Project TODO 하위에 페이지 생성
    result = await confluence.create_page(
        title=f"{play_id} ToDo List",
        body_md=todo_content,
        parent_id=CONFLUENCE_TODO_PAGE_ID  # 720932
    )
    page_id = result["page_id"]
    page_url = result["url"]

    # 2. Project TODO에 링크 추가
    await confluence.append_to_page(
        page_id=CONFLUENCE_TODO_PAGE_ID,
        append_md=f"\n- [{play_id} ToDo List]({page_url})"
    )

    # 3. Play DB에 링크 추가
    await confluence.append_to_page(
        page_id=CONFLUENCE_PLAY_DB_PAGE_ID,  # 720899
        append_md=f"\n- [{play_id} ToDo List]({page_url})"
    )

    return {"page_id": page_id, "url": page_url}
```
