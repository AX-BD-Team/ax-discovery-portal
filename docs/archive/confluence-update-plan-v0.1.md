# Confluence 업데이트 계획

> AX Discovery Portal 프로젝트 진행 상황 및 향후 계획 Confluence 동기화

**작성일**: 2026-01-17
**버전**: v0.5.0 (PoC Week 6)

---

## 📋 업데이트 대상 페이지

### 1. 프로젝트 현황 페이지
**페이지 제목**: `AX Discovery Portal - 프로젝트 현황`
**Space Key**: `AX` (또는 지정된 Space)

### 2. 기술 문서 페이지
**페이지 제목**: `AX Discovery Portal - 기술 아키텍처`

### 3. 주간 리포트 페이지
**페이지 제목**: `AX Discovery Portal - Week 6 Progress Report`

---

## 📊 업데이트 내용

### 섹션 1: 프로젝트 개요 (현황 페이지)

```markdown
## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **프로젝트명** | AX Discovery Portal |
| **버전** | v0.5.0 (PoC) |
| **상태** | 🟢 PoC 진행 중 (Week 6 / 6) |
| **목표** | 멀티에이전트 기반 사업기회 포착 엔진 |

### 핵심 가치 제안
- Activity → Signal → Scorecard → Brief → Validation(S2) → Pilot(S3) 파이프라인 자동화
- 3원천(KT/그룹사/대외) × 5채널 사업기회 신호 수집
- Confluence를 System-of-Record로 활용 (Play DB + Live doc)
- 멀티에이전트 협업으로 BD팀 업무 효율 극대화

### PoC 주간 목표
| 메트릭 | 목표 | 현황 |
|--------|------|------|
| Activity | 20+/주 | 🔄 측정 중 |
| Signal | 30+/주 | 🔄 측정 중 |
| Brief | 6+/주 | 🔄 측정 중 |
| S2 | 2~4/주 | 🔄 측정 중 |

### 리드타임 목표
- Signal → Brief: ≤7일
- Brief → S2: ≤14일
```

---

### 섹션 2: 완료된 기능 (현황 페이지)

```markdown
## ✅ 완료된 기능 (v0.5.0 기준)

### 워크플로 파이프라인 (7개 구현 완료)

| ID | 워크플로 | 설명 | 상태 |
|----|----------|------|------|
| WF-01 | Seminar Pipeline | 세미나 URL → Activity → Signal | ✅ 완료 |
| WF-02 | Interview-to-Brief | 인터뷰 노트 → Signal → Scorecard → Brief | ✅ 완료 |
| WF-03 | VoC Mining | VoC 데이터 → 테마 추출 → Signal | ✅ 완료 |
| WF-04 | Inbound Triage | 인바운드 요청 → 중복체크 → Play 라우팅 | ✅ 완료 |
| WF-05 | KPI Digest | 주간/월간 KPI 리포트 생성 | ✅ 완료 |
| WF-06 | Confluence Sync | DB ↔ Confluence 양방향 동기화 | ✅ 완료 |
| WF-07 | External Scout | 외부 세미나 배치 수집 (RSS/Festa/Eventbrite) | ✅ 완료 |

### 에이전트 시스템 (8개)

| 에이전트 | 역할 |
|----------|------|
| orchestrator | 워크플로 실행 및 서브에이전트 조율 |
| external_scout | 외부 세미나/리포트/뉴스 수집 |
| interview_miner | 인터뷰 노트에서 Pain Point/니즈 추출 |
| voc_analyst | VoC 데이터 클러스터링 및 테마화 |
| scorecard_evaluator | Signal 정량 평가 (100점 만점, 5차원) |
| brief_writer | 1-Page Brief 자동 생성 |
| confluence_sync | Confluence DB/Live doc 자동 업데이트 |
| governance | 위험 도구 차단/승인/감사 |

### API 엔드포인트 (40+ 개)

**주요 라우터**:
- `/api/auth` - JWT 인증
- `/api/inbox` - Signal 관리
- `/api/activities` - Activity 조회
- `/api/scorecard` - Scorecard 평가
- `/api/brief` - Brief 관리
- `/api/plays` - Play Dashboard
- `/api/workflows` - 워크플로 실행
- `/api/webhooks` - 웹훅 수신
- `/api/ontology` - Knowledge Graph
- `/api/xai` - Explainable AI
- `/api/search` - 시맨틱 검색

### 인프라 & 배포

| 컴포넌트 | 플랫폼 | 상태 |
|----------|--------|------|
| Backend API | Render | ✅ 배포됨 |
| Frontend | Cloudflare Pages | ✅ 배포됨 |
| Database | PostgreSQL (Render) | ✅ 운영 중 |
| Vector DB | Cloudflare Vectorize | ✅ 운영 중 |
| CI/CD | GitHub Actions | ✅ 자동화 |
```

---

### 섹션 3: 최근 개발 현황 (Week 6)

```markdown
## 🚧 최근 개발 현황 (Week 6)

### 신규 구현

#### 1. 외부 세미나 수집 시스템 (WF-07: External Scout) 🔍
- **다중 소스 수집기**: RSS, Festa, Eventbrite
- **ActivityRepository**: Entity 테이블 기반 Activity 저장소
- **ExternalScoutPipeline**: 배치 수집 워크플로
- **웹훅 엔드포인트**: 실시간 이벤트 수신
  - `POST /api/webhooks/seminar/rss`
  - `POST /api/webhooks/seminar/festa`
  - `POST /api/webhooks/seminar/eventbrite`

#### 2. 세미나-BD 온톨로지 통합 (WF-01 확장) 🧠
- **LLMExtractionService**: Claude API 기반 엔티티/관계 추출
- **EntityResolutionService**: 동일 엔티티 식별 및 병합
- **OntologyIntegrationService**: 추출 결과 → Entity/Triple 변환
- **SeminarPipelineWithOntology**: 10단계 온톨로지 통합 워크플로
  1. URL 입력 → 2. Activity Entity 생성
  3. LLM 기반 엔티티 추출 → 4. Entity Resolution
  5. Signal 생성 → 6. Triple 관계 생성
  7. 도메인/레인지 검증 → 8. DB 저장
  9. Confluence 동기화 → 10. 이벤트 발행

#### 3. 테스트 커버리지 강화 🧪
- **단위 테스트 133개 추가** (총 500+ 테스트)
  - Activity Repository: 17개
  - External Collectors: 35개
  - Webhook Processor: 29개
  - Ontology Integration: 52개
- **SQLite/PostgreSQL 호환성** 수정
  - `json_value()` 함수로 DB 호환 JSON 쿼리

#### 4. 대시보드 KPI 위젯 🎨
- 실시간 KPI 위젯 (Activity, Signal, Brief, S2)
- 사이클 타임 표시 (Signal→Brief, Brief→S2)
- Toast 알림 시스템
- 글로벌 에러 핸들링

### 코드 품질
- **ruff**: 0 errors
- **mypy**: 0 errors (85개 타입 오류 수정)
- **pytest**: 500+ tests passing
```

---

### 섹션 4: 기술 스택 (기술 문서 페이지)

```markdown
## 🛠️ 기술 스택

### Backend
| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11+ | 런타임 |
| FastAPI | 0.115+ | REST API |
| Claude Agent SDK | 0.1.19+ | 에이전트 오케스트레이션 |
| Claude Sonnet 4 | 20250514 | LLM 엔진 |
| PostgreSQL | 15+ | 메인 DB |
| SQLAlchemy | 2.0+ | ORM |
| Alembic | 1.14+ | 마이그레이션 |

### Frontend
| 기술 | 버전 | 용도 |
|------|------|------|
| Next.js | 15 | React 프레임워크 |
| TypeScript | 5.0+ | 타입 시스템 |
| Tailwind CSS | 3.4+ | 스타일링 |
| shadcn/ui | latest | UI 컴포넌트 |
| TanStack Query | 5.0+ | 서버 상태 관리 |

### 인프라
| 서비스 | 용도 |
|--------|------|
| Render | Backend 호스팅 |
| Cloudflare Pages | Frontend 호스팅 |
| Cloudflare Vectorize | 벡터 DB |
| GitHub Actions | CI/CD |

### 통합
| 서비스 | 용도 |
|--------|------|
| Confluence | System-of-Record |
| Teams | 알림/승인 |
| Slack | 알림/승인 |
```

---

### 섹션 5: 향후 계획 (현황 페이지)

```markdown
## 📅 향후 계획

### Week 6 남은 작업 (PoC 마무리)

| 작업 | 우선순위 | 상태 |
|------|----------|------|
| PoC 목표 달성 검증 | P0 | 🔄 진행 중 |
| E2E 테스트 완료 | P0 | 🔄 진행 중 |
| 데모 시연 준비 | P0 | ✅ 완료 |
| v0.5.0 릴리스 | P0 | 🔄 대기 |

### PoC 이후 로드맵 (v0.6.0+)

#### Phase 1: 안정화 (2주)
- [ ] 프로덕션 모니터링 (Sentry)
- [ ] 성능 최적화
- [ ] 사용자 피드백 반영

#### Phase 2: 확장 (4주)
- [ ] Confluence Database API 완성
- [ ] 모바일 앱 (PWA)
- [ ] 고급 분석 대시보드

#### Phase 3: 고도화 (지속)
- [ ] ML 기반 Signal 스코어링
- [ ] 자동 Play 라우팅 최적화
- [ ] 예측 분석

### 성공 지표

| 지표 | 현재 | 목표 |
|------|------|------|
| 테스트 커버리지 | 80%+ | 90%+ |
| API 응답 시간 | <500ms | <300ms |
| 사용자 만족도 | - | 4.0+/5.0 |
```

---

## 🔄 Confluence 업데이트 절차

### 단계 1: 페이지 확인
```bash
# Confluence API로 기존 페이지 확인
curl -X GET "https://your-domain.atlassian.net/wiki/rest/api/content" \
  -H "Authorization: Bearer $CONFLUENCE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"title": "AX Discovery Portal", "spaceKey": "AX"}'
```

### 단계 2: 페이지 생성/업데이트
```python
# WF-06 Confluence Sync API 사용
POST /api/workflows/confluence-sync
{
  "targets": [
    {
      "target_type": "page",
      "action": "update",
      "page_id": "existing-page-id",
      "title": "AX Discovery Portal - 프로젝트 현황",
      "body_content": "... 위 섹션 내용 ..."
    }
  ],
  "sync_mode": "immediate"
}
```

### 단계 3: 검증
- [ ] 프로젝트 현황 페이지 업데이트 확인
- [ ] 기술 문서 페이지 업데이트 확인
- [ ] 주간 리포트 페이지 생성 확인
- [ ] 링크 및 포맷팅 검증

---

## 📝 업데이트 체크리스트

### 프로젝트 현황 페이지
- [ ] 프로젝트 개요 섹션 업데이트
- [ ] 완료된 기능 섹션 업데이트
- [ ] 최근 개발 현황 추가
- [ ] 향후 계획 업데이트

### 기술 문서 페이지
- [ ] 기술 스택 표 업데이트
- [ ] 아키텍처 다이어그램 업데이트 (필요시)
- [ ] API 엔드포인트 목록 업데이트

### 주간 리포트 페이지
- [ ] Week 6 신규 페이지 생성
- [ ] 주요 성과 기록
- [ ] 이슈/블로커 기록
- [ ] 다음 주 계획 작성

---

## 💡 추가 제안

### 1. Action Log 업데이트
최근 작업들을 Action Log에 기록:
- `WF-07 External Scout 구현 완료`
- `온톨로지 통합 WF-01 확장`
- `단위 테스트 133개 추가`

### 2. Play DB 업데이트
관련 Play의 QTD 집계 갱신:
- `EXT_Desk_D01_Seminar`: activity_qtd 증가
- 전체 signal_qtd, brief_qtd 업데이트

### 3. KPI Digest 생성
```bash
# KPI Digest 워크플로 실행
POST /api/workflows/kpi-digest
{
  "period": "weekly",
  "send_to_teams": true
}
```

---

**작성자**: Claude Code
**검토 필요**: BD팀 담당자
