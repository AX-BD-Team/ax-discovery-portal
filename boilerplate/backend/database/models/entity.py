"""
Entity 모델 템플릿

온톨로지 그래프의 노드(엔티티)를 저장하는 테이블 정의
프로젝트에 맞게 EntityType enum을 커스터마이징하세요.
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class EntityType(enum.Enum):
    """
    엔티티 유형 정의

    프로젝트 도메인에 맞게 커스터마이징하세요.
    예시 카테고리:
    - Pipeline Entities: 데이터 처리 파이프라인 단계
    - Organization Entities: 조직/인물 관련
    - Market Context: 시장/기술/산업 관련
    - Evidence: 근거/출처 관련
    - Operational: 운영/작업 관련
    """

    # ===== Pipeline Entities =====
    # {{ENTITY_TYPE_1}} = "{{EntityType1}}"
    # {{ENTITY_TYPE_2}} = "{{EntityType2}}"

    # ===== Organization Entities =====
    ORGANIZATION = "Organization"
    PERSON = "Person"
    TEAM = "Team"

    # ===== Market Context =====
    TECHNOLOGY = "Technology"
    INDUSTRY = "Industry"

    # ===== Evidence & Reasoning =====
    EVIDENCE = "Evidence"
    SOURCE = "Source"
    REASONING_STEP = "ReasoningStep"

    # ===== Operational =====
    TASK = "Task"


class SyncStatus(enum.Enum):
    """Source 동기화 상태"""

    OK = "ok"
    STALE = "stale"
    ERROR = "error"


class Entity(Base):
    """
    Entity 테이블

    온톨로지 그래프의 노드를 저장하는 테이블
    Subject-Predicate-Object 구조에서 Subject/Object 역할

    Recency 속성 (Evidence/Source용):
    - published_at: 외부 기사/문서 발행 시각
    - observed_at: 내부에서 관측/기록된 시각
    - ingested_at: 시스템에 들어온 시각

    Source Sync 속성:
    - last_synced_at: 동기화 마지막 성공 시각
    - sync_status: ok/stale/error
    """

    __tablename__ = "entities"

    # Primary Key
    entity_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # 엔티티 유형
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # 기본 정보
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # 임베딩 (벡터 검색용)
    embedding: Mapped[list | None] = mapped_column(JSON)

    # 신뢰도 (0.0 ~ 1.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # 메타데이터 (유형별 추가 속성)
    properties: Mapped[dict | None] = mapped_column(JSON, default=dict)

    # 외부 참조 ID (기존 테이블과의 연결)
    external_ref_id: Mapped[str | None] = mapped_column(String(100))

    # ===== Recency 시간 필드 (Evidence/Source용) =====
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ===== Source Sync 상태 =====
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_status: Mapped[SyncStatus | None] = mapped_column(Enum(SyncStatus))

    # ===== 생성/수정 시각 =====
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    created_by: Mapped[str | None] = mapped_column(String(100))

    # Indexes
    __table_args__ = (
        Index("idx_entity_type", "entity_type"),
        Index("idx_entity_name", "name"),
        Index("idx_entity_external_ref", "external_ref_id"),
        Index("idx_entity_created_at", "created_at"),
        Index("idx_entity_published_at", "published_at"),
        Index("idx_entity_sync_status", "sync_status"),
    )

    def __repr__(self) -> str:
        return f"<Entity(entity_id='{self.entity_id}', type='{self.entity_type.value}', name='{self.name}')>"

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "description": self.description,
            "confidence": self.confidence,
            "properties": self.properties,
            "external_ref_id": self.external_ref_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "sync_status": self.sync_status.value if self.sync_status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }

    def get_freshness_score(self, as_of: datetime | None = None) -> float:
        """
        Recency 점수 계산 (0.0 ~ 1.0)
        최근 데이터일수록 높은 점수
        """
        if as_of is None:
            as_of = datetime.now(UTC)

        reference_time = (
            self.published_at or self.observed_at or self.ingested_at or self.created_at
        )

        if reference_time is None:
            return 0.0

        delta_days = (as_of - reference_time).days

        # 감쇠 함수: 30일 이내 = 1.0, 90일 = 0.5, 180일 = 0.25
        if delta_days <= 30:
            return 1.0
        elif delta_days <= 90:
            return 0.5 + 0.5 * (90 - delta_days) / 60
        elif delta_days <= 180:
            return 0.25 + 0.25 * (180 - delta_days) / 90
        else:
            return max(0.1, 0.25 * (365 - delta_days) / 185)
