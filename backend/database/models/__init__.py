"""
Database models package

SQLAlchemy ORM 모델 정의

P0 변경사항:
- Triple: Lifecycle 속성 (status, assertion_type, evidence_span 등)
- Entity: Recency 시간 필드 (published_at, observed_at, ingested_at) + Sync 상태
- Trace: 실패 분류 체계 자동 태깅
- CompetencyQuestion: BD용 regression 테스트
"""

from .action_log import ActionLog, ActionType
from .approval_request import ApprovalRequest, ApprovalStatus, ApprovalType
from .brief import BriefStatus, OpportunityBrief, ValidationMethod
from .entity import Entity, EntityType, SyncStatus

# Evals 모델
from .eval import (
    EvalDecision,
    EvalGraderResult,
    EvalOutcome,
    EvalRun,
    EvalRunStatus,
    EvalSuite,
    EvalSuitePurpose,
    EvalTask,
    EvalTaskType,
    EvalTranscript,
    EvalTrial,
    EvalTrialStatus,
)
from .opportunity import Opportunity, OpportunityStage
from .play_record import (
    PlayChannel,
    PlayCycle,
    PlayPriority,
    PlayRecord,
    PlaySource,
    PlayStatus,
)
from .scorecard import Decision, NextStep, Scorecard
from .signal import Signal, SignalChannel, SignalSource, SignalStatus
from .stage_transition import GateDecision, StageTransition, TransitionTrigger
from .task import Task, TaskPriority, TaskStatus
from .trace import (
    DEFAULT_COMPETENCY_QUESTIONS,
    CompetencyQuestion,
    Trace,
    TraceErrorType,
    TraceStatus,
)
from .triple import AssertionType, PredicateType, Triple, TripleStatus
from .user import User, UserRole

__all__ = [
    # Signal
    "Signal",
    "SignalSource",
    "SignalChannel",
    "SignalStatus",
    # Scorecard
    "Scorecard",
    "Decision",
    "NextStep",
    # OpportunityBrief
    "OpportunityBrief",
    "ValidationMethod",
    "BriefStatus",
    # Opportunity (Stage System)
    "Opportunity",
    "OpportunityStage",
    # StageTransition
    "StageTransition",
    "TransitionTrigger",
    "GateDecision",
    # ApprovalRequest (HITL)
    "ApprovalRequest",
    "ApprovalStatus",
    "ApprovalType",
    # PlayRecord
    "PlayRecord",
    "PlayStatus",
    "PlaySource",
    "PlayChannel",
    "PlayPriority",
    "PlayCycle",
    # Task
    "Task",
    "TaskStatus",
    "TaskPriority",
    # ActionLog
    "ActionLog",
    "ActionType",
    # Ontology - Entity
    "Entity",
    "EntityType",
    "SyncStatus",
    # Ontology - Triple (P0: Lifecycle)
    "Triple",
    "PredicateType",
    "TripleStatus",
    "AssertionType",
    # Trace (P0: 실패 분류)
    "Trace",
    "TraceStatus",
    "TraceErrorType",
    # Competency Questions (P0)
    "CompetencyQuestion",
    "DEFAULT_COMPETENCY_QUESTIONS",
    # User (인증)
    "User",
    "UserRole",
    # Evals (AI 에이전트 평가)
    "EvalSuite",
    "EvalTask",
    "EvalRun",
    "EvalTrial",
    "EvalTranscript",
    "EvalOutcome",
    "EvalGraderResult",
    "EvalTaskType",
    "EvalTrialStatus",
    "EvalRunStatus",
    "EvalSuitePurpose",
    "EvalDecision",
]
