"""
Security 유틸리티

JWT 토큰 생성/검증, 비밀번호 해싱 등 보안 관련 유틸리티
"""

import os
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

# JWT 설정
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-jwt-secret")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


class TokenPayload(BaseModel):
    """JWT 토큰 페이로드"""

    sub: str  # user_id
    email: str
    role: str
    exp: datetime


class TokenData(BaseModel):
    """JWT 토큰 디코딩 결과"""

    user_id: str
    email: str
    role: str


# ==================== 비밀번호 ====================


def get_password_hash(password: str) -> str:
    """
    비밀번호 해싱

    Args:
        password: 평문 비밀번호

    Returns:
        bcrypt 해시된 비밀번호
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증

    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해시된 비밀번호

    Returns:
        일치 여부
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ==================== JWT ====================


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    JWT Access Token 생성

    Args:
        user_id: 사용자 ID
        email: 이메일
        role: 역할 (admin, user)
        expires_delta: 만료 시간 (기본: 60분)

    Returns:
        JWT 토큰 문자열
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenData | None:
    """
    JWT Access Token 디코딩 및 검증

    Args:
        token: JWT 토큰 문자열

    Returns:
        TokenData 또는 None (검증 실패 시)
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        user_id: str | None = payload.get("sub")
        email: str | None = payload.get("email")
        role: str | None = payload.get("role")

        if user_id is None or email is None or role is None:
            return None

        return TokenData(user_id=user_id, email=email, role=role)

    except JWTError:
        return None
