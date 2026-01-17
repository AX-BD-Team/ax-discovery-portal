"""
Database repositories package

CRUD 저장소 패턴
"""

from .base import CRUDBase
from .brief import BriefRepository, brief_repo
from .ontology import OntologyRepository, ontology_repo
from .opportunity import (
    ApprovalRequestRepository,
    OpportunityRepository,
    StageTransitionRepository,
    approval_request_repo,
    opportunity_repo,
    stage_transition_repo,
)
from .play_record import PlayRecordRepository, play_record_repo
from .scorecard import ScorecardRepository, scorecard_repo
from .signal import SignalRepository, signal_repo
from .task import TaskRepository, task_repo

__all__ = [
    # Base
    "CRUDBase",
    # Signal
    "signal_repo",
    "SignalRepository",
    # Scorecard
    "scorecard_repo",
    "ScorecardRepository",
    # Brief
    "brief_repo",
    "BriefRepository",
    # Opportunity (Stage System)
    "opportunity_repo",
    "OpportunityRepository",
    "stage_transition_repo",
    "StageTransitionRepository",
    "approval_request_repo",
    "ApprovalRequestRepository",
    # PlayRecord
    "play_record_repo",
    "PlayRecordRepository",
    # Ontology
    "ontology_repo",
    "OntologyRepository",
    # Task
    "task_repo",
    "TaskRepository",
]
