"""Add core tables (signals, scorecards, briefs, play_records, action_logs, traces, competency_questions)

핵심 비즈니스 테이블 생성:
- signals: Signal 엔티티 (사업기회 신호)
- scorecards: Scorecard 평가 (100점 만점, 5차원)
- opportunity_briefs: 1-Page Brief
- play_records: Play 진행현황
- action_logs: 활동 로그
- traces: 실행 추적 (P0 실패 분류)
- competency_questions: BD용 regression 테스트 (P0)

Revision ID: 3b4c5d6e7f80
Revises: 2a3f9d8e7c01
Create Date: 2026-01-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b4c5d6e7f80"
down_revision: str | None = "2a3f9d8e7c01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enum 타입 생성
    signal_source_enum = sa.Enum("KT", "그룹사", "대외", name="signalsource")
    signal_channel_enum = sa.Enum(
        "데스크리서치", "자사활동", "영업PM", "인바운드", "아웃바운드", name="signalchannel"
    )
    signal_status_enum = sa.Enum(
        "NEW",
        "SCORING",
        "SCORED",
        "BRIEF_CREATED",
        "VALIDATED",
        "PILOT_READY",
        "ARCHIVED",
        name="signalstatus",
    )
    brief_status_enum = sa.Enum(
        "DRAFT", "REVIEW", "APPROVED", "VALIDATED", "PILOT_READY", "ARCHIVED", name="briefstatus"
    )
    action_type_enum = sa.Enum(
        "ACTIVITY",
        "SIGNAL",
        "SCORECARD",
        "BRIEF",
        "VALIDATION",
        "PILOT",
        "OTHER",
        name="actiontype",
    )
    trace_status_enum = sa.Enum("running", "success", "partial", "failed", name="tracestatus")

    # 1. signals 테이블
    op.create_table(
        "signals",
        sa.Column("signal_id", sa.String(50), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("source", signal_source_enum, nullable=False),
        sa.Column("channel", signal_channel_enum, nullable=False),
        sa.Column("play_id", sa.String(100), nullable=False),
        sa.Column("customer_segment", sa.String(200), nullable=True),
        sa.Column("pain", sa.Text, nullable=False),
        sa.Column("proposed_value", sa.Text, nullable=True),
        sa.Column("kpi_hypothesis", sa.JSON, nullable=True),
        sa.Column("evidence", sa.JSON, nullable=True),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("status", signal_status_enum, nullable=False, server_default="NEW"),
        sa.Column("owner", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
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
    op.create_index("idx_signal_status", "signals", ["status"])
    op.create_index("idx_signal_source", "signals", ["source"])
    op.create_index("idx_signal_channel", "signals", ["channel"])
    op.create_index("idx_signal_play_id", "signals", ["play_id"])
    op.create_index("idx_signal_created_at", "signals", ["created_at"])

    # 2. scorecards 테이블
    op.create_table(
        "scorecards",
        sa.Column("scorecard_id", sa.String(50), primary_key=True),
        sa.Column(
            "signal_id",
            sa.String(50),
            sa.ForeignKey("signals.signal_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("total_score", sa.Float, nullable=False),
        sa.Column("dimension_scores", sa.JSON, nullable=False),
        sa.Column("red_flags", sa.JSON, nullable=True),
        sa.Column("recommendation", sa.JSON, nullable=False),
        sa.Column("scored_by", sa.String(100), nullable=True),
        sa.Column(
            "scored_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_scorecard_signal_id", "scorecards", ["signal_id"])
    op.create_index("idx_scorecard_total_score", "scorecards", ["total_score"])
    op.create_index("idx_scorecard_scored_at", "scorecards", ["scored_at"])

    # 3. opportunity_briefs 테이블
    op.create_table(
        "opportunity_briefs",
        sa.Column("brief_id", sa.String(50), primary_key=True),
        sa.Column(
            "signal_id",
            sa.String(50),
            sa.ForeignKey("signals.signal_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("customer", sa.JSON, nullable=False),
        sa.Column("problem", sa.JSON, nullable=False),
        sa.Column("solution_hypothesis", sa.JSON, nullable=False),
        sa.Column("kpis", sa.JSON, nullable=False),
        sa.Column("evidence", sa.JSON, nullable=False),
        sa.Column("validation_plan", sa.JSON, nullable=False),
        sa.Column("mvp_scope", sa.JSON, nullable=True),
        sa.Column("risks", sa.JSON, nullable=True),
        sa.Column("status", brief_status_enum, nullable=False, server_default="DRAFT"),
        sa.Column("owner", sa.String(100), nullable=False),
        sa.Column("confluence_url", sa.String(500), nullable=True),
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
    op.create_index("idx_brief_signal_id", "opportunity_briefs", ["signal_id"])
    op.create_index("idx_brief_status", "opportunity_briefs", ["status"])
    op.create_index("idx_brief_owner", "opportunity_briefs", ["owner"])
    op.create_index("idx_brief_created_at", "opportunity_briefs", ["created_at"])

    # 4. play_records 테이블
    op.create_table(
        "play_records",
        sa.Column("play_id", sa.String(100), primary_key=True),
        sa.Column("play_name", sa.String(200), nullable=False),
        sa.Column("owner", sa.String(100), nullable=True),
        sa.Column("status", sa.String(1), nullable=False),
        sa.Column("activity_qtd", sa.Integer, nullable=False, server_default="0"),
        sa.Column("signal_qtd", sa.Integer, nullable=False, server_default="0"),
        sa.Column("brief_qtd", sa.Integer, nullable=False, server_default="0"),
        sa.Column("s2_qtd", sa.Integer, nullable=False, server_default="0"),
        sa.Column("s3_qtd", sa.Integer, nullable=False, server_default="0"),
        sa.Column("next_action", sa.String(500), nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("last_activity_date", sa.Date, nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("confluence_live_doc_url", sa.String(500), nullable=True),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_play_record_status", "play_records", ["status"])
    op.create_index("idx_play_record_owner", "play_records", ["owner"])
    op.create_index("idx_play_record_due_date", "play_records", ["due_date"])
    op.create_index("idx_play_record_last_updated", "play_records", ["last_updated"])

    # 5. action_logs 테이블
    op.create_table(
        "action_logs",
        sa.Column("log_id", sa.String(50), primary_key=True),
        sa.Column("play_id", sa.String(100), nullable=False),
        sa.Column("action_type", action_type_enum, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("related_ids", sa.JSON, nullable=True),
        sa.Column("actor", sa.String(100), nullable=True),
        sa.Column("agent_id", sa.String(100), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("workflow_id", sa.String(100), nullable=True),
        sa.Column("extra_data", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_action_log_play_id", "action_logs", ["play_id"])
    op.create_index("idx_action_log_action_type", "action_logs", ["action_type"])
    op.create_index("idx_action_log_created_at", "action_logs", ["created_at"])
    op.create_index("idx_action_log_actor", "action_logs", ["actor"])

    # 6. traces 테이블
    op.create_table(
        "traces",
        sa.Column("trace_id", sa.String(100), primary_key=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("workflow_id", sa.String(50), nullable=True),
        sa.Column("run_id", sa.String(100), nullable=True),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("input_data", sa.JSON, nullable=True),
        sa.Column("output_data", sa.JSON, nullable=True),
        sa.Column("status", trace_status_enum, nullable=False, server_default="running"),
        sa.Column("error_types", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("entity_ids", sa.JSON, nullable=True),
        sa.Column("triple_ids", sa.JSON, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(100), nullable=True),
        sa.Column("extractor_run_id", sa.String(100), nullable=True),
        sa.Column("extra_metadata", sa.JSON, nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
    )
    op.create_index("idx_trace_session_id", "traces", ["session_id"])
    op.create_index("idx_trace_workflow_id", "traces", ["workflow_id"])
    op.create_index("idx_trace_operation", "traces", ["operation"])
    op.create_index("idx_trace_status", "traces", ["status"])
    op.create_index("idx_trace_started_at", "traces", ["started_at"])

    # 7. competency_questions 테이블
    op.create_table(
        "competency_questions",
        sa.Column("question_id", sa.String(50), primary_key=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("expected_query_type", sa.String(50), nullable=True),
        sa.Column("parameters", sa.JSON, nullable=True),
        sa.Column("expected_result_pattern", sa.JSON, nullable=True),
        sa.Column("min_precision", sa.Float, nullable=True, server_default="0.8"),
        sa.Column("min_recall", sa.Float, nullable=True, server_default="0.7"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_test_result", sa.JSON, nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("idx_cq_category", "competency_questions", ["category"])
    op.create_index("idx_cq_is_active", "competency_questions", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_cq_is_active", table_name="competency_questions")
    op.drop_index("idx_cq_category", table_name="competency_questions")
    op.drop_table("competency_questions")
    op.drop_index("idx_trace_started_at", table_name="traces")
    op.drop_index("idx_trace_status", table_name="traces")
    op.drop_index("idx_trace_operation", table_name="traces")
    op.drop_index("idx_trace_workflow_id", table_name="traces")
    op.drop_index("idx_trace_session_id", table_name="traces")
    op.drop_table("traces")
    op.drop_index("idx_action_log_actor", table_name="action_logs")
    op.drop_index("idx_action_log_created_at", table_name="action_logs")
    op.drop_index("idx_action_log_action_type", table_name="action_logs")
    op.drop_index("idx_action_log_play_id", table_name="action_logs")
    op.drop_table("action_logs")
    op.drop_index("idx_play_record_last_updated", table_name="play_records")
    op.drop_index("idx_play_record_due_date", table_name="play_records")
    op.drop_index("idx_play_record_owner", table_name="play_records")
    op.drop_index("idx_play_record_status", table_name="play_records")
    op.drop_table("play_records")
    op.drop_index("idx_brief_created_at", table_name="opportunity_briefs")
    op.drop_index("idx_brief_owner", table_name="opportunity_briefs")
    op.drop_index("idx_brief_status", table_name="opportunity_briefs")
    op.drop_index("idx_brief_signal_id", table_name="opportunity_briefs")
    op.drop_table("opportunity_briefs")
    op.drop_index("idx_scorecard_scored_at", table_name="scorecards")
    op.drop_index("idx_scorecard_total_score", table_name="scorecards")
    op.drop_index("idx_scorecard_signal_id", table_name="scorecards")
    op.drop_table("scorecards")
    op.drop_index("idx_signal_created_at", table_name="signals")
    op.drop_index("idx_signal_play_id", table_name="signals")
    op.drop_index("idx_signal_channel", table_name="signals")
    op.drop_index("idx_signal_source", table_name="signals")
    op.drop_index("idx_signal_status", table_name="signals")
    op.drop_table("signals")
    sa.Enum(name="tracestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="actiontype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="briefstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="signalstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="signalchannel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="signalsource").drop(op.get_bind(), checkfirst=True)
