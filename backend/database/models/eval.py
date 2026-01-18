"""
Evals 모델

AI 에이전트 평가 플랫폼 테이블 정의
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


# ============================================================================
# Enums
# ============================================================================


class EvalTaskType(enum.Enum):
    """Task 유형"""

    CODING = "coding"
    WORKFLOW = "workflow"
    CONVERSATIONAL = "conversational"
    RESEARCH = "research"
    COMPUTER_USE = "computer_use"


class EvalTrialStatus(enum.Enum):
    """Trial 실행 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class EvalRunStatus(enum.Enum):
    """Run 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvalSuitePurpose(enum.Enum):
    """Suite 목적"""

    CAPABILITY = "capability"
    REGRESSION = "regression"
    BENCHMARK = "benchmark"
    SAFETY = "safety"


class EvalDecision(enum.Enum):
    """평가 판정"""

    PASS = "pass"
    FAIL = "fail"
    MARGINAL = "marginal"
    UNKNOWN = "unknown"


# ============================================================================
# EvalSuite
# ============================================================================


class EvalSuite(Base, TimestampMixin):
    """
    평가 스위트 (Eval Suite)

    특정 역량/행동을 측정하는 Task 묶음
    """

    __tablename__ = "eval_suites"

    # Primary Key
    suite_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # 기본 정보
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    purpose: Mapped[EvalSuitePurpose] = mapped_column(Enum(EvalSuitePurpose), nullable=False)

    # 분류
    domain: Mapped[str | None] = mapped_column(String(50))
    owner_team: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list | None] = mapped_column(JSON)

    # 설정 (YAML에서 로드)
    defaults_config: Mapped[dict | None] = mapped_column(JSON)
    schedule_config: Mapped[dict | None] = mapped_column(JSON)
    gates_config: Mapped[dict | None] = mapped_column(JSON)
    notifications_config: Mapped[dict | None] = mapped_column(JSON)

    # Relationships
    tasks: Mapped[list[EvalTask]] = relationship(
        "EvalTask",
        back_populates="suite",
        cascade="all, delete-orphan",
    )

    runs: Mapped[list[EvalRun]] = relationship(
        "EvalRun",
        back_populates="suite",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_eval_suite_purpose", "purpose"),
        Index("idx_eval_suite_domain", "domain"),
        Index("idx_eval_suite_owner_team", "owner_team"),
    )

    def __repr__(self) -> str:
        return f"<EvalSuite(suite_id='{self.suite_id}', name='{self.name}')>"


# ============================================================================
# EvalTask
# ============================================================================


class EvalTask(Base, TimestampMixin):
    """
    평가 과제 (Eval Task)

    입력 + 성공 기준이 정의된 단일 테스트 케이스
    """

    __tablename__ = "eval_tasks"

    # Primary Key
    task_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign Key
    suite_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("eval_suites.suite_id", ondelete="CASCADE"),
        nullable=False,
    )

    # 기본 정보
    type: Mapped[EvalTaskType] = mapped_column(Enum(EvalTaskType), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")

    # 메타데이터
    domain: Mapped[str | None] = mapped_column(String(50))
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    risk: Mapped[str] = mapped_column(String(20), default="low")
    purpose: Mapped[str | None] = mapped_column(String(50))
    expected_pass_rate: Mapped[float | None] = mapped_column(Float)
    owner: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list | None] = mapped_column(JSON)

    # 설정 (YAML에서 로드, JSON으로 저장)
    inputs_config: Mapped[dict | None] = mapped_column(JSON)
    success_criteria: Mapped[dict | None] = mapped_column(JSON)
    trial_config: Mapped[dict | None] = mapped_column(JSON)
    environment_config: Mapped[dict | None] = mapped_column(JSON)
    agent_config: Mapped[dict | None] = mapped_column(JSON)
    graders_config: Mapped[list | None] = mapped_column(JSON)
    scoring_config: Mapped[dict | None] = mapped_column(JSON)
    timeout_config: Mapped[dict | None] = mapped_column(JSON)
    cost_budget: Mapped[dict | None] = mapped_column(JSON)

    # YAML 원본 경로
    yaml_path: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    suite: Mapped[EvalSuite] = relationship("EvalSuite", back_populates="tasks")

    trials: Mapped[list[EvalTrial]] = relationship(
        "EvalTrial",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_eval_task_suite_id", "suite_id"),
        Index("idx_eval_task_type", "type"),
        Index("idx_eval_task_difficulty", "difficulty"),
    )

    def __repr__(self) -> str:
        return f"<EvalTask(task_id='{self.task_id}', type='{self.type.value}')>"


# ============================================================================
# EvalRun
# ============================================================================


class EvalRun(Base, TimestampMixin):
    """
    평가 실행 (Eval Run)

    하나의 평가 세션 (Suite 또는 개별 Task 실행)
    """

    __tablename__ = "eval_runs"

    # Primary Key
    run_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign Key
    suite_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("eval_suites.suite_id", ondelete="SET NULL"),
        nullable=True,
    )

    # 트리거 정보
    triggered_by: Mapped[str] = mapped_column(String(50), default="manual")
    git_sha: Mapped[str | None] = mapped_column(String(40))
    git_branch: Mapped[str | None] = mapped_column(String(200))
    pr_number: Mapped[int | None] = mapped_column(Integer)

    # 버전 정보
    agent_version: Mapped[str | None] = mapped_column(String(50))
    model_version: Mapped[str | None] = mapped_column(String(100))
    suite_version: Mapped[str | None] = mapped_column(String(20))

    # 상태
    status: Mapped[EvalRunStatus] = mapped_column(
        Enum(EvalRunStatus), default=EvalRunStatus.PENDING, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 실행 설정
    trial_k: Mapped[int] = mapped_column(Integer, default=5)
    parallel: Mapped[bool] = mapped_column(Boolean, default=True)
    task_ids: Mapped[list | None] = mapped_column(JSON)

    # 결과 요약
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    passed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    failed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    # 게이트 결과
    gate_passed: Mapped[bool | None] = mapped_column(Boolean)
    gate_decision: Mapped[EvalDecision | None] = mapped_column(Enum(EvalDecision))
    gate_reason: Mapped[str | None] = mapped_column(Text)

    # Relationships
    suite: Mapped[EvalSuite | None] = relationship("EvalSuite", back_populates="runs")

    trials: Mapped[list[EvalTrial]] = relationship(
        "EvalTrial",
        back_populates="run",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_eval_run_suite_id", "suite_id"),
        Index("idx_eval_run_status", "status"),
        Index("idx_eval_run_triggered_by", "triggered_by"),
        Index("idx_eval_run_git_sha", "git_sha"),
        Index("idx_eval_run_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<EvalRun(run_id='{self.run_id}', status='{self.status.value}')>"


# ============================================================================
# EvalTrial
# ============================================================================


class EvalTrial(Base, TimestampMixin):
    """
    트라이얼 (Trial)

    한 Task에 대한 1회 실행 시도
    """

    __tablename__ = "eval_trials"

    # Primary Key
    trial_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign Keys
    run_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("eval_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("eval_tasks.task_id", ondelete="CASCADE"),
        nullable=False,
    )

    # 실행 정보
    trial_index: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int | None] = mapped_column(Integer)
    env_snapshot_id: Mapped[str | None] = mapped_column(String(100))

    # 상태
    status: Mapped[EvalTrialStatus] = mapped_column(
        Enum(EvalTrialStatus), default=EvalTrialStatus.PENDING, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 메트릭
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # 채점 결과
    passed: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[float | None] = mapped_column(Float)
    grader_results: Mapped[list | None] = mapped_column(JSON)

    # 에러 정보
    error_message: Mapped[str | None] = mapped_column(Text)
    error_type: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    run: Mapped[EvalRun] = relationship("EvalRun", back_populates="trials")
    task: Mapped[EvalTask] = relationship("EvalTask", back_populates="trials")

    transcript: Mapped[EvalTranscript | None] = relationship(
        "EvalTranscript",
        back_populates="trial",
        uselist=False,
        cascade="all, delete-orphan",
    )

    outcome: Mapped[EvalOutcome | None] = relationship(
        "EvalOutcome",
        back_populates="trial",
        uselist=False,
        cascade="all, delete-orphan",
    )

    grader_result_details: Mapped[list[EvalGraderResult]] = relationship(
        "EvalGraderResult",
        back_populates="trial",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_eval_trial_run_id", "run_id"),
        Index("idx_eval_trial_task_id", "task_id"),
        Index("idx_eval_trial_status", "status"),
        Index("idx_eval_trial_passed", "passed"),
    )

    def __repr__(self) -> str:
        return f"<EvalTrial(trial_id='{self.trial_id}', status='{self.status.value}')>"


# ============================================================================
# EvalTranscript
# ============================================================================


class EvalTranscript(Base):
    """
    트랜스크립트 (Transcript)

    한 Trial의 전체 실행 기록
    """

    __tablename__ = "eval_transcripts"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign Key
    trial_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("eval_trials.trial_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # 메시지 기록
    messages: Mapped[list | None] = mapped_column(JSON)
    tool_calls: Mapped[list | None] = mapped_column(JSON)
    intermediate_states: Mapped[list | None] = mapped_column(JSON)

    # 트랜스크립트 메트릭
    n_turns: Mapped[int] = mapped_column(Integer, default=0)
    n_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    n_errors: Mapped[int] = mapped_column(Integer, default=0)
    n_retries: Mapped[int] = mapped_column(Integer, default=0)

    # 원본 저장 (압축된 JSON)
    raw_transcript: Mapped[str | None] = mapped_column(Text)

    # Relationships
    trial: Mapped[EvalTrial] = relationship("EvalTrial", back_populates="transcript")

    # Indexes
    __table_args__ = (Index("idx_eval_transcript_trial_id", "trial_id"),)

    def __repr__(self) -> str:
        return f"<EvalTranscript(trial_id='{self.trial_id}', n_turns={self.n_turns})>"


# ============================================================================
# EvalOutcome
# ============================================================================


class EvalOutcome(Base):
    """
    결과 상태 (Outcome)

    Trial 종료 시 환경의 최종 상태
    """

    __tablename__ = "eval_outcomes"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign Key
    trial_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("eval_trials.trial_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # 최종 상태
    final_state: Mapped[dict | None] = mapped_column(JSON)
    artifacts: Mapped[list | None] = mapped_column(JSON)
    db_changes: Mapped[list | None] = mapped_column(JSON)
    file_hashes: Mapped[dict | None] = mapped_column(JSON)
    api_responses: Mapped[list | None] = mapped_column(JSON)

    # Relationships
    trial: Mapped[EvalTrial] = relationship("EvalTrial", back_populates="outcome")

    # Indexes
    __table_args__ = (Index("idx_eval_outcome_trial_id", "trial_id"),)

    def __repr__(self) -> str:
        return f"<EvalOutcome(trial_id='{self.trial_id}')>"


# ============================================================================
# EvalGraderResult
# ============================================================================


class EvalGraderResult(Base):
    """
    채점 결과 (Grader Result)

    개별 채점기의 평가 결과
    """

    __tablename__ = "eval_grader_results"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign Key
    trial_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("eval_trials.trial_id", ondelete="CASCADE"),
        nullable=False,
    )

    # 채점기 정보
    grader_id: Mapped[str] = mapped_column(String(50), nullable=False)
    grader_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # 점수
    score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    partial_scores: Mapped[dict | None] = mapped_column(JSON)

    # 설명
    explanation: Mapped[str | None] = mapped_column(Text)

    # LLM Judge 메타데이터
    judge_model: Mapped[str | None] = mapped_column(String(100))
    judge_prompt: Mapped[str | None] = mapped_column(Text)
    judge_response: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)

    # 실행 정보
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text)
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    trial: Mapped[EvalTrial] = relationship("EvalTrial", back_populates="grader_result_details")

    # Indexes
    __table_args__ = (
        Index("idx_eval_grader_result_trial_id", "trial_id"),
        Index("idx_eval_grader_result_grader_id", "grader_id"),
        Index("idx_eval_grader_result_passed", "passed"),
    )

    def __repr__(self) -> str:
        return f"<EvalGraderResult(grader_id='{self.grader_id}', score={self.score})>"
