# AX Discovery/Portal 자동화 플랫폼 – Claude Code 착수용 개발 기획서 + 스캐폴딩 (v0.1)

> 목적: **AX BD 아이디어/기회 포착(3원천×5채널 + 40+ Action Play)**을 “활동 기록 → Signal → Scorecard → 1p Brief → Validation(S2) → Pilot-ready(S3)”로 **자동 전환**하고, 이를 **Confluence DB + Live doc**에 자동 업데이트하는 **멀티 에이전트 자동화 플랫폼**을 **Claude Code/Claude Agent SDK**로 바로 개발 시작할 수 있는 형태로 구체화한다.

---

## 0. 한 줄 결론

- **Confluence를 System-of-Record**로 두고(Play 진행현황 DB + Action Log DB + Play Live doc),
- **Claude Agent SDK 기반 멀티에이전트 런타임**이 수집/정리/평가/문서화를 자동화하며,
- 웹/앱은 **Unified Inbox + Scorecard + Brief + Sprint + Dashboard**로 “행동→전환→계량”을 강제한다.

---

## 1. PoC 범위(6주) – Definition of Done

### 1.1 PoC 목표(정량)
- 주간 기준
  - **Activity 20+**
  - **Signal 30+**
  - **Brief 6+**
  - **S2(Validated) 2~4**
- 리드타임
  - Signal→Brief **≤ 7일**
  - Brief→S2 **≤ 14일 착수/판정**
- 운영체계
  - 40+ Play 중 **S2 목표가 있는 Play 12~15개만** 우선 가동
  - Play DB는 **주 1회(금 EOD)** 업데이트 룰 적용

### 1.2 PoC 필수 기능
1) **Signal Inbox**: 생성/중복/태깅/담당자 배정  
2) **Scorecard**: 100점 채점 + Red-flag + 추천(Go/Pivot/Hold)  
3) **1p Brief 자동 생성**: 템플릿 기반 생성 + 증거 링크 자동 첨부  
4) **Confluence Sync**: Play 진행현황 DB(QTD), Action Log, Live doc에 자동 기록  
5) **KPI Digest**: Play별 전환율/리드타임/지연 경고(Weekly)  

---

## 2. 상위 아키텍처(웹/앱 공통)

### 2.1 구성요소
- **Client**: Web(Next.js) + App(PWA/React Native) – 동일 API 사용
- **Backend API**: FastAPI(권장) 또는 Node – 인증/권한/업무 API 제공
- **Agent Runtime**: Claude Agent SDK 컨테이너(하이브리드 세션)
- **Integrations**: MCP 서버(Confluence/Teams/Calendar/CRM/내부데이터)
- **Data**: Postgres(정형) + Object Storage(첨부) + Observability(로그/트레이스)

### 2.2 데이터 흐름
1) Client/Automation → **Activity 생성**
2) Agent가 Activity에서 **Signal 추출(JSON Schema)**
3) Evaluator Agent가 **Scorecard** 생성
4) Writer Agent가 **Brief 생성 + Confluence 페이지 생성**
5) Sprint/Validation 기록 → S2/S3 업데이트
6) Confluence DB(Play/QTD) + Live doc에 자동 업데이트

---

## 3. 멀티 에이전트 설계(역할/책임)

> 에이전트는 “역할 기반”으로 나누고, 오케스트레이터가 워크플로를 실행한다.

### 3.1 Agent 목록
- **Orchestrator**: 워크플로 실행/분기/승인 요청, 서브에이전트 호출
- **ExternalScout**: 외부 세미나/리포트/뉴스 수집→Activity 생성
- **InterviewMiner**: 미팅/인터뷰 노트 → Signal/Brief 후보 추출
- **VoCAnalyst**: VoC/티켓/로그 → 테마화/Signal 생성
- **ScorecardEvaluator**: Scorecard 채점(정형 JSON 출력)
- **BriefWriter**: 1p Brief 생성(정형 JSON + Confluence 문서)
- **SprintFacilitator**: 5-day 스프린트 플랜/체크리스트 생성(옵션)
- **ConfluenceSync**: Confluence DB/Live doc 업데이트 전담
- **GovernanceAgent**: 위험 툴 호출 차단/승인/감사 로그

---

## 4. Workflow(최소 6개) – PoC 우선순위

### WF-01 Seminar Pipeline (External Desk)
- 입력: 세미나 후보 URL/메타
- 출력: Activity → AAR 템플릿 → Signal 2개 → Follow-up Task → Brief 후보
- 트리거: 수동(/ax:seminar-add) + 주간 배치

### WF-02 Interview-to-Brief (Sales/PM)
- 입력: 인터뷰 노트(텍스트/문서 링크)
- 출력: Signal → Scorecard → Brief 생성(승인 후)

### WF-03 VoC Mining (KT/Group Desk)
- 입력: VoC/티켓 샘플(링크/데이터 요약)
- 출력: 테마 5개 + Signal 다건 + Brief 후보 1~2개

### WF-04 Inbound Triage (Internal/External)
- 입력: Intake 폼 제출
- 출력: 중복 체크 → Scorecard 초안 → Brief 승격(48h SLA)

### WF-05 KPI Digest (Ops)
- 입력: Postgres/Confluence DB
- 출력: 주간 KPI 리포트 + 지연 Play/Action 경고

### WF-06 Confluence Sync (All)
- 입력: 모든 단계 산출물
- 출력: Play 진행현황 DB(QTD), Action Log, Live doc append

---

## 5. Claude Code에서 바로 시작하기 – 레포 구조(권장)

> 아래 파일 트리를 그대로 만들고, Claude Code로 각 파일을 채워 나간다.

```text
ax-discovery-portal/
  README.md
  .env.example
  .claude/
    settings.json
    mcp.json
    skills/
      ax-scorecard/SKILL.md
      ax-brief/SKILL.md
      ax-sprint/SKILL.md
      ax-seminar/SKILL.md
      ax-confluence/SKILL.md
    agents/
      orchestrator.md
      external_scout.md
      scorecard_evaluator.md
      brief_writer.md
      confluence_sync.md
      governance.md
    commands/
      ax_triage.md
      ax_brief.md
      ax_seminar_add.md
      ax_kpi_digest.md
    hooks/
      pre_tool_use.py
      post_tool_use.py
  backend/
    api/
      main.py
      routers/
        inbox.py
        scorecard.py
        brief.py
        play_dashboard.py
      deps.py
    agent_runtime/
      runner.py
      workflows/
        wf_seminar_pipeline.py
        wf_interview_to_brief.py
        wf_voc_mining.py
        wf_inbound_triage.py
        wf_kpi_digest.py
      models/
        signal.schema.json
        scorecard.schema.json
        brief.schema.json
        validation.schema.json
        pilot_ready.schema.json
        play_record.schema.json
        action_log.schema.json
    integrations/
      mcp_confluence/
        server.py
        tools.py
        models.py
        README.md
      mcp_teams/
        README.md
        server.py
  app/
    web/
      README.md
    mobile/
      README.md
```

---

## 6. .claude 설정(초기)

### 6.1 `.claude/settings.json` (예시)
> 실제 옵션명은 환경/버전에 따라 다를 수 있으니, **“허용할 도구/모드/스킬 로딩”**이 핵심이라는 점을 유지한 채 조정한다.

```json
{
  "setting_sources": ["project", "user"],
  "allowed_tools": ["Skill", "mcp", "bash", "files"],
  "permission_mode": "ask",
  "default_agent": "orchestrator"
}
```

### 6.2 `.claude/mcp.json` (예시)
- Confluence MCP / Teams MCP 등을 등록한다(개발 초기에는 Confluence만 우선).

```json
{
  "mcpServers": {
    "confluence": {
      "command": "python",
      "args": ["backend/integrations/mcp_confluence/server.py"],
      "env": {
        "CONFLUENCE_BASE_URL": "${CONFLUENCE_BASE_URL}",
        "CONFLUENCE_API_TOKEN": "${CONFLUENCE_API_TOKEN}",
        "CONFLUENCE_USER_EMAIL": "${CONFLUENCE_USER_EMAIL}",
        "CONFLUENCE_SPACE_KEY": "${CONFLUENCE_SPACE_KEY}"
      }
    }
  }
}
```

---

## 7. Skills (팀 표준을 자동 적용)

> SKILL.md는 “규칙 + 출력 형식”을 명시한다. 모델이 호출하면 항상 같은 품질을 유지한다.

### 7.1 `ax-scorecard/SKILL.md` (요약)
- 입력: Signal JSON
- 출력: Scorecard JSON(0~100, red flags, recommendation)

필수 규칙:
- Red-flag 조건(데이터 접근 불가/규제 불가/Buyer 부재 등) 명시
- 총점 산식(가중치) 고정

### 7.2 `ax-brief/SKILL.md`
- 입력: Scorecard 통과 Signal
- 출력: Brief JSON + Confluence 페이지 마크다운 본문(선택)

### 7.3 `ax-seminar/SKILL.md`
- 입력: 세미나 URL/메타 + 관심 테마
- 출력: Activity + AAR 템플릿 + Signal 2개

### 7.4 `ax-confluence/SKILL.md`
- 입력: (Play ID, 단계, 산출물 링크)
- 출력: Confluence DB/Live doc에 어떻게 기록할지 “작성 규칙”

---

## 8. Commands (Claude Code에서 수동 실행 진입점)

> 팀이 “바로 써먹는 버튼” 역할. PoC는 command 중심으로 시작해도 충분하다.

- `/ax:seminar-add` : 세미나 URL 입력 → WF-01 실행
- `/ax:triage` : Inbox에서 선택한 Signal들을 Scorecard 큐로
- `/ax:brief` : Scorecard 통과 Signal → Brief 생성
- `/ax:kpi-digest` : 주간 KPI 요약 생성 + Confluence/Teams 공지(옵션)

각 command 파일(`.claude/commands/*.md`)에는:
- 입력 인자
- 실행할 워크플로
- 출력(어디에 기록되는지)
- 에러/예외 처리 규칙

---

## 9. Confluence MCP 서버 – Tool Spec (PoC 최소)

> PoC는 Confluence만 제대로 붙으면 운영이 “기록 중심”으로 굴러간다.

### 9.1 MCP Tools 목록(권장)

#### (A) 페이지/라이브문서
- `confluence.search_pages(query: str, limit: int=10) -> {pages:[...]}`
- `confluence.get_page(page_id: str) -> {id,title,body,version,...}`
- `confluence.create_page(space_key: str, parent_id: str|null, title: str, body_md: str, labels: [str]) -> {page_id,url}`
- `confluence.update_page(page_id: str, body_md: str, version: int) -> {page_id,url,version}`
- `confluence.append_to_page(page_id: str, append_md: str) -> {page_id,url}`
- `confluence.add_labels(page_id: str, labels: [str]) -> {page_id,labels}`

#### (B) Database(Play 진행현황/Action Log)
> Confluence DB는 구현 방식이 계정/테넌트마다 달라질 수 있으므로 PoC에서는 **“DB를 페이지 내 테이블/DB API”** 중 한 방식을 먼저 택한다.  
> 권장: DB API가 가능하면 `db_upsert_row` 형태, 아니면 “표(테이블) 업데이트”로 우회.

- `confluence.db_query(database_id: str, filter: object) -> {rows:[...]}`
- `confluence.db_upsert_row(database_id: str, key: {field:str,value:any}, fields: object) -> {row_id}`
- `confluence.db_increment(database_id: str, key: {...}, field: str, delta: number) -> {row_id,new_value}`

#### (C) 템플릿 기반 Live doc 생성(선택)
- `confluence.create_live_doc(parent_id: str, title: str, template_id: str|null) -> {page_id,url}`

### 9.2 Tool I/O 예시(JSON-RPC 스타일)

#### create_page
```json
{
  "tool": "confluence.create_page",
  "input": {
    "space_key": "AXBD",
    "parent_id": "123456",
    "title": "[BRIEF] 상담요약 자동화로 AHT 15%↓",
    "body_md": "# 1p Opportunity Brief\n...",
    "labels": ["ax-bd", "brief", "2026q1", "play:KT_Sales_SP01"]
  }
}
```

#### db_upsert_row (Play 진행현황)
```json
{
  "tool": "confluence.db_upsert_row",
  "input": {
    "database_id": "PLAY_DB_ID",
    "key": {"field": "Play ID", "value": "EXT_Desk_D01_세미나파이프라인"},
    "fields": {
      "Activity 실적(QTD)": 3,
      "Signal 실적(QTD)": 6,
      "Brief 실적(QTD)": 1,
      "S2 실적(QTD)": 0,
      "상태(RAG)": "G",
      "Next Action": "이번주 행사 1건 참석→AAR→Signal 2건",
      "Next Action Due": "2026-01-16"
    }
  }
}
```

---

## 10. Structured Output JSON Schemas (바로 사용 가능)

> 아래 JSON Schema 파일을 그대로 `backend/agent_runtime/models/*.schema.json`로 저장한다.

### 10.1 `signal.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Signal",
  "type": "object",
  "required": ["signal_id", "title", "summary", "origin", "channel", "play_id", "evidence", "created_at"],
  "properties": {
    "signal_id": {"type": "string", "description": "UUID or ULID"},
    "title": {"type": "string"},
    "summary": {"type": "string"},
    "origin": {"type": "string", "enum": ["KT", "그룹사", "대외", "공통"]},
    "channel": {"type": "string", "enum": ["데스크", "자사활동", "영업/PM", "인바운드", "아웃바운드"]},
    "play_id": {"type": "string"},
    "industry": {"type": "string"},
    "customer_or_account": {"type": "string"},
    "pain_statement": {"type": "string"},
    "current_workflow": {"type": "string"},
    "proposed_value": {"type": "string"},
    "kpi_hypothesis": {
      "type": "array",
      "items": {"type": "string"},
      "description": "예: AHT 15%↓, 처리시간 30%↓"
    },
    "evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "title", "url"],
        "properties": {
          "type": {"type": "string", "enum": ["link", "doc", "ticket", "meeting_note", "dataset", "image"]},
          "title": {"type": "string"},
          "url": {"type": "string"},
          "note": {"type": "string"}
        }
      }
    },
    "tags": {"type": "array", "items": {"type": "string"}},
    "owner": {"type": "string"},
    "created_at": {"type": "string", "format": "date-time"},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
  }
}
```

### 10.2 `scorecard.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Scorecard",
  "type": "object",
  "required": ["signal_id", "total_score", "dimension_scores", "red_flags", "recommendation", "scored_at"],
  "properties": {
    "signal_id": {"type": "string"},
    "total_score": {"type": "number", "minimum": 0, "maximum": 100},
    "dimension_scores": {
      "type": "object",
      "required": ["problem_severity", "willingness_to_pay", "data_availability", "feasibility", "strategic_fit"],
      "properties": {
        "problem_severity": {"type": "number", "minimum": 0, "maximum": 20},
        "willingness_to_pay": {"type": "number", "minimum": 0, "maximum": 20},
        "data_availability": {"type": "number", "minimum": 0, "maximum": 20},
        "feasibility": {"type": "number", "minimum": 0, "maximum": 20},
        "strategic_fit": {"type": "number", "minimum": 0, "maximum": 20}
      }
    },
    "red_flags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "예: 데이터 접근 불가, Buyer/예산 오너 부재"
    },
    "recommendation": {
      "type": "object",
      "required": ["decision", "next_step"],
      "properties": {
        "decision": {"type": "string", "enum": ["GO", "PIVOT", "HOLD", "NO_GO"]},
        "next_step": {"type": "string", "enum": ["BRIEF", "VALIDATION", "PILOT_READY", "DROP", "NEED_MORE_EVIDENCE"]},
        "rationale": {"type": "string"}
      }
    },
    "scored_by": {"type": "string"},
    "scored_at": {"type": "string", "format": "date-time"}
  }
}
```

### 10.3 `brief.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "OpportunityBrief",
  "type": "object",
  "required": ["brief_id", "signal_id", "title", "customer", "problem", "solution_hypothesis", "kpis", "evidence", "validation_plan", "owner", "created_at"],
  "properties": {
    "brief_id": {"type": "string"},
    "signal_id": {"type": "string"},
    "title": {"type": "string"},
    "customer": {
      "type": "object",
      "required": ["segment", "buyer_role"],
      "properties": {
        "segment": {"type": "string"},
        "buyer_role": {"type": "string"},
        "users": {"type": "string"},
        "account": {"type": "string"}
      }
    },
    "problem": {
      "type": "object",
      "required": ["pain", "why_now"],
      "properties": {
        "pain": {"type": "string"},
        "why_now": {"type": "string"},
        "current_process": {"type": "string"}
      }
    },
    "solution_hypothesis": {
      "type": "object",
      "required": ["approach", "integration_points"],
      "properties": {
        "approach": {"type": "string"},
        "integration_points": {"type": "array", "items": {"type": "string"}},
        "data_needed": {"type": "array", "items": {"type": "string"}}
      }
    },
    "kpis": {"type": "array", "items": {"type": "string"}},
    "evidence": {"type": "array", "items": {"type": "string"}},
    "validation_plan": {
      "type": "object",
      "required": ["questions", "method", "success_criteria", "timebox_days"],
      "properties": {
        "questions": {"type": "array", "items": {"type": "string"}},
        "method": {"type": "string", "enum": ["5DAY_SPRINT", "INTERVIEW", "DATA_ANALYSIS", "BUYER_REVIEW"]},
        "success_criteria": {"type": "array", "items": {"type": "string"}},
        "timebox_days": {"type": "integer", "minimum": 1, "maximum": 30}
      }
    },
    "mvp_scope": {
      "type": "object",
      "properties": {
        "in_scope": {"type": "array", "items": {"type": "string"}},
        "out_of_scope": {"type": "array", "items": {"type": "string"}}
      }
    },
    "risks": {"type": "array", "items": {"type": "string"}},
    "owner": {"type": "string"},
    "confluence_url": {"type": "string"},
    "created_at": {"type": "string", "format": "date-time"}
  }
}
```

### 10.4 `validation.schema.json` (S2)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ValidationResult",
  "type": "object",
  "required": ["validation_id", "brief_id", "method", "decision", "findings", "validated_at"],
  "properties": {
    "validation_id": {"type": "string"},
    "brief_id": {"type": "string"},
    "method": {"type": "string", "enum": ["5DAY_SPRINT", "INTERVIEW", "DATA_ANALYSIS", "POC"]},
    "decision": {"type": "string", "enum": ["GO", "PIVOT", "NO_GO"]},
    "findings": {"type": "array", "items": {"type": "string"}},
    "evidence_links": {"type": "array", "items": {"type": "string"}},
    "next_actions": {"type": "array", "items": {"type": "string"}},
    "validated_at": {"type": "string", "format": "date-time"}
  }
}
```

### 10.5 `pilot_ready.schema.json` (S3)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PilotReady",
  "type": "object",
  "required": ["pilot_id", "brief_id", "scope", "success_metrics", "data_access_plan", "security_plan", "stakeholders", "timeline"],
  "properties": {
    "pilot_id": {"type": "string"},
    "brief_id": {"type": "string"},
    "scope": {
      "type": "object",
      "required": ["in_scope", "out_of_scope"],
      "properties": {
        "in_scope": {"type": "array", "items": {"type": "string"}},
        "out_of_scope": {"type": "array", "items": {"type": "string"}}
      }
    },
    "success_metrics": {"type": "array", "items": {"type": "string"}},
    "data_access_plan": {"type": "array", "items": {"type": "string"}},
    "security_plan": {"type": "array", "items": {"type": "string"}},
    "stakeholders": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["role", "name_or_team"],
        "properties": {
          "role": {"type": "string"},
          "name_or_team": {"type": "string"}
        }
      }
    },
    "timeline": {
      "type": "object",
      "required": ["start_date", "end_date"],
      "properties": {
        "start_date": {"type": "string", "format": "date"},
        "end_date": {"type": "string", "format": "date"}
      }
    },
    "assumptions": {"type": "array", "items": {"type": "string"}}
  }
}
```

---

## 11. Confluence에 기록하는 규칙(Play DB + Live doc)

### 11.1 Play 진행현황 DB(필수 필드 매핑)
- key: `Play ID`
- 업데이트 대상(QTD): Activity/Signal/Brief/S2
- 매주 금요일 EOD: 상태(RAG), Next Action, Due 업데이트

### 11.2 Live doc append 규칙(“사건 발생 시”)
- 세미나 참석 완료 → 24h 내 AAR 섹션 append
- Signal 생성 → 링크 2개 이상(evidence) 추가
- Brief 생성 → Confluence 페이지 URL 연결
- Validation 결과 → Decision/Next action 기록

> PoC에서는 “append_to_page”만 있어도 충분(업데이트 충돌 최소화).

---

## 12. 개발 순서(Claude Code 작업 지시서)

### Step 1) 레포/스키마/템플릿 생성 (Day 1~2)
- 위 파일 트리 생성
- JSON schema 5개 저장
- Skills/Commands 문서 뼈대 작성

### Step 2) Confluence MCP 서버(최소 툴 5개) (Day 3~5)
- create_page / append_to_page / search_pages / db_upsert_row / db_query
- 우선 “Play DB”는 Confluence DB API가 어렵다면 **임시로 Postgres에 적재 후** Confluence는 페이지 테이블로 업데이트(우회)도 가능

### Step 3) WF-01 Seminar Pipeline 구현 (Week 2)
- `/ax:seminar-add URL` → Activity 생성 → Signal 2개 → Confluence Live doc 기록 → Play DB QTD +1/+2

### Step 4) WF-02 Interview-to-Brief 구현 (Week 3)
- 인터뷰 노트 입력 → Signal/Scorecard → 승인 후 Brief 생성 → Confluence 페이지 생성

### Step 5) KPI Digest 구현 (Week 4~5)
- Play별 목표 대비 페이싱/전환율/지연 표시
- “Y/R Play만” 자동 요약

### Step 6) Web UI(최소) (Week 5~6)
- Inbox 리스트 + 필터(원천/채널/Play)
- Signal 상세 + Scorecard 입력
- Brief 생성 버튼(승인 포함)

---

## 13. 리스크/의존성(초기)
- Confluence DB API 접근/권한이 제한될 수 있음 → **PoC는 Postgres SoR + Confluence는 “리포팅/링크 허브”**로 우회 가능
- 외부 세미나/뉴스 수집은 자동 크롤링 대신 **수동 입력(초기)**로 시작해도 충분
- 구매형 PoC/법무/보안 템플릿은 PoC 2단계로 분리(P2)

---

## 14. 부록 – Play ID ↔ Workflow 라우팅 규칙(예)
- `EXT_Desk_D01_*` → WF-01 Seminar
- `KT_Sales_*` → WF-02 Interview-to-Brief
- `KT_Desk_*` → WF-03 VoC Mining
- `*_Inbound_*` → WF-04 Inbound Triage
- `*_Outbound_OUT03_*` → WF-05 Sprint Kickoff

---

## 15. 다음 액션(팀 착수 체크리스트)
- [ ] Confluence Space/Parent Page/DB ID(Play DB, Action Log DB) 확보
- [ ] PoC 대상 Play 12~15개 선정(S2 목표 있는 Play 우선)
- [ ] `.env` 값 확정(Confluence token, space key)
- [ ] 레포 생성 + Claude Code 첫 커맨드 `/ax:seminar-add`로 end-to-end 성공

---

**이 문서는 “Claude Code에서 바로 만들기 시작”하도록 만든 초안이며, 실제 사용 중인 Confluence/Teams/SSO 환경 제약에 따라 Integration 부분은 PoC에서 단계적으로 조정한다.**
