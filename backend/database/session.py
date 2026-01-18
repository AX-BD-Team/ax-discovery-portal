"""
비동기 데이터베이스 세션 관리
"""

import os
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = structlog.get_logger()

# 환경변수에서 데이터베이스 URL 가져오기
_raw_url = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/ax_discovery"
)

# postgresql:// → postgresql+asyncpg:// 변환 (async 호환성)
# asyncpg 드라이버 사용 (psycopg3 async c-extension 문제 회피)
if _raw_url.startswith("postgresql://"):
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgres://"):
    DATABASE_URL = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql+psycopg://"):
    DATABASE_URL = _raw_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = _raw_url

# 비동기 엔진 생성
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # 개발 환경에서 SQL 로그 출력
    pool_pre_ping=True,  # 연결 상태 체크
    pool_size=5,
    max_overflow=10,
)

# 비동기 세션 팩토리
SessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 의존성으로 사용할 데이터베이스 세션 생성기

    Usage:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
