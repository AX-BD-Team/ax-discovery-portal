"""
User 모델

JWT 인증을 위한 사용자 테이블 정의
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class UserRole(enum.Enum):
    """사용자 역할"""

    ADMIN = "admin"
    USER = "user"


class User(Base):
    """
    User 테이블

    JWT 인증을 위한 사용자 정보 저장
    회원가입 없이 관리자가 미리 생성
    """

    __tablename__ = "users"

    # Primary Key (UUID)
    user_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # 인증 정보
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # 사용자 정보
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)

    # 상태
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 생성/수정 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # 마지막 로그인 시각
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Indexes
    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_role", "role"),
        Index("idx_user_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User(user_id='{self.user_id}', email='{self.email}', role='{self.role.value}')>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """딕셔너리로 변환"""
        data = {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": (self.last_login_at.isoformat() if self.last_login_at else None),
        }

        if include_sensitive:
            data["hashed_password"] = self.hashed_password

        return data
