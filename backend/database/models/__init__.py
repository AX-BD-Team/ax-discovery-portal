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
from .brief import BriefStatus, OpportunityBrief, ValidationMethod
from .entity import Entity, EntityType, SyncStatus
from .play_record import PlayRecord, PlayStatus
from .scorecard import Decision, NextStep, Scorecard
from .signal import Signal, SignalChannel, SignalSource, SignalStatus
from .trace import (
    CompetencyQuestion,
    Trace,
    TraceErrorType,
    TraceStatus,
    DEFAULT_COMPETENCY_QUESTIONS,
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
    # PlayRecord
    "PlayRecord",
    "PlayStatus",
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
]
