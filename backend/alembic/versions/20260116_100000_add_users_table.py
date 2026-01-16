"""Add users table

JWT 인증을 위한 사용자 테이블 생성
- users: 사용자 정보 (email, password, role)

Revision ID: 2a3f9d8e7c01
Revises: 1f0188fcd880
Create Date: 2026-01-16 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a3f9d8e7c01"
down_revision: str | None = "1f0188fcd880"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # UserRole Enum 생성
    user_role_enum = sa.Enum(
        "admin",
        "user",
        name="userrole",
    )

    # users 테이블 생성
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", user_role_enum, nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    # users 인덱스
    op.create_index("idx_user_email", "users", ["email"])
    op.create_index("idx_user_role", "users", ["role"])
    op.create_index("idx_user_is_active", "users", ["is_active"])


def downgrade() -> None:
    # users 인덱스 삭제
    op.drop_index("idx_user_is_active", table_name="users")
    op.drop_index("idx_user_role", table_name="users")
    op.drop_index("idx_user_email", table_name="users")

    # users 테이블 삭제
    op.drop_table("users")

    # Enum 타입 삭제
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
