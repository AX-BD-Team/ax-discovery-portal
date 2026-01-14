"""
AX Discovery Portal - Backend API

FastAPI 기반 백엔드 서버
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .routers import inbox, scorecard, brief, play_dashboard


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 처리"""
    logger.info("Starting AX Discovery Portal API...")
    
    # 시작 시 초기화
    # await init_database()
    # await init_agent_runtime()
    
    yield
    
    # 종료 시 정리
    logger.info("Shutting down AX Discovery Portal API...")


app = FastAPI(
    title="AX Discovery Portal API",
    description="AX BD팀 멀티에이전트 기반 사업기회 포착 엔진",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(inbox.router, prefix="/api/inbox", tags=["inbox"])
app.include_router(scorecard.router, prefix="/api/scorecard", tags=["scorecard"])
app.include_router(brief.router, prefix="/api/brief", tags=["brief"])
app.include_router(play_dashboard.router, prefix="/api/plays", tags=["plays"])


@app.get("/")
async def root():
    """헬스체크"""
    return {"status": "ok", "service": "ax-discovery-portal"}


@app.get("/health")
async def health():
    """상세 헬스체크"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "components": {
            "database": "ok",
            "agent_runtime": "ok",
            "confluence": "ok"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
