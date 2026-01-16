# AX Discovery Portal - 운영 가이드

> 배포, 모니터링, 트러블슈팅을 위한 운영 매뉴얼

**버전**: 0.4.0
**최종 업데이트**: 2026-01-16

---

## 목차

1. [환경 구성](#1-환경-구성)
2. [배포](#2-배포)
3. [모니터링](#3-모니터링)
4. [트러블슈팅](#4-트러블슈팅)
5. [백업 및 복구](#5-백업-및-복구)
6. [보안](#6-보안)

---

## 1. 환경 구성

### 1.1 환경 종류

| 환경 | 용도 | URL | 브랜치 |
|------|------|-----|--------|
| Development | 로컬 개발 | http://localhost:8000 | feature/* |
| Staging | 테스트/QA | https://ax-discovery-api-staging.onrender.com | staging, main |
| Production | 운영 | https://ax-discovery-api.onrender.com | main |

### 1.2 필수 환경변수

```bash
# =============================================================================
# 필수 설정
# =============================================================================

# Application
APP_ENV=production          # development | staging | production
DEBUG=false                 # true | false
LOG_LEVEL=INFO              # DEBUG | INFO | WARNING | ERROR

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# Security (프로덕션 필수)
JWT_SECRET_KEY=<strong-random-secret>  # 최소 32자 이상 권장

# =============================================================================
# 외부 서비스 연동
# =============================================================================

# Anthropic API (에이전트 실행용)
ANTHROPIC_API_KEY=sk-ant-xxx

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Confluence (System-of-Record)
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_API_TOKEN=your-api-token
CONFLUENCE_USER_EMAIL=your-email@example.com
CONFLUENCE_SPACE_KEY=AXBD

# =============================================================================
# 선택 설정
# =============================================================================

# Cloudflare (Vector Search)
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_API_TOKEN=your-api-token
D1_DATABASE_ID=your-database-id

# OpenAI (임베딩)
OPENAI_API_KEY=sk-xxx
EMBEDDING_MODEL=text-embedding-3-small

# Sentry (에러 모니터링)
SENTRY_DSN=https://xxx@sentry.io/xxx

# Teams/Slack (알림)
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx

# CORS
CORS_ORIGINS=https://ax-discovery-portal.pages.dev,https://your-domain.com
```

### 1.3 환경별 설정 파일

```
.env                    # 기본 설정 (git 제외)
.env.development        # 개발 환경 템플릿
.env.staging            # 스테이징 환경 템플릿
.env.production         # 프로덕션 환경 템플릿
.env.example            # 설정 예시 (git 포함)
```

---

## 2. 배포

### 2.1 배포 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                         │
│                         (main branch)                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (CI/CD)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ ci-backend   │  │ cd-backend   │  │ frontend     │          │
│  │ (lint/test)  │  │ (deploy)     │  │ (build/deploy)│         │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Render     │  │  Cloudflare  │  │  Cloudflare  │
│  (Backend)   │  │   Pages      │  │  D1/Vectorize│
│              │  │  (Frontend)  │  │  (Database)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 2.2 배포 방법

#### 자동 배포 (권장)

```bash
# 1. feature 브랜치에서 작업
git checkout -b feature/my-feature

# 2. 변경사항 커밋
git add .
git commit -m "feat: 새 기능 추가"

# 3. main 브랜치로 PR 생성 및 머지
gh pr create --base main --title "feat: 새 기능 추가"

# 4. PR 머지 시 자동 배포
#    - CI: lint + test 실행
#    - CD: Staging → Production 순차 배포
```

#### 수동 배포 (긴급 시)

```bash
# Render Deploy Hook 직접 호출
curl -X POST "$RENDER_STAGING_DEPLOY_HOOK"
curl -X POST "$RENDER_PRODUCTION_DEPLOY_HOOK"
```

### 2.3 배포 워크플로 (cd-backend.yml)

```yaml
# 트리거 조건
on:
  push:
    branches: [main, staging]
    paths:
      - 'backend/**'
      - 'pyproject.toml'
      - 'render.yaml'

# 배포 순서
jobs:
  deploy-staging:    # 1. Staging 배포
    environment: staging

  deploy-production: # 2. Production 배포 (main 브랜치만)
    needs: deploy-staging
    environment: production
    if: github.ref == 'refs/heads/main'
```

### 2.4 롤백

```bash
# 1. 이전 커밋으로 되돌리기
git revert HEAD
git push origin main

# 2. Render 대시보드에서 이전 배포로 롤백
#    Render Dashboard → Service → Deploys → Rollback

# 3. 긴급 시 서비스 일시 중지
#    Render Dashboard → Service → Settings → Suspend Service
```

### 2.5 데이터베이스 마이그레이션

```bash
# 마이그레이션 상태 확인
alembic current

# 새 마이그레이션 생성
alembic revision --autogenerate -m "설명"

# 마이그레이션 적용
alembic upgrade head

# 롤백 (한 단계)
alembic downgrade -1

# 특정 버전으로 롤백
alembic downgrade <revision_id>
```

---

## 3. 모니터링

### 3.1 헬스체크 엔드포인트

| 엔드포인트 | 용도 | 예상 응답 |
|------------|------|-----------|
| `/health` | Liveness Probe | `{"status": "healthy"}` |
| `/ready` | Readiness Probe | `{"status": "ready", "components": {...}}` |
| `/` | 기본 상태 | `{"status": "ok"}` |

```bash
# 헬스체크 확인
curl https://ax-discovery-api-staging.onrender.com/health
curl https://ax-discovery-api-staging.onrender.com/ready

# 응답 예시
{
  "status": "ready",
  "version": "0.4.0",
  "environment": "staging",
  "components": {
    "database": "ok",           # PostgreSQL 연결 상태
    "agent_runtime": "ok",      # Agent SDK 상태
    "confluence": "configured"  # Confluence 설정 상태
  }
}
```

### 3.2 로그 확인

#### Render 대시보드

```
Render Dashboard → Service → Logs
```

#### 로그 포맷

```json
// 프로덕션 (JSON 포맷)
{
  "timestamp": "2026-01-16T12:00:00.000000Z",
  "level": "info",
  "logger": "backend.api.main",
  "message": "Request completed",
  "path": "/api/inbox",
  "method": "GET",
  "status_code": 200,
  "duration_ms": 45
}

// 개발환경 (컬러 콘솔)
2026-01-16T12:00:00.000000Z [info] Request completed path=/api/inbox status=200
```

### 3.3 Sentry 에러 모니터링

```bash
# 환경변수 설정
SENTRY_DSN=https://xxx@sentry.io/xxx

# Sentry 대시보드에서 확인 가능한 항목:
# - 에러 발생 빈도 및 추이
# - 에러 스택트레이스
# - 영향받은 사용자 수
# - 성능 메트릭 (트랜잭션 시간)
```

### 3.4 부하 테스트

```bash
# 의존성 설치
pip install ".[loadtest]"

# 테스트 시나리오 실행
./tests/loadtest/run_loadtest.sh quick     # 스모크 테스트 (30초)
./tests/loadtest/run_loadtest.sh standard  # 표준 테스트 (60초)
./tests/loadtest/run_loadtest.sh stress    # 스트레스 테스트 (5분)
./tests/loadtest/run_loadtest.sh ui        # 웹 UI 모드

# 환경변수로 대상 서버 지정
HOST=https://ax-discovery-api-staging.onrender.com ./tests/loadtest/run_loadtest.sh quick
```

### 3.5 메트릭 대시보드

| 메트릭 | 정상 범위 | 경고 임계값 |
|--------|----------|-------------|
| 응답 시간 (p95) | < 500ms | > 1000ms |
| 에러율 | < 1% | > 5% |
| CPU 사용률 | < 70% | > 90% |
| 메모리 사용률 | < 80% | > 95% |

---

## 4. 트러블슈팅

### 4.1 일반적인 문제

#### 서비스 시작 실패

```bash
# 증상: 서비스가 시작되지 않음
# 원인: 환경변수 누락 또는 잘못된 값

# 해결:
1. Render 대시보드에서 환경변수 확인
2. 필수 환경변수 설정 여부 확인:
   - ANTHROPIC_API_KEY
   - JWT_SECRET_KEY (프로덕션)
3. 로그에서 에러 메시지 확인
```

#### 데이터베이스 연결 실패

```bash
# 증상: /ready 응답에서 database: "error"
# 원인: DATABASE_URL 미설정 또는 잘못된 연결 문자열

# 해결:
1. DATABASE_URL 형식 확인:
   postgresql+asyncpg://user:password@host:5432/dbname

2. 네트워크 연결 확인 (Render → PostgreSQL)

3. 데이터베이스 서버 상태 확인
```

#### Confluence 연동 실패

```bash
# 증상: Confluence 관련 API 500 에러
# 원인: API 토큰 만료 또는 권한 부족

# 해결:
1. CONFLUENCE_API_TOKEN 유효성 확인
2. CONFLUENCE_USER_EMAIL 확인
3. Confluence Space 접근 권한 확인
4. API 토큰 재발급:
   https://id.atlassian.com/manage-profile/security/api-tokens
```

#### Agent Runtime 오류

```bash
# 증상: 워크플로 실행 시 500 에러
# 원인: ANTHROPIC_API_KEY 오류 또는 Rate Limit

# 해결:
1. ANTHROPIC_API_KEY 유효성 확인
2. Anthropic 대시보드에서 사용량/할당량 확인
3. Rate Limit 시 재시도 로직 확인
```

### 4.2 성능 문제

#### 느린 응답 시간

```bash
# 진단:
1. /ready 엔드포인트로 컴포넌트별 상태 확인
2. 로그에서 slow query 확인
3. Sentry 성능 탭에서 병목 지점 확인

# 해결:
1. 데이터베이스 인덱스 확인
2. N+1 쿼리 패턴 수정
3. 캐싱 적용 고려
```

#### 메모리 부족

```bash
# 증상: OOM (Out of Memory) 에러
# 원인: 대용량 데이터 처리 또는 메모리 누수

# 해결:
1. Render Plan 업그레이드 고려
2. 배치 처리로 변경 (페이지네이션)
3. 메모리 프로파일링 실행
```

### 4.3 에러 코드 참조

| HTTP 코드 | 의미 | 일반적인 원인 |
|-----------|------|---------------|
| 400 | Bad Request | 잘못된 요청 파라미터 |
| 401 | Unauthorized | JWT 토큰 만료/누락 |
| 403 | Forbidden | 권한 부족 |
| 404 | Not Found | 존재하지 않는 리소스 |
| 422 | Validation Error | Pydantic 검증 실패 |
| 429 | Too Many Requests | Rate Limit 초과 |
| 500 | Internal Server Error | 서버 내부 오류 |
| 502 | Bad Gateway | 업스트림 서버 오류 |
| 503 | Service Unavailable | 서비스 일시 중단 |

---

## 5. 백업 및 복구

### 5.1 데이터베이스 백업

```bash
# PostgreSQL 백업 (pg_dump)
pg_dump -h host -U user -d dbname > backup_$(date +%Y%m%d).sql

# Cloudflare D1 백업
wrangler d1 export ax-discovery-db --output=backup_$(date +%Y%m%d).sql
```

### 5.2 복구 절차

```bash
# PostgreSQL 복구
psql -h host -U user -d dbname < backup_20260116.sql

# Cloudflare D1 복구
wrangler d1 execute ax-discovery-db --file=backup_20260116.sql
```

### 5.3 백업 주기

| 대상 | 주기 | 보관 기간 |
|------|------|-----------|
| PostgreSQL | 매일 | 30일 |
| D1 Database | 매일 | 30일 |
| Confluence (SoR) | 자동 (Atlassian) | 무제한 |

---

## 6. 보안

### 6.1 인증 및 권한

```bash
# JWT 토큰 발급
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password"
}

# API 요청 시 Authorization 헤더 포함
curl -H "Authorization: Bearer <token>" https://api.example.com/api/inbox
```

### 6.2 시크릿 관리

```bash
# 민감한 환경변수는 Render Dashboard에서 직접 설정
# render.yaml에 sync: false 설정

envVars:
  - key: ANTHROPIC_API_KEY
    sync: false  # Dashboard에서만 설정
  - key: JWT_SECRET_KEY
    sync: false
```

### 6.3 보안 체크리스트

- [ ] JWT_SECRET_KEY: 최소 32자 이상의 랜덤 문자열
- [ ] DEBUG=false: 프로덕션에서 반드시 false
- [ ] CORS_ORIGINS: 허용된 도메인만 명시
- [ ] HTTPS 강제: Render에서 자동 적용
- [ ] API 키 노출 방지: 로그에 민감 정보 마스킹
- [ ] Rate Limiting: 필요 시 적용 고려

### 6.4 민감 데이터 필터링

```python
# Sentry로 전송 전 자동 필터링
# backend/core/logging.py

def _filter_sensitive_data(event, hint):
    # Authorization 헤더 필터링
    # JWT 토큰 필터링 (eyJ로 시작)
    # API 키 필터링 (sk-, sk_)
    return event
```

---

## 부록

### A. 유용한 명령어

```bash
# 로컬 서버 실행
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

# 테스트 실행
pytest tests/ -v --cov=backend

# 린트 검사
ruff check backend/

# 타입 검사
mypy backend/

# 마이그레이션 생성
alembic revision --autogenerate -m "설명"

# 마이그레이션 적용
alembic upgrade head
```

### B. 연락처

| 역할 | 담당 | 연락처 |
|------|------|--------|
| 기술 리드 | AX BD Team | ax-bd@kt.com |
| 인프라 | DevOps Team | - |
| 보안 | Security Team | - |

### C. 관련 문서

- [CLAUDE.md](../CLAUDE.md) - 프로젝트 개발 문서
- [README.md](../README.md) - 프로젝트 개요
- [project-todo.md](../project-todo.md) - 작업 추적
- [changelog.md](../changelog.md) - 변경 이력
