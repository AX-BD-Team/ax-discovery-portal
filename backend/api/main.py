"""
AX Discovery Portal - Backend API

FastAPI 기반 백엔드 서버
"""

from contextlib import asynccontextmanager

# .env 파일 로드
from dotenv import load_dotenv

load_dotenv()

# Sentry 초기화 (가능한 빨리 로드)
from backend.core.config import settings

if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        release=f"ax-discovery-portal@{settings.app_version}",
        environment=settings.app_env,
        # 성능 모니터링 (개발 환경에서는 100% 수집, 프로덕션에서는 설정값 사용)
        traces_sample_rate=1.0 if settings.is_development else settings.sentry_traces_sample_rate,
        # 프로파일링 (개발 환경에서는 비활성화, 프로덕션에서는 설정값 사용)
        profiles_sample_rate=0.0
        if settings.is_development
        else settings.sentry_profiles_sample_rate,
        # 통합
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        # 개발 환경에서는 디버그 모드
        debug=settings.is_development,
        # 민감 정보 필터링
        send_default_pii=False,
        # 추가 컨텍스트
        _experiments={
            "continuous_profiling_auto_start": True,
        },
    )

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    activities,
    auth,
    brief,
    evals,
    inbox,
    ontology,
    play_dashboard,
    scorecard,
    search,
    stages,
    stream,
    tasks,
    templates,
    webhooks,
    workflows,
    xai,
)

logger = structlog.get_logger()

# ============================================================
# OpenAPI 메타데이터
# ============================================================

API_VERSION = "0.4.0"

# 태그 설명 (Swagger UI에서 그룹화)
TAGS_METADATA = [
    {
        "name": "auth",
        "description": "JWT 기반 사용자 인증 및 권한 관리",
    },
    {
        "name": "inbox",
        "description": "Signal 관리 - 사업기회 신호 등록, 조회, Triage",
    },
    {
        "name": "activities",
        "description": "Activity 관리 - 외부 세미나/이벤트 수집 결과 조회",
    },
    {
        "name": "scorecard",
        "description": "Scorecard 관리 - Signal 5차원 평가 (100점 만점)",
    },
    {
        "name": "brief",
        "description": "Brief 관리 - 1-Page Brief 생성 및 승인 워크플로",
    },
    {
        "name": "plays",
        "description": "Play Dashboard - Play별 Signal/Brief 현황 조회",
    },
    {
        "name": "tasks",
        "description": "Task 관리 - Play의 ToDoList, 작업 진행 추적",
    },
    {
        "name": "stages",
        "description": "Stage Pipeline - Opportunity 단계 관리, HITL 승인, 퍼널 분석",
    },
    {
        "name": "workflows",
        "description": "워크플로 실행 - WF-01~07 파이프라인 (세미나, 인터뷰, VoC, Triage, KPI, Confluence, External Scout)",
    },
    {
        "name": "webhooks",
        "description": "웹훅 수신 - RSS/Festa/Eventbrite 실시간 이벤트 수신",
    },
    {
        "name": "stream",
        "description": "SSE 스트리밍 - AG-UI 실시간 이벤트 구독",
    },
    {
        "name": "ontology",
        "description": "Knowledge Graph - Entity/Triple 기반 온톨로지 관리",
    },
    {
        "name": "xai",
        "description": "Explainable AI - 의사결정 근거 및 추론 경로 조회",
    },
    {
        "name": "search",
        "description": "시맨틱 검색 - Vector RAG 기반 유사도 검색",
    },
    {
        "name": "evals",
        "description": "AI 평가 플랫폼 - Suite/Run/Trial 관리 및 통계 분석",
    },
    {
        "name": "templates",
        "description": "Boilerplate 템플릿 - Claude Agent SDK 프로젝트 템플릿 다운로드",
    },
]

# API 설명 (Markdown 지원)
API_DESCRIPTION = """
# AX Discovery Portal API

**AX BD팀 멀티에이전트 기반 사업기회 포착 엔진**

## 🎯 핵심 기능

- **Signal 수집**: 3원천(KT/그룹사/대외) × 5채널에서 사업기회 신호 포착
- **Scorecard 평가**: 5차원 100점 평가로 GO/PIVOT/HOLD/NO_GO 판정
- **Brief 생성**: 1-Page Brief 자동 생성 및 승인 워크플로
- **워크플로 자동화**: WF-01~06 파이프라인으로 전체 흐름 자동화

## 📊 워크플로

| ID | 이름 | 설명 |
|---|---|---|
| WF-01 | Seminar Pipeline | 세미나 URL → Activity → Signal |
| WF-02 | Interview-to-Brief | 인터뷰 노트 → Signal → Scorecard → Brief |
| WF-03 | VoC Mining | VoC 데이터 → 테마 추출 → Signal |
| WF-04 | Inbound Triage | 인바운드 요청 → 중복체크 → Play 라우팅 |
| WF-05 | KPI Digest | 주간/월간 KPI 리포트 생성 |
| WF-06 | Confluence Sync | DB ↔ Confluence 양방향 동기화 |

## 🔐 인증

JWT 토큰 기반 인증을 사용합니다. `/api/auth/login`에서 토큰을 발급받아
`Authorization: Bearer <token>` 헤더에 포함하세요.

## 📚 추가 문서

- [GitHub Repository](https://github.com/anthropics/ax-discovery-portal)
- [Confluence Space](https://your-confluence.atlassian.net/wiki/spaces/AX)
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 처리"""
    logger.info("Starting AX Discovery Portal API...")

    # Sentry 상태 로깅
    if settings.sentry_dsn:
        import sentry_sdk

        logger.info(
            "Sentry initialized",
            release=f"ax-discovery-portal@{settings.app_version}",
            environment=settings.app_env,
        )
        # 시작 이벤트 전송
        sentry_sdk.capture_message(
            f"AX Discovery Portal API started (v{settings.app_version})",
            level="info",
        )
    else:
        logger.info("Sentry disabled (SENTRY_DSN not configured)")

    # Agent Runtime 초기화
    from backend.agent_runtime.runner import runtime

    await runtime.initialize()

    yield

    # 종료 시 정리
    logger.info("Shutting down AX Discovery Portal API...")
    if settings.sentry_dsn:
        import sentry_sdk

        # Sentry 버퍼 플러시
        sentry_sdk.flush(timeout=2.0)


app = FastAPI(
    title="AX Discovery Portal API",
    description=API_DESCRIPTION,
    version=API_VERSION,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    # OpenAPI 문서 경로
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    # 추가 메타데이터
    contact={
        "name": "AX BD Team",
        "email": "ax-bd@kt.com",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://kt.com",
    },
    servers=[
        {"url": "http://localhost:8000", "description": "Local Development"},
        {"url": "https://ax-discovery-portal.onrender.com", "description": "Production (Render)"},
    ],
)

# CORS 설정
# Development: localhost 허용, Production: Cloudflare Pages 도메인 허용
CORS_ORIGINS = [
    # Development
    "http://localhost:3000",  # Next.js web
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3100",  # Next.js web (alternate port)
    "http://localhost:4000",  # Next.js web (alternate port)
    "http://localhost:5173",  # Vite dev server (legacy)
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:3100",
    "http://127.0.0.1:4000",
    "http://127.0.0.1:5173",
    # Production - Cloudflare Pages
    "https://ax-discovery-portal.pages.dev",
    "https://ax-discovery-portal-preview.pages.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
# Auth (JWT 인증)
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(inbox.router, prefix="/api/inbox", tags=["inbox"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
app.include_router(scorecard.router, prefix="/api/scorecard", tags=["scorecard"])
app.include_router(brief.router, prefix="/api/brief", tags=["brief"])
app.include_router(play_dashboard.router, prefix="/api/plays", tags=["plays"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(stages.router, prefix="/api/stages", tags=["stages"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(stream.router, tags=["stream"])
# Ontology & XAI
app.include_router(ontology.router, prefix="/api", tags=["ontology"])
app.include_router(xai.router, prefix="/api", tags=["xai"])
# Vector Search
app.include_router(search.router, prefix="/api/search", tags=["search"])
# Evals Platform
app.include_router(evals.router, prefix="/api/evals", tags=["evals"])
# Templates
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])


@app.get("/")
async def root():
    """헬스체크"""
    return {"status": "ok", "service": "ax-discovery-portal"}


@app.get("/health")
@app.head("/health")
async def health():
    """
    상세 헬스체크

    Kubernetes liveness probe용 엔드포인트.
    애플리케이션이 살아있는지 확인합니다.
    """
    components: dict[str, str] = {"api": "ok"}

    # Sentry 상태 체크
    if settings.sentry_configured:
        components["sentry"] = "enabled"
    else:
        components["sentry"] = "disabled"

    return {
        "status": "healthy",
        "version": API_VERSION,
        "environment": settings.app_env,
        "components": components,
    }


@app.get("/ready")
@app.head("/ready")
async def ready():
    """
    준비 상태 체크

    Kubernetes readiness probe용 엔드포인트.
    모든 의존성이 준비되었는지 확인합니다.
    """
    from backend.core.config import settings

    components: dict[str, str] = {}
    all_ready = True

    # 1. 데이터베이스 연결 체크
    try:
        if settings.database_url:
            from sqlalchemy import text

            from backend.database.session import engine

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            components["database"] = "ok"
        else:
            components["database"] = "not_configured"
    except Exception as e:
        components["database"] = f"error: {str(e)[:50]}"
        all_ready = False

    # 2. Agent Runtime 체크
    try:
        from backend.agent_runtime.runner import runtime

        # AgentRuntime이 로드되었는지 확인
        if runtime.agents:
            components["agent_runtime"] = "ok"
        else:
            components["agent_runtime"] = "no_agents"
    except Exception as e:
        components["agent_runtime"] = f"error: {str(e)[:50]}"
        all_ready = False

    # 3. Confluence 연결 체크 (설정된 경우에만)
    if settings.confluence_configured:
        components["confluence"] = "configured"
    else:
        components["confluence"] = "not_configured"

    # 4. Sentry 상태 체크
    if settings.sentry_configured:
        components["sentry"] = "enabled"
    else:
        components["sentry"] = "disabled"

    # 5. 전체 상태 결정
    status = "ready" if all_ready else "degraded"

    return {
        "status": status,
        "version": API_VERSION,
        "environment": settings.app_env,
        "components": components,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
