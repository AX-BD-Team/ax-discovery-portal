"""Add ontology tables (entities and triples)

온톨로지 기반 Knowledge Graph 테이블 생성
- entities: 그래프 노드 (12종 EntityType)
- triples: 그래프 엣지 (15종 PredicateType, SPO 구조)

Revision ID: 1f0188fcd880
Revises:
Create Date: 2026-01-15 08:41:50.599255

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f0188fcd880"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # EntityType Enum 생성
    entity_type_enum = sa.Enum(
        "Signal",
        "Topic",
        "Scorecard",
        "Brief",
        "Customer",
        "Technology",
        "Competitor",
        "Industry",
        "Evidence",
        "Source",
        "ReasoningStep",
        "Play",
        name="entitytype",
    )

    # PredicateType Enum 생성
    predicate_type_enum = sa.Enum(
        "has_pain",
        "has_scorecard",
        "has_brief",
        "belongs_to_play",
        "similar_to",
        "parent_of",
        "related_to",
        "targets",
        "uses_technology",
        "competes_with",
        "in_industry",
        "supported_by",
        "sourced_from",
        "inferred_from",
        "leads_to",
        name="predicatetype",
    )

    # entities 테이블 생성
    op.create_table(
        "entities",
        sa.Column("entity_id", sa.String(50), primary_key=True),
        sa.Column("entity_type", entity_type_enum, nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("embedding", sa.JSON, nullable=True),
        sa.Column("confidence", sa.Float, default=1.0),
        sa.Column("properties", sa.JSON, default=dict),
        sa.Column("external_ref_id", sa.String(100), nullable=True),
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
        sa.Column("created_by", sa.String(100), nullable=True),
    )

    # entities 인덱스
    op.create_index("idx_entity_type", "entities", ["entity_type"])
    op.create_index("idx_entity_name", "entities", ["name"])
    op.create_index("idx_entity_external_ref", "entities", ["external_ref_id"])
    op.create_index("idx_entity_created_at", "entities", ["created_at"])

    # triples 테이블 생성
    op.create_table(
        "triples",
        sa.Column("triple_id", sa.String(50), primary_key=True),
        sa.Column(
            "subject_id",
            sa.String(50),
            sa.ForeignKey("entities.entity_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("predicate", predicate_type_enum, nullable=False),
        sa.Column(
            "object_id",
            sa.String(50),
            sa.ForeignKey("entities.entity_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weight", sa.Float, default=1.0),
        sa.Column("confidence", sa.Float, default=1.0),
        sa.Column("evidence_ids", sa.JSON, default=list),
        sa.Column("reasoning_path_id", sa.String(50), nullable=True),
        sa.Column("properties", sa.JSON, default=dict),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.UniqueConstraint("subject_id", "predicate", "object_id", name="uq_triple_spo"),
    )

    # triples 인덱스 (SPO, POS, OSP 패턴)
    op.create_index("idx_triple_spo", "triples", ["subject_id", "predicate", "object_id"])
    op.create_index("idx_triple_pos", "triples", ["predicate", "object_id", "subject_id"])
    op.create_index("idx_triple_osp", "triples", ["object_id", "subject_id", "predicate"])
    op.create_index("idx_triple_confidence", "triples", ["confidence"])
    op.create_index("idx_triple_created_at", "triples", ["created_at"])


def downgrade() -> None:
    # triples 테이블 삭제
    op.drop_index("idx_triple_created_at", table_name="triples")
    op.drop_index("idx_triple_confidence", table_name="triples")
    op.drop_index("idx_triple_osp", table_name="triples")
    op.drop_index("idx_triple_pos", table_name="triples")
    op.drop_index("idx_triple_spo", table_name="triples")
    op.drop_table("triples")

    # entities 테이블 삭제
    op.drop_index("idx_entity_created_at", table_name="entities")
    op.drop_index("idx_entity_external_ref", table_name="entities")
    op.drop_index("idx_entity_name", table_name="entities")
    op.drop_index("idx_entity_type", table_name="entities")
    op.drop_table("entities")

    # Enum 타입 삭제
    sa.Enum(name="predicatetype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="entitytype").drop(op.get_bind(), checkfirst=True)
