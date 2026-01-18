"""
AX Discovery Portal - 환경 설정

Pydantic Settings를 사용한 중앙 집중화된 설정 관리
환경별 설정 분리: development, staging, production
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정

    환경변수 또는 .env 파일에서 설정을 로드합니다.
    환경별 .env 파일 우선순위:
    1. .env.{APP_ENV}.local (git에서 제외, 로컬 오버라이드)
    2. .env.{APP_ENV}
    3. .env.local (git에서 제외)
    4. .env
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # Application
    # =========================================================================
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="애플리케이션 환경 (development, staging, production)",
    )
    debug: bool = Field(default=True, description="디버그 모드")
    log_level: str = Field(default="INFO", description="로그 레벨")

    # API Server
    api_host: str = Field(default="0.0.0.0", description="API 서버 호스트")
    api_port: int = Field(default=8000, description="API 서버 포트")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="허용된 CORS 오리진 (쉼표 구분)",
    )

    # =========================================================================
    # Security
    # =========================================================================
    jwt_secret_key: str = Field(
        default="change-me-in-production-jwt-secret",
        description="JWT 서명 시크릿 키",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT 알고리즘")
    jwt_access_token_expire_minutes: int = Field(
        default=60, description="JWT 액세스 토큰 만료 시간 (분)"
    )
    approval_timeout: int = Field(default=86400, description="승인 타임아웃 (초)")

    # =========================================================================
    # Monitoring - Sentry
    # =========================================================================
    sentry_dsn: str = Field(default="", description="Sentry DSN. 비어있으면 비활성화")
    app_version: str = Field(default="0.6.0", description="앱 버전 (Sentry 릴리스용)")
    sentry_traces_sample_rate: float = Field(
        default=0.2, description="Sentry 성능 모니터링 샘플링 비율 (0.0~1.0)"
    )
    sentry_profiles_sample_rate: float = Field(
        default=0.1, description="Sentry 프로파일링 샘플링 비율 (0.0~1.0)"
    )

    # =========================================================================
    # Anthropic API
    # =========================================================================
    anthropic_api_key: str = Field(default="", description="Anthropic API 키")
    agent_model: str = Field(default="claude-sonnet-4-20250514", description="에이전트 모델")

    # =========================================================================
    # Database - PostgreSQL (Render) / Cloudflare D1
    # =========================================================================
    database_url: str = Field(
        default="",
        description="PostgreSQL 연결 URL (asyncpg)",
    )

    # Cloudflare D1
    cloudflare_account_id: str = Field(default="", description="Cloudflare 계정 ID")
    cloudflare_api_token: str = Field(default="", description="Cloudflare API 토큰")
    d1_database_id: str = Field(default="", description="D1 데이터베이스 ID")

    # =========================================================================
    # Vector Search - Cloudflare Vectorize
    # =========================================================================
    vectorize_index_name: str = Field(
        default="ax-discovery-entities", description="Vectorize 인덱스 이름"
    )
    vectorize_signal_index: str = Field(
        default="ax-discovery-signals", description="Signal 벡터 인덱스"
    )
    vectorize_entity_index: str = Field(
        default="ax-discovery-entities", description="Entity 벡터 인덱스"
    )
    vectorize_evidence_index: str = Field(
        default="ax-discovery-evidence", description="Evidence 벡터 인덱스"
    )

    # =========================================================================
    # Embeddings - OpenAI
    # =========================================================================
    openai_api_key: str = Field(default="", description="OpenAI API 키")
    embedding_model: str = Field(default="text-embedding-3-small", description="임베딩 모델")

    # =========================================================================
    # Confluence
    # =========================================================================
    confluence_base_url: str = Field(default="", description="Confluence 베이스 URL")
    confluence_api_token: str = Field(default="", description="Confluence API 토큰")
    confluence_user_email: str = Field(default="", description="Confluence 사용자 이메일")
    confluence_space_key: str = Field(default="AXBD", description="Confluence 스페이스 키")
    confluence_action_log_page_id: str = Field(default="", description="Action Log 페이지 ID")
    confluence_play_db_page_id: str = Field(default="", description="Play DB 페이지 ID")
    confluence_live_doc_page_id: str = Field(default="", description="Live Doc 페이지 ID")

    # =========================================================================
    # Teams / Slack Integration
    # =========================================================================
    teams_webhook_url: str = Field(default="", description="Teams Webhook URL")
    teams_channel_name: str = Field(default="AX-BD-Alerts", description="Teams 채널 이름")
    slack_webhook_url: str = Field(default="", description="Slack Webhook URL")
    slack_channel_name: str = Field(default="#ax-bd-alerts", description="Slack 채널 이름")

    # =========================================================================
    # Computed Properties
    # =========================================================================
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.app_env == "development"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_staging(self) -> bool:
        """스테이징 환경 여부"""
        return self.app_env == "staging"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.app_env == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        """CORS 오리진 리스트"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def confluence_configured(self) -> bool:
        """Confluence 설정 완료 여부"""
        return bool(self.confluence_base_url and self.confluence_api_token)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_configured(self) -> bool:
        """데이터베이스 설정 완료 여부"""
        return bool(self.database_url) or bool(self.d1_database_id)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sentry_configured(self) -> bool:
        """Sentry 설정 완료 여부"""
        return bool(self.sentry_dsn)


@lru_cache
def get_settings() -> Settings:
    """싱글톤 설정 인스턴스 반환

    Returns:
        Settings: 애플리케이션 설정
    """
    return Settings()


# 편의를 위한 전역 설정 접근
settings = get_settings()
