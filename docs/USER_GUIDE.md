# AX Discovery Portal - 사용자 가이드

> BD팀을 위한 멀티에이전트 기반 사업기회 포착 엔진 사용 매뉴얼

**버전**: 0.4.0
**최종 업데이트**: 2026-01-16

---

## 목차

1. [Quick Start (5분 시작)](#1-quick-start-5분-시작)
2. [핵심 개념](#2-핵심-개념)
3. [워크플로 사용법](#3-워크플로-사용법)
4. [웹 UI 가이드](#4-웹-ui-가이드)
5. [API 사용법](#5-api-사용법)
6. [Claude Code 명령어](#6-claude-code-명령어)
7. [FAQ](#7-faq)

---

## 1. Quick Start (5분 시작)

### 1.1 웹 UI로 시작하기

```
1. 브라우저에서 접속
   → https://ax-discovery-portal.pages.dev

2. 로그인 (테스트 계정)
   → Email: test@kt.com
   → Password: test1234

3. 대시보드에서 현황 확인
   → Activity, Signal, Brief 카운트
   → 주간 KPI 요약

4. 첫 Signal 등록
   → Inbox → "Signal 등록" 버튼
   → 필수 정보 입력 후 저장
```

### 1.2 API로 시작하기

```bash
# 1. 헬스체크
curl https://ax-discovery-api-staging.onrender.com/health

# 2. Signal 목록 조회
curl https://ax-discovery-api-staging.onrender.com/api/inbox

# 3. Scorecard 목록 조회
curl https://ax-discovery-api-staging.onrender.com/api/scorecard

# 4. API 문서 확인
# 브라우저에서: https://ax-discovery-api-staging.onrender.com/docs
```

### 1.3 Claude Code로 시작하기

```bash
# 1. 프로젝트 디렉토리 이동
cd ax-discovery-portal

# 2. Claude Code 실행
claude

# 3. 세미나 등록 명령
> /ax:seminar-add

# 4. KPI 현황 확인
> /ax:kpi-digest
```

---

## 2. 핵심 개념

### 2.1 파이프라인 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    AX Discovery Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Activity    →    Signal    →    Scorecard    →    Brief        │
│  (수집)          (신호)         (평가)           (문서화)        │
│                                                                  │
│     ↓              ↓               ↓               ↓            │
│  세미나         사업기회        5차원          1-Page           │
│  인터뷰         포착           100점 평가      Brief            │
│  VoC                                                            │
│  인바운드                                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 주요 용어

| 용어 | 설명 | 예시 |
|------|------|------|
| **Activity** | 영업/BD 활동 기록 | 세미나 참석, 고객 미팅, 뉴스 스크랩 |
| **Signal** | 사업기회 신호 | "A사가 AI 고객센터에 관심" |
| **Scorecard** | Signal 평가 결과 | 5차원 100점 평가 (GO/HOLD/NO_GO) |
| **Brief** | 1-Page 사업기회 문서 | 경영진 보고용 요약 |
| **Play** | 사업기회 추진 단위 | "AI 고객센터 혁신" 프로젝트 |
| **Stage** | 진행 단계 | S1(Signal) → S2(Validation) → S3(Pilot) |

### 2.3 5차원 평가 기준

| 차원 | 설명 | 가중치 |
|------|------|--------|
| **Market Fit** | 시장 수요 및 타이밍 | 25% |
| **Org Synergy** | KT 역량 및 시너지 | 25% |
| **Tech Feasibility** | 기술 구현 가능성 | 20% |
| **Urgency** | 긴급성 및 경쟁 상황 | 15% |
| **Revenue Potential** | 매출 잠재력 | 15% |

**판정 기준**:
- **GO** (80점 이상): 즉시 추진
- **PIVOT** (60~79점): 수정 후 재검토
- **HOLD** (40~59점): 모니터링
- **NO_GO** (40점 미만): 중단

---

## 3. 워크플로 사용법

### 3.1 WF-01: Seminar Pipeline (세미나 등록)

**용도**: 세미나/컨퍼런스 참석 후 인사이트 기록

**입력**:
- 세미나 URL 또는 정보
- 발표 내용 요약
- 발견한 인사이트

**실행 방법**:

```bash
# Claude Code 명령
> /ax:seminar-add

# 또는 API 호출
curl -X POST https://api.example.com/api/inbox/seminar \
  -H "Content-Type: application/json" \
  -d '{
    "seminar_url": "https://example.com/seminar",
    "title": "AI 트렌드 2026",
    "summary": "주요 발표 내용...",
    "insights": ["인사이트1", "인사이트2"]
  }'
```

**출력**:
- Activity 자동 생성
- Signal 후보 추출
- AAR (After Action Review) 템플릿

---

### 3.2 WF-02: Interview-to-Brief (인터뷰 → Brief)

**용도**: 고객 인터뷰 내용을 Signal/Brief로 변환

**입력**:
- 인터뷰 녹취록 또는 메모
- 고객 정보 (회사, 담당자)
- Pain Point

**실행 방법**:

```bash
# API 호출
curl -X POST https://api.example.com/api/workflows/interview-to-brief \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "A사",
    "interviewee": "김부장",
    "transcript": "인터뷰 내용...",
    "pain_points": ["고객 대기 시간 증가", "상담원 이직률"]
  }'
```

**출력**:
- Signal 자동 생성
- Scorecard 초안 (5차원 평가)
- Brief 초안 (승인 대기)

---

### 3.3 WF-03: VoC Mining (VoC 분석)

**용도**: 대량 VoC 데이터에서 Signal 자동 추출

**지원 형식**: CSV, Excel, JSON, 텍스트

**실행 방법**:

```bash
# 미리보기 (분석만)
curl -X POST https://api.example.com/api/workflows/voc-mining/preview \
  -H "Content-Type: application/json" \
  -d '{
    "source": "customer_survey",
    "format": "csv",
    "content": "고객ID,피드백\n1,서비스 속도 개선 필요..."
  }'

# 실행 (Signal 생성)
curl -X POST https://api.example.com/api/workflows/voc-mining \
  -H "Content-Type: application/json" \
  -d '{
    "source": "customer_survey",
    "format": "csv",
    "content": "...",
    "auto_create_signals": true
  }'
```

**출력**:
- 테마별 분류
- Signal 후보 목록
- 중복 체크 결과

---

### 3.4 WF-04: Inbound Triage (인바운드 분류)

**용도**: 고객 문의를 자동 분류하고 Scorecard 생성

**입력**:
- 회사명, 담당자, 연락처
- 문의 유형, 설명
- 긴급도

**실행 방법**:

```bash
# Claude Code 명령
> /ax:triage

# 또는 API 호출
curl -X POST https://api.example.com/api/workflows/inbound-triage \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "B사",
    "contact_name": "이과장",
    "contact_email": "lee@b-company.com",
    "inquiry_type": "partnership",
    "description": "AI 솔루션 협력 문의",
    "urgency": "normal"
  }'
```

**SLA 기준**:
- URGENT: 24시간 내 응답
- NORMAL: 48시간 내 응답
- LOW: 72시간 내 응답

**출력**:
- Signal 자동 생성
- Play 자동 매칭
- Scorecard 초안
- SLA 타이머 시작

---

### 3.5 WF-05: KPI Digest (KPI 리포트)

**용도**: 주간/월간 KPI 현황 리포트 생성

**실행 방법**:

```bash
# Claude Code 명령
> /ax:kpi-digest

# 또는 API 호출 (주간)
curl "https://api.example.com/api/workflows/kpi-digest?period=weekly"

# 월간 리포트
curl "https://api.example.com/api/workflows/kpi-digest?period=monthly"
```

**출력 예시**:

```json
{
  "period": "2026-01-10 ~ 2026-01-16",
  "metrics": {
    "activity_count": 25,
    "signal_count": 32,
    "brief_count": 8,
    "s2_count": 3,
    "s3_count": 1
  },
  "lead_times": {
    "signal_to_brief_avg_days": 5.2,
    "brief_to_s2_avg_days": 12.1
  },
  "alerts": [
    {"type": "warning", "message": "Signal 목표 미달 (32/35)"}
  ],
  "top_plays": [
    {"play_name": "AI 고객센터", "score": 85}
  ]
}
```

---

### 3.6 WF-06: Confluence Sync (동기화)

**용도**: DB ↔ Confluence 양방향 동기화

**동기화 대상**:
- Signal → Confluence 페이지
- Scorecard → Confluence 페이지
- Brief → Confluence 페이지
- Activity Log → Confluence 페이지

**실행 방법**:

```bash
# Signal 동기화
curl -X POST https://api.example.com/api/workflows/confluence-sync/signal \
  -d '{"signal_id": "SIG-001"}'

# Brief 동기화
curl -X POST https://api.example.com/api/workflows/confluence-sync/brief \
  -d '{"brief_id": "BR-001"}'

# Confluence → DB 가져오기
curl -X POST https://api.example.com/api/workflows/confluence-sync/import \
  -d '{"page_id": "123456"}'

# 양방향 동기화
curl -X POST https://api.example.com/api/workflows/confluence-sync/bidirectional \
  -d '{"signal_id": "SIG-001"}'
```

---

## 4. 웹 UI 가이드

### 4.1 대시보드

**경로**: `/`

**주요 기능**:
- KPI 요약 카드 (Activity, Signal, Brief, S2/S3)
- 주간 트렌드 차트
- 최근 Activity 목록
- 알림/경고 배너

### 4.2 Inbox (Signal 관리)

**경로**: `/inbox`

**주요 기능**:
- Signal 목록 조회 (필터, 정렬)
- Signal 상세 보기
- Signal 등록/수정
- Triage 실행

**필터 옵션**:
- 상태: NEW, SCORING, SCORED, BRIEFED
- 출처: KT, 그룹사, 대외
- 채널: 데스크리서치, 자사활동, 영업PM, 인바운드, 아웃바운드

### 4.3 Scorecard (평가 관리)

**경로**: `/scorecard`

**주요 기능**:
- Scorecard 목록 조회
- 5차원 평가 상세 보기
- 평가 수정/재평가
- GO/HOLD/NO_GO 판정

### 4.4 Brief (문서 관리)

**경로**: `/brief`

**주요 기능**:
- Brief 목록 조회
- Brief 상세 보기/편집
- 승인 워크플로 (DRAFT → REVIEW → APPROVED)
- Confluence 동기화

### 4.5 Play Dashboard

**경로**: `/plays`

**주요 기능**:
- Play별 현황 (Signal, Brief, Stage)
- Play 생성/수정
- 담당자 할당
- 진행 상태 업데이트

### 4.6 Seminar 등록

**경로**: `/seminar`

**주요 기능**:
- 세미나 정보 입력
- 인사이트 기록
- Activity/Signal 자동 생성

---

## 5. API 사용법

### 5.1 인증

```bash
# 로그인하여 JWT 토큰 발급
curl -X POST https://api.example.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@kt.com", "password": "password"}'

# 응답
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}

# API 요청 시 Authorization 헤더 추가
curl -H "Authorization: Bearer eyJ..." https://api.example.com/api/inbox
```

### 5.2 주요 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/inbox` | Signal 목록 |
| POST | `/api/inbox` | Signal 생성 |
| GET | `/api/inbox/{id}` | Signal 상세 |
| GET | `/api/scorecard` | Scorecard 목록 |
| GET | `/api/scorecard/{id}` | Scorecard 상세 |
| GET | `/api/brief` | Brief 목록 |
| GET | `/api/brief/{id}` | Brief 상세 |
| GET | `/api/plays` | Play 목록 |
| POST | `/api/workflows/inbound-triage` | Triage 실행 |
| GET | `/api/workflows/kpi-digest` | KPI 리포트 |

### 5.3 페이지네이션

```bash
# 기본 페이지네이션
curl "https://api.example.com/api/inbox?page=1&page_size=20"

# 응답
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

### 5.4 에러 처리

```json
// 400 Bad Request
{
  "detail": "Invalid request parameters",
  "errors": [{"field": "email", "message": "Invalid email format"}]
}

// 401 Unauthorized
{
  "detail": "Not authenticated"
}

// 404 Not Found
{
  "detail": "Signal not found"
}

// 422 Validation Error
{
  "detail": [{"loc": ["body", "title"], "msg": "field required"}]
}
```

---

## 6. Claude Code 명령어

### 6.1 사용 가능한 명령어

| 명령어 | 설명 | 용도 |
|--------|------|------|
| `/ax:seminar-add` | 세미나 등록 | 세미나 참석 후 인사이트 기록 |
| `/ax:triage` | 인바운드 분류 | 고객 문의 분류 및 평가 |
| `/ax:brief` | Brief 생성 | Signal → Brief 변환 |
| `/ax:kpi-digest` | KPI 리포트 | 주간/월간 현황 조회 |
| `/ax:wrap-up` | 작업 정리 | 테스트 실행 및 커밋 |

### 6.2 사용 예시

```bash
# Claude Code 실행
claude

# 세미나 등록
> /ax:seminar-add
# → 세미나 URL, 제목, 요약, 인사이트 입력 프롬프트

# 인바운드 Triage
> /ax:triage
# → 회사명, 담당자, 문의 내용 입력 프롬프트

# KPI 현황 확인
> /ax:kpi-digest
# → 주간 KPI 요약 출력

# Brief 생성
> /ax:brief SIG-001
# → Signal ID로 Brief 자동 생성
```

---

## 7. FAQ

### Q1. Signal과 Activity의 차이는?

**Activity**는 BD팀의 모든 활동 기록입니다 (세미나 참석, 미팅, 리서치 등).
**Signal**은 Activity에서 발견된 **사업기회 신호**입니다.

하나의 Activity에서 여러 Signal이 추출될 수 있습니다.

---

### Q2. Scorecard 점수는 어떻게 계산되나요?

5개 차원별 점수(0~100)에 가중치를 적용하여 총점을 계산합니다:

```
총점 = (Market Fit × 0.25) + (Org Synergy × 0.25) +
       (Tech Feasibility × 0.20) + (Urgency × 0.15) +
       (Revenue Potential × 0.15)
```

---

### Q3. Brief 승인 절차는?

1. **DRAFT**: 초안 작성 (자동 생성 또는 수동)
2. **REVIEW**: 검토 요청 (팀 리더에게 알림)
3. **APPROVED**: 승인 완료 → S2(Validation) 진입
4. **REJECTED**: 반려 → 수정 후 재제출

---

### Q4. Confluence 동기화는 언제 실행되나요?

- **자동 동기화**: Brief 승인 시, Stage 변경 시
- **수동 동기화**: `/api/workflows/confluence-sync` API 호출
- **양방향 동기화**: Confluence 페이지 수정 후 DB 반영

---

### Q5. 중복 Signal은 어떻게 처리되나요?

시스템이 자동으로 Jaccard 유사도를 계산합니다:
- **70% 이상**: 중복 경고, 기존 Signal과 병합 권장
- **50~70%**: 유사 Signal 알림
- **50% 미만**: 신규 Signal로 등록

---

### Q6. API 호출 시 인증 오류가 발생합니다

1. JWT 토큰 만료 여부 확인 (기본 60분)
2. Authorization 헤더 형식 확인: `Bearer <token>`
3. 토큰 재발급: `POST /api/auth/login`

---

### Q7. 로컬에서 개발 서버를 실행하려면?

```bash
# 1. 환경 설정
cp .env.example .env
# .env 파일에 필수 환경변수 설정

# 2. 의존성 설치
pip install -e ".[dev]"

# 3. 서버 실행
uvicorn backend.api.main:app --reload --port 8000

# 4. API 문서 확인
# http://localhost:8000/docs
```

---

### Q8. 테스트는 어떻게 실행하나요?

```bash
# 전체 테스트
pytest tests/ -v

# 커버리지 포함
pytest tests/ -v --cov=backend

# 특정 테스트만
pytest tests/unit/test_workflows.py -v
```

---

## 부록

### A. 상태 코드 참조

| 상태 | Signal | Scorecard | Brief | Play |
|------|--------|-----------|-------|------|
| NEW | 신규 등록 | - | - | - |
| SCORING | 평가 중 | - | - | - |
| SCORED | 평가 완료 | 평가 완료 | - | - |
| DRAFT | - | - | 초안 | - |
| REVIEW | - | - | 검토 중 | - |
| APPROVED | - | - | 승인됨 | - |
| G (Green) | - | - | - | 정상 진행 |
| Y (Yellow) | - | - | - | 주의 필요 |
| R (Red) | - | - | - | 위험 |

### B. 단축키 (웹 UI)

| 단축키 | 기능 |
|--------|------|
| `Ctrl/Cmd + K` | 빠른 검색 |
| `Ctrl/Cmd + N` | 새 Signal 등록 |
| `Ctrl/Cmd + S` | 저장 |
| `Esc` | 모달 닫기 |

### C. 관련 문서

- [운영 가이드](./OPERATIONS_GUIDE.md) - 배포, 모니터링, 트러블슈팅
- [CLAUDE.md](../CLAUDE.md) - 프로젝트 개발 문서
- [API 문서](https://ax-discovery-api-staging.onrender.com/docs) - Swagger UI
