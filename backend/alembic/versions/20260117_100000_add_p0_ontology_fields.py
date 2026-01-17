"""Add P0 ontology fields (Recency, Sync, Lifecycle)

Entity 테이블:
- Recency 시간 필드: published_at, observed_at, ingested_at
- Source Sync 상태: last_synced_at, sync_status

Triple 테이블:
- Lifecycle 필드: status, assertion_type, evidence_span, extractor_run_id, verified_by, verified_at, updated_at

Revision ID: 2a0199fcd881
Revises: 20260116_120000_add_core_tables
Create Date: 2026-01-17 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a0199fcd881"
down_revision: str = "3b4c5d6e7f80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ===== SyncStatus Enum 생성 =====
    sync_status_enum = sa.Enum("ok", "stale", "error", name="syncstatus")
    sync_status_enum.create(op.get_bind(), checkfirst=True)

    # ===== TripleStatus Enum 생성 =====
    triple_status_enum = sa.Enum(
        "proposed", "verified", "deprecated", "rejected", name="triplestatus"
    )
    triple_status_enum.create(op.get_bind(), checkfirst=True)

    # ===== AssertionType Enum 생성 =====
    assertion_type_enum = sa.Enum("observed", "inferred", name="assertiontype")
    assertion_type_enum.create(op.get_bind(), checkfirst=True)

    # ===== Entity 테이블: Recency 필드 추가 =====
    op.add_column(
        "entities",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "entities",
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "entities",
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ===== Entity 테이블: Source Sync 필드 추가 =====
    op.add_column(
        "entities",
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "entities",
        sa.Column(
            "sync_status",
            sa.Enum("ok", "stale", "error", name="syncstatus", create_type=False),
            nullable=True,
        ),
    )

    # ===== Entity 테이블: Recency/Sync 인덱스 추가 =====
    op.create_index("idx_entity_published_at", "entities", ["published_at"])
    op.create_index("idx_entity_observed_at", "entities", ["observed_at"])
    op.create_index("idx_entity_ingested_at", "entities", ["ingested_at"])
    op.create_index("idx_entity_sync_status", "entities", ["sync_status"])
    op.create_index("idx_entity_last_synced_at", "entities", ["last_synced_at"])

    # ===== Triple 테이블: Lifecycle 필드 추가 =====
    op.add_column(
        "triples",
        sa.Column(
            "status",
            sa.Enum(
                "proposed",
                "verified",
                "deprecated",
                "rejected",
                name="triplestatus",
                create_type=False,
            ),
            nullable=False,
            server_default="proposed",
        ),
    )
    op.add_column(
        "triples",
        sa.Column(
            "assertion_type",
            sa.Enum("observed", "inferred", name="assertiontype", create_type=False),
            nullable=False,
            server_default="observed",
        ),
    )
    op.add_column(
        "triples",
        sa.Column("evidence_span", sa.JSON, nullable=True),
    )
    op.add_column(
        "triples",
        sa.Column("extractor_run_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "triples",
        sa.Column("verified_by", sa.String(100), nullable=True),
    )
    op.add_column(
        "triples",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "triples",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # ===== Triple 테이블: Lifecycle 인덱스 추가 =====
    op.create_index("idx_triple_status", "triples", ["status"])
    op.create_index("idx_triple_assertion_type", "triples", ["assertion_type"])
    # 복합 인덱스: BFS 안전모드용 (status + predicate)
    op.create_index("idx_triple_status_predicate", "triples", ["status", "predicate"])
    # 복합 인덱스: 쿼리 최적화 (status + assertion_type)
    op.create_index("idx_triple_status_assertion", "triples", ["status", "assertion_type"])


def downgrade() -> None:
    # ===== Triple 인덱스 삭제 =====
    op.drop_index("idx_triple_status_assertion", table_name="triples")
    op.drop_index("idx_triple_status_predicate", table_name="triples")
    op.drop_index("idx_triple_assertion_type", table_name="triples")
    op.drop_index("idx_triple_status", table_name="triples")

    # ===== Triple 컬럼 삭제 =====
    op.drop_column("triples", "updated_at")
    op.drop_column("triples", "verified_at")
    op.drop_column("triples", "verified_by")
    op.drop_column("triples", "extractor_run_id")
    op.drop_column("triples", "evidence_span")
    op.drop_column("triples", "assertion_type")
    op.drop_column("triples", "status")

    # ===== Entity 인덱스 삭제 =====
    op.drop_index("idx_entity_last_synced_at", table_name="entities")
    op.drop_index("idx_entity_sync_status", table_name="entities")
    op.drop_index("idx_entity_ingested_at", table_name="entities")
    op.drop_index("idx_entity_observed_at", table_name="entities")
    op.drop_index("idx_entity_published_at", table_name="entities")

    # ===== Entity 컬럼 삭제 =====
    op.drop_column("entities", "sync_status")
    op.drop_column("entities", "last_synced_at")
    op.drop_column("entities", "ingested_at")
    op.drop_column("entities", "observed_at")
    op.drop_column("entities", "published_at")

    # ===== Enum 타입 삭제 =====
    sa.Enum(name="assertiontype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="triplestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="syncstatus").drop(op.get_bind(), checkfirst=True)
