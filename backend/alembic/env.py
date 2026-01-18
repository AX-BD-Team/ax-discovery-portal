"""
Alembic Environment Configuration

비동기 PostgreSQL 마이그레이션 환경 설정
"""

import asyncio
import sys
from logging.config import fileConfig

# Windows에서 psycopg async 호환성을 위해 SelectorEventLoop 사용
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from alembic import context  # noqa: E402
from sqlalchemy import pool  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

# Import Base directly (not through __init__ to avoid session initialization)
from backend.database.base import Base  # noqa: E402

# Import all models to ensure they are registered with Base.metadata
# These imports must be after Base is imported
from backend.database.models import (  # noqa: E402, F401
    ActionLog,
    CompetencyQuestion,
    Entity,
    EvalGraderResult,
    EvalOutcome,
    EvalRun,
    EvalSuite,
    EvalTask,
    EvalTranscript,
    EvalTrial,
    OpportunityBrief,
    PlayRecord,
    Scorecard,
    Signal,
    Trace,
    Triple,
    User,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Settings에서 DATABASE_URL 가져오기"""
    from backend.core.config import settings

    raw_url = (
        settings.database_url or "postgresql+psycopg://user:password@localhost:5432/ax_discovery"
    )

    # postgresql:// → postgresql+psycopg:// 변환 (Render 호환성)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    return raw_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Enum 타입 비교
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations in 'online' mode (sync context)"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # Enum 타입 비교
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run migrations in 'online' mode (async)"""
    connectable = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
