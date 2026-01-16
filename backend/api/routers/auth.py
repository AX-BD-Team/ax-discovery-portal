"""
Auth Router

JWT 인증 관련 API 엔드포인트
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import CurrentUserDep, get_db
from backend.api.security import create_access_token, verify_password
from backend.database.models.user import User

router = APIRouter()


# ==================== Request/Response Models ====================


class LoginRequest(BaseModel):
    """로그인 요청 (JSON 바디용)"""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """토큰 응답"""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """사용자 정보 응답"""

    user_id: str
    email: str
    name: str
    role: str
    is_active: bool
    last_login_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MeResponse(BaseModel):
    """현재 사용자 정보 응답"""

    user: UserResponse


# ==================== Helper Functions ====================


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """
    사용자 인증

    Args:
        db: 데이터베이스 세션
        email: 이메일
        password: 비밀번호

    Returns:
        인증된 User 또는 None
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


async def update_last_login(db: AsyncSession, user: User) -> None:
    """마지막 로그인 시각 업데이트"""
    user.last_login_at = datetime.now(UTC)
    await db.commit()


# ==================== API Endpoints ====================


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    로그인 (JSON 바디)

    이메일과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.

    - **email**: 사용자 이메일
    - **password**: 비밀번호
    """
    user = await authenticate_user(db, request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 토큰 생성
    access_token = create_access_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role.value,
    )

    # 마지막 로그인 시각 업데이트
    await update_last_login(db, user)

    return TokenResponse(access_token=access_token)


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    로그인 (OAuth2 Form)

    OAuth2 표준 form-data 형식으로 로그인합니다.
    Swagger UI 인증에 사용됩니다.

    - **username**: 이메일
    - **password**: 비밀번호
    """
    user = await authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 토큰 생성
    access_token = create_access_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role.value,
    )

    # 마지막 로그인 시각 업데이트
    await update_last_login(db, user)

    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=MeResponse)
async def get_current_user_info(
    current_user: CurrentUserDep,
):
    """
    현재 사용자 정보 조회

    JWT 토큰에서 추출한 현재 로그인한 사용자 정보를 반환합니다.
    """
    return MeResponse(
        user=UserResponse(
            user_id=current_user.user_id,
            email=current_user.email,
            name=current_user.name,
            role=current_user.role.value,
            is_active=current_user.is_active,
            last_login_at=(
                current_user.last_login_at.isoformat() if current_user.last_login_at else None
            ),
        )
    )
