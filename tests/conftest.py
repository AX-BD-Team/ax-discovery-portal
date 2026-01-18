"""
pytest 공용 fixtures

모든 테스트에서 사용할 수 있는 공통 fixture 정의
"""

# ============================================================
# structlog 테스트 환경 설정 (다른 모든 import 전에 실행)
# ============================================================
import logging
import sys

import structlog

# structlog 테스트 환경 즉시 설정 (모듈 import 시점에 실행)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(colors=False),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=False,  # 테스트 환경에서는 캐시 비활성화
)

# 기본 로깅 설정
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.WARNING,  # 테스트 시 로그 최소화
    force=True,  # 기존 핸들러 재설정
)

# ============================================================
# 일반 import
# ============================================================
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.database.base import Base
from tests.fixtures.sample_markdown import get_agent_markdown

# ============================================================
# 테스트 격리 fixture
# ============================================================


@pytest.fixture(autouse=True)
def reset_structlog_for_each_test():
    """각 테스트 전후 structlog 상태 초기화"""
    # 테스트 전: structlog 재설정
    structlog.reset_defaults()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    yield  # 테스트 실행

    # 테스트 후: 컨텍스트 변수 정리
    structlog.contextvars.clear_contextvars()


@pytest.fixture
def mock_env(monkeypatch):
    """환경변수 Mock"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
    monkeypatch.setenv("AGENT_MODEL", "claude-sonnet-4-20250514")
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://test.atlassian.net")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "test-token")
    monkeypatch.setenv("CONFLUENCE_USER_EMAIL", "test@example.com")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "TEST")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_ax_discovery"
    )
    return monkeypatch


@pytest.fixture
def sample_agent_markdown(tmp_path: Path) -> Path:
    """샘플 에이전트 Markdown 파일 생성 (6개)"""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)

    agent_names = [
        "orchestrator",
        "external_scout",
        "scorecard_evaluator",
        "brief_writer",
        "confluence_sync",
        "governance",
    ]

    for agent_name in agent_names:
        agent_file = agents_dir / f"{agent_name}.md"
        agent_file.write_text(get_agent_markdown(agent_name), encoding="utf-8")

    return agents_dir


@pytest.fixture
def mock_teams_mcp():
    """TeamsMCP Mock"""
    mock = AsyncMock()

    # send_message
    mock.send_message.return_value = {
        "status": "sent",
        "channel": "Test-Channel",
        "timestamp": "2026-01-16T12:00:00",
    }

    # send_notification
    mock.send_notification.return_value = {
        "status": "sent",
        "level": "info",
        "channel": "Test-Channel",
        "timestamp": "2026-01-16T12:00:00",
    }

    # send_card
    mock.send_card.return_value = {
        "status": "sent",
        "channel": "Test-Channel",
        "timestamp": "2026-01-16T12:00:00",
    }

    # request_approval
    mock.request_approval.return_value = {
        "status": "pending",
        "item_id": "BRF-001",
        "item_type": "Brief",
        "channel": "Test-Channel",
        "timestamp": "2026-01-16T12:00:00",
    }

    # send_kpi_digest
    mock.send_kpi_digest.return_value = {
        "status": "sent",
        "period": "2026-W03",
        "channel": "Test-Channel",
        "timestamp": "2026-01-16T12:00:00",
    }

    return mock


@pytest.fixture
def mock_confluence_mcp():
    """ConfluenceMCP Mock"""
    mock = AsyncMock()

    # search_pages
    mock.search_pages.return_value = {"pages": [], "total": 0}

    # get_page
    mock.get_page.return_value = {
        "page_id": "12345",
        "title": "Test Page",
        "content": "<p>Test content</p>",
        "version": 1,
    }

    # create_page
    mock.create_page.return_value = {"page_id": "67890", "title": "New Page", "version": 1}

    # update_page
    mock.update_page.return_value = {"page_id": "12345", "title": "Updated Page", "version": 2}

    # append_to_page
    mock.append_to_page.return_value = {"page_id": "12345", "version": 2}

    # delete_page
    mock.delete_page.return_value = {"success": True}

    # list_spaces
    mock.list_spaces.return_value = {"spaces": [{"key": "TEST", "name": "Test Space"}], "total": 1}

    return mock


@pytest.fixture
async def test_db_engine():
    """테스트용 인메모리 데이터베이스 엔진"""
    # SQLite 인메모리 데이터베이스 사용
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True,
    )

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # 정리
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션"""
    SessionLocal = async_sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        yield session


@pytest.fixture
async def agent_runtime_instance(mock_env, sample_agent_markdown, monkeypatch):
    """AgentRuntime 인스턴스 (초기화 완료)"""
    from backend.agent_runtime.runner import AgentRuntime

    # .claude/agents 경로를 tmp_path로 변경
    monkeypatch.setattr(
        "backend.agent_runtime.runner.Path",
        lambda x: sample_agent_markdown.parent if ".claude" in str(x) else Path(x),
    )

    runtime = AgentRuntime()
    await runtime.initialize()

    yield runtime

    # 정리
    runtime.sessions.clear()
    runtime.agents.clear()


@pytest.fixture
def mock_claude_sdk_client():
    """ClaudeSDKClient Mock"""
    mock_client = MagicMock()
    mock_client.chat = AsyncMock(return_value={"role": "assistant", "content": "Test response"})
    return mock_client


@pytest.fixture
def mock_httpx_response():
    """httpx Response Mock (메타데이터 추출용)"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <head>
        <title>Test Seminar</title>
        <meta property="og:title" content="Test Seminar Title">
        <meta property="og:description" content="Test description">
    </head>
    <body>
        <h1>Test Seminar</h1>
        <p>Date: 2026-01-15</p>
    </body>
    </html>
    """
    return mock_response
