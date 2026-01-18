"""Add evals tables (eval_suites, eval_tasks, eval_runs, eval_trials, etc.)

AI 에이전트 평가 플랫폼 테이블 생성:
- eval_suites: 평가 스위트 (Task 묶음)
- eval_tasks: 평가 과제 (개별 테스트 케이스)
- eval_runs: 평가 실행 세션
- eval_trials: 트라이얼 (1회 실행 시도)
- eval_transcripts: 실행 기록
- eval_outcomes: 최종 결과 상태
- eval_grader_results: 채점 결과

Revision ID: 5d6e7f890123
Revises: 4c5d6e7f8901
Create Date: 2026-01-18 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d6e7f890123"
down_revision: str | None = "4c5d6e7f8901"  # add_stage_system
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # =========================================================================
    # Enum 타입 생성
    # =========================================================================

    eval_task_type_enum = sa.Enum(
        "coding",
        "workflow",
        "conversational",
        "research",
        "computer_use",
        name="evaltasktype",
    )

    eval_trial_status_enum = sa.Enum(
        "pending",
        "running",
        "completed",
        "failed",
        "timeout",
        "cancelled",
        name="evaltrialstatus",
    )

    eval_run_status_enum = sa.Enum(
        "pending",
        "running",
        "completed",
        "failed",
        "cancelled",
        name="evalrunstatus",
    )

    eval_suite_purpose_enum = sa.Enum(
        "capability",
        "regression",
        "benchmark",
        "safety",
        name="evalsuitepurpose",
    )

    eval_decision_enum = sa.Enum(
        "pass",
        "fail",
        "marginal",
        "unknown",
        name="evaldecision",
    )

    # =========================================================================
    # 1. eval_suites 테이블
    # =========================================================================

    op.create_table(
        "eval_suites",
        sa.Column("suite_id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("purpose", eval_suite_purpose_enum, nullable=False),
        sa.Column("domain", sa.String(50), nullable=True),
        sa.Column("owner_team", sa.String(100), nullable=True),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("defaults_config", sa.JSON, nullable=True),
        sa.Column("schedule_config", sa.JSON, nullable=True),
        sa.Column("gates_config", sa.JSON, nullable=True),
        sa.Column("notifications_config", sa.JSON, nullable=True),
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
    op.create_index("idx_eval_suite_purpose", "eval_suites", ["purpose"])
    op.create_index("idx_eval_suite_domain", "eval_suites", ["domain"])
    op.create_index("idx_eval_suite_owner_team", "eval_suites", ["owner_team"])

    # =========================================================================
    # 2. eval_tasks 테이블
    # =========================================================================

    op.create_table(
        "eval_tasks",
        sa.Column("task_id", sa.String(50), primary_key=True),
        sa.Column(
            "suite_id",
            sa.String(50),
            sa.ForeignKey("eval_suites.suite_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", eval_task_type_enum, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("domain", sa.String(50), nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("risk", sa.String(20), nullable=False, server_default="low"),
        sa.Column("purpose", sa.String(50), nullable=True),
        sa.Column("expected_pass_rate", sa.Float, nullable=True),
        sa.Column("owner", sa.String(100), nullable=True),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("inputs_config", sa.JSON, nullable=True),
        sa.Column("success_criteria", sa.JSON, nullable=True),
        sa.Column("trial_config", sa.JSON, nullable=True),
        sa.Column("environment_config", sa.JSON, nullable=True),
        sa.Column("agent_config", sa.JSON, nullable=True),
        sa.Column("graders_config", sa.JSON, nullable=True),
        sa.Column("scoring_config", sa.JSON, nullable=True),
        sa.Column("timeout_config", sa.JSON, nullable=True),
        sa.Column("cost_budget", sa.JSON, nullable=True),
        sa.Column("yaml_path", sa.String(500), nullable=True),
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
    op.create_index("idx_eval_task_suite_id", "eval_tasks", ["suite_id"])
    op.create_index("idx_eval_task_type", "eval_tasks", ["type"])
    op.create_index("idx_eval_task_difficulty", "eval_tasks", ["difficulty"])

    # =========================================================================
    # 3. eval_runs 테이블
    # =========================================================================

    op.create_table(
        "eval_runs",
        sa.Column("run_id", sa.String(50), primary_key=True),
        sa.Column(
            "suite_id",
            sa.String(50),
            sa.ForeignKey("eval_suites.suite_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("triggered_by", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("git_sha", sa.String(40), nullable=True),
        sa.Column("git_branch", sa.String(200), nullable=True),
        sa.Column("pr_number", sa.Integer, nullable=True),
        sa.Column("agent_version", sa.String(50), nullable=True),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column("suite_version", sa.String(20), nullable=True),
        sa.Column(
            "status",
            eval_run_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_k", sa.Integer, nullable=False, server_default="5"),
        sa.Column("parallel", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("task_ids", sa.JSON, nullable=True),
        sa.Column("total_tasks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("passed_tasks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_tasks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_duration_seconds", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("gate_passed", sa.Boolean, nullable=True),
        sa.Column("gate_decision", eval_decision_enum, nullable=True),
        sa.Column("gate_reason", sa.Text, nullable=True),
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
    op.create_index("idx_eval_run_suite_id", "eval_runs", ["suite_id"])
    op.create_index("idx_eval_run_status", "eval_runs", ["status"])
    op.create_index("idx_eval_run_triggered_by", "eval_runs", ["triggered_by"])
    op.create_index("idx_eval_run_git_sha", "eval_runs", ["git_sha"])
    op.create_index("idx_eval_run_created_at", "eval_runs", ["created_at"])

    # =========================================================================
    # 4. eval_trials 테이블
    # =========================================================================

    op.create_table(
        "eval_trials",
        sa.Column("trial_id", sa.String(50), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(50),
            sa.ForeignKey("eval_runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.String(50),
            sa.ForeignKey("eval_tasks.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trial_index", sa.Integer, nullable=False),
        sa.Column("seed", sa.Integer, nullable=True),
        sa.Column("env_snapshot_id", sa.String(100), nullable=True),
        sa.Column(
            "status",
            eval_trial_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("passed", sa.Boolean, nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("grader_results", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_type", sa.String(100), nullable=True),
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
    op.create_index("idx_eval_trial_run_id", "eval_trials", ["run_id"])
    op.create_index("idx_eval_trial_task_id", "eval_trials", ["task_id"])
    op.create_index("idx_eval_trial_status", "eval_trials", ["status"])
    op.create_index("idx_eval_trial_passed", "eval_trials", ["passed"])

    # =========================================================================
    # 5. eval_transcripts 테이블
    # =========================================================================

    op.create_table(
        "eval_transcripts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "trial_id",
            sa.String(50),
            sa.ForeignKey("eval_trials.trial_id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("messages", sa.JSON, nullable=True),
        sa.Column("tool_calls", sa.JSON, nullable=True),
        sa.Column("intermediate_states", sa.JSON, nullable=True),
        sa.Column("n_turns", sa.Integer, nullable=False, server_default="0"),
        sa.Column("n_tool_calls", sa.Integer, nullable=False, server_default="0"),
        sa.Column("n_errors", sa.Integer, nullable=False, server_default="0"),
        sa.Column("n_retries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("raw_transcript", sa.Text, nullable=True),
    )
    op.create_index("idx_eval_transcript_trial_id", "eval_transcripts", ["trial_id"])

    # =========================================================================
    # 6. eval_outcomes 테이블
    # =========================================================================

    op.create_table(
        "eval_outcomes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "trial_id",
            sa.String(50),
            sa.ForeignKey("eval_trials.trial_id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("final_state", sa.JSON, nullable=True),
        sa.Column("artifacts", sa.JSON, nullable=True),
        sa.Column("db_changes", sa.JSON, nullable=True),
        sa.Column("file_hashes", sa.JSON, nullable=True),
        sa.Column("api_responses", sa.JSON, nullable=True),
    )
    op.create_index("idx_eval_outcome_trial_id", "eval_outcomes", ["trial_id"])

    # =========================================================================
    # 7. eval_grader_results 테이블
    # =========================================================================

    op.create_table(
        "eval_grader_results",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "trial_id",
            sa.String(50),
            sa.ForeignKey("eval_trials.trial_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("grader_id", sa.String(50), nullable=False),
        sa.Column("grader_type", sa.String(50), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("partial_scores", sa.JSON, nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("judge_model", sa.String(100), nullable=True),
        sa.Column("judge_prompt", sa.Text, nullable=True),
        sa.Column("judge_response", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "graded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_eval_grader_result_trial_id", "eval_grader_results", ["trial_id"])
    op.create_index("idx_eval_grader_result_grader_id", "eval_grader_results", ["grader_id"])
    op.create_index("idx_eval_grader_result_passed", "eval_grader_results", ["passed"])


def downgrade() -> None:
    # eval_grader_results 테이블 삭제
    op.drop_index("idx_eval_grader_result_passed", table_name="eval_grader_results")
    op.drop_index("idx_eval_grader_result_grader_id", table_name="eval_grader_results")
    op.drop_index("idx_eval_grader_result_trial_id", table_name="eval_grader_results")
    op.drop_table("eval_grader_results")

    # eval_outcomes 테이블 삭제
    op.drop_index("idx_eval_outcome_trial_id", table_name="eval_outcomes")
    op.drop_table("eval_outcomes")

    # eval_transcripts 테이블 삭제
    op.drop_index("idx_eval_transcript_trial_id", table_name="eval_transcripts")
    op.drop_table("eval_transcripts")

    # eval_trials 테이블 삭제
    op.drop_index("idx_eval_trial_passed", table_name="eval_trials")
    op.drop_index("idx_eval_trial_status", table_name="eval_trials")
    op.drop_index("idx_eval_trial_task_id", table_name="eval_trials")
    op.drop_index("idx_eval_trial_run_id", table_name="eval_trials")
    op.drop_table("eval_trials")

    # eval_runs 테이블 삭제
    op.drop_index("idx_eval_run_created_at", table_name="eval_runs")
    op.drop_index("idx_eval_run_git_sha", table_name="eval_runs")
    op.drop_index("idx_eval_run_triggered_by", table_name="eval_runs")
    op.drop_index("idx_eval_run_status", table_name="eval_runs")
    op.drop_index("idx_eval_run_suite_id", table_name="eval_runs")
    op.drop_table("eval_runs")

    # eval_tasks 테이블 삭제
    op.drop_index("idx_eval_task_difficulty", table_name="eval_tasks")
    op.drop_index("idx_eval_task_type", table_name="eval_tasks")
    op.drop_index("idx_eval_task_suite_id", table_name="eval_tasks")
    op.drop_table("eval_tasks")

    # eval_suites 테이블 삭제
    op.drop_index("idx_eval_suite_owner_team", table_name="eval_suites")
    op.drop_index("idx_eval_suite_domain", table_name="eval_suites")
    op.drop_index("idx_eval_suite_purpose", table_name="eval_suites")
    op.drop_table("eval_suites")

    # Enum 타입 삭제
    sa.Enum(name="evaldecision").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="evalsuitepurpose").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="evalrunstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="evaltrialstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="evaltasktype").drop(op.get_bind(), checkfirst=True)
