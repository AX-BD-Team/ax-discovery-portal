"""
FastAPI Dependencies

의존성 주입 함수들
"""

from typing import Annotated, AsyncGenerator
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production"
    
    # Anthropic
    anthropic_api_key: str = ""
    agent_model: str = "claude-sonnet-4-20250514"
    
    # Confluence
    confluence_base_url: str = ""
    confluence_api_token: str = ""
    confluence_user_email: str = ""
    confluence_space_key: str = "AXBD"
    
    # Database
    database_url: str = ""
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Agent
    agent_session_timeout: int = 3600
    agent_max_iterations: int = 100
    agent_approval_timeout: int = 86400
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤"""
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    # TODO: 인증 구현
    # authorization: str = Header(None)
) -> dict:
    """현재 사용자 조회 (인증)"""
    # TODO: JWT/OAuth 인증 구현
    return {
        "user_id": "dev_user",
        "email": "dev@example.com",
        "name": "Developer",
        "roles": ["admin"]
    }


CurrentUserDep = Annotated[dict, Depends(get_current_user)]


async def verify_api_key(
    settings: SettingsDep
) -> bool:
    """API 키 검증"""
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Anthropic API key not configured"
        )
    return True


async def verify_confluence_config(
    settings: SettingsDep
) -> bool:
    """Confluence 설정 검증"""
    if not all([
        settings.confluence_base_url,
        settings.confluence_api_token,
        settings.confluence_user_email
    ]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Confluence credentials not configured"
        )
    return True


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    데이터베이스 세션 의존성

    Usage:
        @router.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    from backend.database.session import SessionLocal

    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
