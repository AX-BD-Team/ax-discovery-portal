"""
FastAPI Dependencies

의존성 주입 함수들
"""

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.security import decode_access_token
from backend.database.models.user import User, UserRole


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

    # Sentry (monitoring)
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤"""
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


# OAuth2 설정 (Bearer 토큰)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


async def get_db_for_auth() -> AsyncGenerator[AsyncSession, None]:
    """인증용 데이터베이스 세션 (순환 import 방지)"""
    from backend.database.session import SessionLocal

    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_for_auth)],
) -> User:
    """
    현재 사용자 조회 (JWT 인증)

    Args:
        token: Bearer 토큰
        db: 데이터베이스 세션

    Returns:
        인증된 User 객체

    Raises:
        HTTPException: 인증 실패 시 401
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    # JWT 토큰 디코딩
    token_data = decode_access_token(token)
    if not token_data:
        raise credentials_exception

    # DB에서 사용자 조회
    result = await db.execute(select(User).where(User.user_id == token_data.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다",
        )

    return user


async def get_current_user_optional(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_for_auth)],
) -> User | None:
    """
    현재 사용자 조회 (선택적 인증)

    토큰이 없거나 유효하지 않으면 None 반환
    """
    if not token:
        return None

    token_data = decode_access_token(token)
    if not token_data:
        return None

    result = await db.execute(select(User).where(User.user_id == token_data.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        return None

    return user


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    관리자 사용자 조회

    현재 사용자가 admin 역할인지 확인

    Raises:
        HTTPException: admin이 아닌 경우 403
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다",
        )
    return current_user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
CurrentUserOptionalDep = Annotated[User | None, Depends(get_current_user_optional)]
AdminUserDep = Annotated[User, Depends(get_admin_user)]


async def verify_api_key(settings: SettingsDep) -> bool:
    """API 키 검증"""
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Anthropic API key not configured",
        )
    return True


async def verify_confluence_config(settings: SettingsDep) -> bool:
    """Confluence 설정 검증"""
    if not all(
        [
            settings.confluence_base_url,
            settings.confluence_api_token,
            settings.confluence_user_email,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Confluence credentials not configured",
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
