"""
Entity 모델

온톨로지 그래프의 노드(엔티티)를 저장하는 테이블 정의

P1 변경사항:
- Organization 타입 추가 (Customer/Competitor를 역할로 통합)
- Evidence/Source에 시간 필드 3종 분리 (published_at, observed_at, ingested_at)
- Source에 sync 상태 추가 (last_synced_at, sync_status)
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class EntityType(enum.Enum):
    """엔티티 유형 (22종) - BD 특화 온톨로지 v2"""

    # ===== Pipeline Entities (7종) =====
    ACTIVITY = "Activity"  # v2: 세미나/미팅/인바운드 등 활동
    SIGNAL = "Signal"  # 사업 기회 신호
    TOPIC = "Topic"  # Pain Point / Trend
    SCORECARD = "Scorecard"  # 100점 평가
    BRIEF = "Brief"  # 1-Page 요약
    VALIDATION = "Validation"  # v2: S2 검증 결과
    PILOT = "Pilot"  # v2: S3 파일럿 프로젝트

    # ===== Organization Entities (3종) =====
    ORGANIZATION = "Organization"  # 회사/기관 (역할 분리)
    PERSON = "Person"  # v2: 담당자/의사결정자
    TEAM = "Team"  # v2: BD팀/고객팀

    # ===== Market Context (4종) =====
    TECHNOLOGY = "Technology"  # 기술/솔루션
    INDUSTRY = "Industry"  # 산업/버티컬
    MARKET_SEGMENT = "MarketSegment"  # v2: 시장 세그먼트
    TREND = "Trend"  # v2: 시장 트렌드

    # ===== Evidence & Reasoning (4종) =====
    EVIDENCE = "Evidence"  # 근거 자료
    SOURCE = "Source"  # 출처 (Confluence, 기사 등)
    REASONING_STEP = "ReasoningStep"  # 추론 단계
    DECISION = "Decision"  # v2: GO/NOGO 결정

    # ===== Operational (4종) =====
    PLAY = "Play"  # BD Play (사업 영역)
    MEETING = "Meeting"  # v2: 미팅 기록
    TASK = "Task"  # v2: 후속 조치
    MILESTONE = "Milestone"  # v2: 주요 이정표

    # ===== Deprecated (하위 호환용) =====
    CUSTOMER = "Customer"  # deprecated: Organization + HAS_ROLE 사용 권장
    COMPETITOR = "Competitor"  # deprecated: Organization + HAS_ROLE 사용 권장


class SyncStatus(enum.Enum):
    """Source 동기화 상태"""

    OK = "ok"  # 동기화 성공
    STALE = "stale"  # 오래됨 (재동기화 필요)
    ERROR = "error"  # 동기화 실패


class Entity(Base):
    """
    Entity 테이블

    온톨로지 그래프의 노드를 저장하는 테이블
    Subject-Predicate-Object 구조에서 Subject/Object 역할

    P0 Recency 속성 (Evidence/Source용):
    - published_at: 외부 기사/문서 발행 시각
    - observed_at: 내부에서 관측/기록된 시각 (미팅노트, 콜로그 등)
    - ingested_at: 시스템에 들어온 시각

    P0 Source Sync 속성:
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

    # 임베딩 (벡터 검색용) - JSON으로 저장, 실제 검색은 Vectorize 사용
    embedding: Mapped[list | None] = mapped_column(JSON)

    # 신뢰도 (0.0 ~ 1.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # 메타데이터 (유형별 추가 속성)
    # Organization: {"canonical_name": "...", "aliases": [...], "industry": "..."}
    # Evidence: {"content_hash": "...", "word_count": 123}
    properties: Mapped[dict | None] = mapped_column(JSON, default=dict)

    # 외부 참조 ID (기존 테이블과의 연결)
    # 예: Signal 엔티티면 signals 테이블의 signal_id
    external_ref_id: Mapped[str | None] = mapped_column(String(100))

    # ===== P0: Recency 시간 필드 (Evidence/Source용) =====
    # 외부 기사/문서 발행 시각 (원본 데이터의 시간)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 내부에서 관측/기록된 시각 (미팅노트, 콜로그 등)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 시스템에 들어온 시각 (수집/입력 시점)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ===== P0: Source Sync 상태 =====
    # Confluence/크롤러 동기화 마지막 성공 시각
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 동기화 상태 (ok/stale/error)
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

    # 생성자 (user_id 또는 agent_id)
    created_by: Mapped[str | None] = mapped_column(String(100))

    # Indexes
    __table_args__ = (
        Index("idx_entity_type", "entity_type"),
        Index("idx_entity_name", "name"),
        Index("idx_entity_external_ref", "external_ref_id"),
        Index("idx_entity_created_at", "created_at"),
        # P0: Recency 인덱스
        Index("idx_entity_published_at", "published_at"),
        Index("idx_entity_observed_at", "observed_at"),
        Index("idx_entity_ingested_at", "ingested_at"),
        # P0: Source Sync 인덱스
        Index("idx_entity_sync_status", "sync_status"),
        Index("idx_entity_last_synced_at", "last_synced_at"),
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
            # Recency 필드
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
            # Sync 상태
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "sync_status": self.sync_status.value if self.sync_status else None,
            # 기본 타임스탬프
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

        # 가장 최신 시간 사용 (published > observed > ingested > created)
        reference_time = (
            self.published_at or self.observed_at or self.ingested_at or self.created_at
        )

        if reference_time is None:
            return 0.0

        # 시간 차이 계산 (일 단위)
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

    def is_stale(self, threshold_days: int = 30) -> bool:
        """Source가 오래되었는지 확인"""
        if self.entity_type != EntityType.SOURCE:
            return False

        if self.sync_status == SyncStatus.STALE:
            return True

        if self.last_synced_at:
            delta = datetime.now(UTC) - self.last_synced_at
            return delta.days > threshold_days

        return True  # sync 정보 없으면 stale 취급
