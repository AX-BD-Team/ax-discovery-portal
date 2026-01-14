"""
Database repositories package

CRUD 저장소 패턴
"""

from .base import CRUDBase
from .signal import signal_repo, SignalRepository
from .scorecard import scorecard_repo, ScorecardRepository
from .brief import brief_repo, BriefRepository
from .play_record import play_record_repo, PlayRecordRepository
from .ontology import ontology_repo, OntologyRepository

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
    # PlayRecord
    "play_record_repo",
    "PlayRecordRepository",
    # Ontology
    "ontology_repo",
    "OntologyRepository",
]
