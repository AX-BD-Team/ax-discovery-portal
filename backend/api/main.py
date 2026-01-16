"""
AX Discovery Portal - Backend API

FastAPI 기반 백엔드 서버
"""

from contextlib import asynccontextmanager

# .env 파일 로드
from dotenv import load_dotenv

load_dotenv()

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    brief,
    inbox,
    ontology,
    play_dashboard,
    scorecard,
    search,
    stream,
    workflows,
    xai,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 처리"""
    logger.info("Starting AX Discovery Portal API...")

    # Agent Runtime 초기화
    from backend.agent_runtime.runner import runtime

    await runtime.initialize()

    yield

    # 종료 시 정리
    logger.info("Shutting down AX Discovery Portal API...")


app = FastAPI(
    title="AX Discovery Portal API",
    description="AX BD팀 멀티에이전트 기반 사업기회 포착 엔진",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS 설정
# Development: localhost 허용, Production: Cloudflare Pages 도메인 허용
CORS_ORIGINS = [
    # Development
    "http://localhost:3000",  # Next.js web
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:5173",  # Vite dev server (legacy)
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
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
app.include_router(inbox.router, prefix="/api/inbox", tags=["inbox"])
app.include_router(scorecard.router, prefix="/api/scorecard", tags=["scorecard"])
app.include_router(brief.router, prefix="/api/brief", tags=["brief"])
app.include_router(play_dashboard.router, prefix="/api/plays", tags=["plays"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(stream.router, tags=["stream"])
# Ontology & XAI
app.include_router(ontology.router, prefix="/api", tags=["ontology"])
app.include_router(xai.router, prefix="/api", tags=["xai"])
# Vector Search
app.include_router(search.router, prefix="/api/search", tags=["search"])


@app.get("/")
async def root():
    """헬스체크"""
    return {"status": "ok", "service": "ax-discovery-portal"}


@app.get("/health")
@app.head("/health")
async def health():
    """상세 헬스체크"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "components": {"database": "ok", "agent_runtime": "ok", "confluence": "ok"},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
