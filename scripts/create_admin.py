#!/usr/bin/env python3
"""
관리자 계정 생성 스크립트

초기 admin 계정을 생성합니다.

Usage:
    # 기본 admin 계정 생성
    python scripts/create_admin.py

    # 커스텀 정보로 생성
    python scripts/create_admin.py --email admin@ax.com --name "Admin User" --password SecurePass123

환경변수:
    DATABASE_URL: PostgreSQL 연결 URL
"""

import argparse
import asyncio
import getpass
import os
import sys
import uuid

import structlog
from dotenv import load_dotenv
from sqlalchemy import select

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# ruff: noqa: E402
from backend.api.security import get_password_hash
from backend.database.models.user import User, UserRole
from backend.database.session import SessionLocal

# 로거 설정
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True),
    ]
)
logger = structlog.get_logger()


async def create_admin_user(
    email: str,
    name: str,
    password: str,
    force: bool = False,
) -> User | None:
    """
    관리자 계정 생성

    Args:
        email: 이메일
        name: 이름
        password: 비밀번호
        force: 기존 계정이 있어도 업데이트

    Returns:
        생성된 User 또는 None
    """
    async with SessionLocal() as db:
        # 기존 계정 확인
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            if force:
                logger.info("기존 계정 업데이트", email=email)
                existing_user.name = name
                existing_user.hashed_password = get_password_hash(password)
                existing_user.role = UserRole.ADMIN
                existing_user.is_active = True
                await db.commit()
                logger.info("관리자 계정 업데이트 완료", email=email)
                return existing_user
            else:
                logger.warning("이미 존재하는 계정", email=email)
                logger.info("기존 계정을 업데이트하려면 --force 옵션을 사용하세요")
                return None

        # 새 계정 생성
        user = User(
            user_id=str(uuid.uuid4()),
            email=email,
            name=name,
            hashed_password=get_password_hash(password),
            role=UserRole.ADMIN,
            is_active=True,
        )

        db.add(user)
        await db.commit()

        logger.info(
            "관리자 계정 생성 완료",
            user_id=user.user_id,
            email=user.email,
            name=user.name,
        )

        return user


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="관리자 계정을 생성합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python scripts/create_admin.py
  python scripts/create_admin.py --email admin@ax.com --name "Admin"
  python scripts/create_admin.py --force  # 기존 계정 업데이트
        """,
    )

    parser.add_argument(
        "--email",
        "-e",
        default="admin@ax.com",
        help="관리자 이메일 (기본: admin@ax.com)",
    )

    parser.add_argument(
        "--name",
        "-n",
        default="AX Admin",
        help="관리자 이름 (기본: AX Admin)",
    )

    parser.add_argument(
        "--password",
        "-p",
        help="비밀번호 (미지정 시 프롬프트)",
    )

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="기존 계정이 있으면 업데이트",
    )

    args = parser.parse_args()

    # 비밀번호 입력
    password = args.password
    if not password:
        password = getpass.getpass("비밀번호 입력: ")
        password_confirm = getpass.getpass("비밀번호 확인: ")

        if password != password_confirm:
            logger.error("비밀번호가 일치하지 않습니다")
            sys.exit(1)

    if len(password) < 8:
        logger.error("비밀번호는 8자 이상이어야 합니다")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("관리자 계정 생성")
    logger.info("=" * 60)

    try:
        user = await create_admin_user(
            email=args.email,
            name=args.name,
            password=password,
            force=args.force,
        )

        if user:
            logger.info("=" * 60)
            logger.info("계정 정보:")
            logger.info(f"  User ID: {user.user_id}")
            logger.info(f"  Email: {user.email}")
            logger.info(f"  Name: {user.name}")
            logger.info(f"  Role: {user.role.value}")
            logger.info("=" * 60)
        else:
            sys.exit(1)

    except Exception as e:
        logger.error("계정 생성 실패", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
