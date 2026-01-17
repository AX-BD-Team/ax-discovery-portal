"""Add stage system (opportunities, stage_transitions, approval_requests)

단계(Stage) 파이프라인 시스템 테이블 생성:
- opportunities: Opportunity 엔티티 (사업기회 파이프라인)
- stage_transitions: 단계 전환 이력
- approval_requests: HITL 승인 요청

Revision ID: 4c5d6e7f8901
Revises: 9a8b7c6d5e4f
Create Date: 2026-01-17 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c5d6e7f8901"
down_revision: str | None = "4c8e9f0a1b2d"  # ontology_v2_schema_expansion
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enum 타입 생성
    opportunity_stage_enum = sa.Enum(
        "01_DISCOVERY",
        "02_IDEA_CARD",
        "03_GATE1",
        "04_MOCKUP",
        "05_GATE2",
        "06_BIZ_PLANNING",
        "07_PILOT",
        "08_PRE_PROPOSAL",
        "09_HANDOFF",
        "HOLD",
        "DROP",
        name="opportunitystage",
    )

    transition_trigger_enum = sa.Enum(
        "AUTO",
        "MANUAL",
        "GATE",
        name="transitiontrigger",
    )

    gate_decision_enum = sa.Enum(
        "GO",
        "HOLD",
        "STOP",
        name="gatedecision",
    )

    approval_status_enum = sa.Enum(
        "PENDING",
        "APPROVED",
        "REJECTED",
        "EXPIRED",
        name="approvalstatus",
    )

    approval_type_enum = sa.Enum(
        "GATE1",
        "GATE2",
        "BIZ_APPROVAL",
        "PRE_PROPOSAL",
        "HANDOFF",
        "STAGE_ADVANCE",
        name="approvaltype",
    )

    # 1. opportunities 테이블
    op.create_table(
        "opportunities",
        sa.Column("opportunity_id", sa.String(50), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "current_stage",
            opportunity_stage_enum,
            nullable=False,
            server_default="01_DISCOVERY",
        ),
        sa.Column(
            "signal_id",
            sa.String(50),
            sa.ForeignKey("signals.signal_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "brief_id",
            sa.String(50),
            sa.ForeignKey("opportunity_briefs.brief_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("bd_owner", sa.String(100), nullable=True),
        sa.Column("play_id", sa.String(100), nullable=True),
        sa.Column("stage_artifacts", sa.JSON, nullable=True),
        sa.Column("gate_decisions", sa.JSON, nullable=True),
        sa.Column("hold_reason", sa.Text, nullable=True),
        sa.Column("drop_reason", sa.Text, nullable=True),
        sa.Column("tags", sa.JSON, nullable=True),
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
    )
    op.create_index("idx_opportunity_stage", "opportunities", ["current_stage"])
    op.create_index("idx_opportunity_signal_id", "opportunities", ["signal_id"])
    op.create_index("idx_opportunity_brief_id", "opportunities", ["brief_id"])
    op.create_index("idx_opportunity_bd_owner", "opportunities", ["bd_owner"])
    op.create_index("idx_opportunity_play_id", "opportunities", ["play_id"])
    op.create_index("idx_opportunity_created_at", "opportunities", ["created_at"])

    # 2. stage_transitions 테이블
    op.create_table(
        "stage_transitions",
        sa.Column("transition_id", sa.String(50), primary_key=True),
        sa.Column(
            "opportunity_id",
            sa.String(50),
            sa.ForeignKey("opportunities.opportunity_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_stage", sa.String(50), nullable=False),
        sa.Column("to_stage", sa.String(50), nullable=False),
        sa.Column(
            "trigger",
            transition_trigger_enum,
            nullable=False,
            server_default="MANUAL",
        ),
        sa.Column("gate_decision", gate_decision_enum, nullable=True),
        sa.Column("gate_comments", sa.Text, nullable=True),
        sa.Column("approver", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
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
    )
    op.create_index("idx_transition_opportunity_id", "stage_transitions", ["opportunity_id"])
    op.create_index("idx_transition_from_stage", "stage_transitions", ["from_stage"])
    op.create_index("idx_transition_to_stage", "stage_transitions", ["to_stage"])
    op.create_index("idx_transition_trigger", "stage_transitions", ["trigger"])
    op.create_index("idx_transition_created_at", "stage_transitions", ["created_at"])

    # 3. approval_requests 테이블
    op.create_table(
        "approval_requests",
        sa.Column("request_id", sa.String(50), primary_key=True),
        sa.Column(
            "opportunity_id",
            sa.String(50),
            sa.ForeignKey("opportunities.opportunity_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_stage", sa.String(50), nullable=False),
        sa.Column(
            "approval_type",
            approval_type_enum,
            nullable=False,
            server_default="STAGE_ADVANCE",
        ),
        sa.Column(
            "status",
            approval_status_enum,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("approvers", sa.JSON, nullable=False),
        sa.Column("responses", sa.JSON, nullable=True),
        sa.Column("requested_by", sa.String(100), nullable=False),
        sa.Column("request_reason", sa.Text, nullable=True),
        sa.Column("artifacts", sa.JSON, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.String(100), nullable=True),
        sa.Column("final_comments", sa.Text, nullable=True),
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
    )
    op.create_index("idx_approval_opportunity_id", "approval_requests", ["opportunity_id"])
    op.create_index("idx_approval_status", "approval_requests", ["status"])
    op.create_index("idx_approval_type", "approval_requests", ["approval_type"])
    op.create_index("idx_approval_target_stage", "approval_requests", ["target_stage"])
    op.create_index("idx_approval_requested_by", "approval_requests", ["requested_by"])
    op.create_index("idx_approval_expires_at", "approval_requests", ["expires_at"])
    op.create_index("idx_approval_created_at", "approval_requests", ["created_at"])


def downgrade() -> None:
    # approval_requests 테이블 삭제
    op.drop_index("idx_approval_created_at", table_name="approval_requests")
    op.drop_index("idx_approval_expires_at", table_name="approval_requests")
    op.drop_index("idx_approval_requested_by", table_name="approval_requests")
    op.drop_index("idx_approval_target_stage", table_name="approval_requests")
    op.drop_index("idx_approval_type", table_name="approval_requests")
    op.drop_index("idx_approval_status", table_name="approval_requests")
    op.drop_index("idx_approval_opportunity_id", table_name="approval_requests")
    op.drop_table("approval_requests")

    # stage_transitions 테이블 삭제
    op.drop_index("idx_transition_created_at", table_name="stage_transitions")
    op.drop_index("idx_transition_trigger", table_name="stage_transitions")
    op.drop_index("idx_transition_to_stage", table_name="stage_transitions")
    op.drop_index("idx_transition_from_stage", table_name="stage_transitions")
    op.drop_index("idx_transition_opportunity_id", table_name="stage_transitions")
    op.drop_table("stage_transitions")

    # opportunities 테이블 삭제
    op.drop_index("idx_opportunity_created_at", table_name="opportunities")
    op.drop_index("idx_opportunity_play_id", table_name="opportunities")
    op.drop_index("idx_opportunity_bd_owner", table_name="opportunities")
    op.drop_index("idx_opportunity_brief_id", table_name="opportunities")
    op.drop_index("idx_opportunity_signal_id", table_name="opportunities")
    op.drop_index("idx_opportunity_stage", table_name="opportunities")
    op.drop_table("opportunities")

    # Enum 타입 삭제
    sa.Enum(name="approvaltype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="approvalstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="gatedecision").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="transitiontrigger").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="opportunitystage").drop(op.get_bind(), checkfirst=True)
