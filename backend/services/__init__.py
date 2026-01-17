"""
Services 모듈

비즈니스 로직을 처리하는 서비스 레이어
"""

from backend.services.approval_service import ApprovalService, approval_service
from backend.services.embedding_service import EmbeddingService, embedding_service
from backend.services.entity_resolution_service import (
    EntityResolutionService,
    entity_resolution_service,
)
from backend.services.llm_extraction_service import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
    LLMExtractionService,
    llm_extraction_service,
)
from backend.services.notification_service import NotificationService, notification_service
from backend.services.ontology_integration_service import (
    OntologyCreationResult,
    OntologyIntegrationService,
    ontology_integration_service,
)
from backend.services.ontology_service import (
    OntologyService,
    ontology_service,
    ontology_service_no_index,
)
from backend.services.play_sync_service import PlaySyncService, play_sync_service
from backend.services.play_sync_triggers import (
    PlaySyncTriggers,
    emit_activity_created,
    emit_brief_created,
    emit_brief_status_changed,
    emit_signal_created,
    emit_task_completed,
    play_sync_triggers,
)
from backend.services.rag_service import RAGService, rag_service
from backend.services.task_converter import TaskConverter, TaskTemplate, task_converter
from backend.services.todo_parser import TodoItem, TodoList, TodoParser, todo_parser
from backend.services.todo_sync_service import (
    ProgressReport,
    SyncDiff,
    TodoSyncService,
    todo_sync_service,
)

__all__ = [
    # Embedding
    "EmbeddingService",
    "embedding_service",
    # Entity Resolution
    "EntityResolutionService",
    "entity_resolution_service",
    # LLM Extraction
    "LLMExtractionService",
    "llm_extraction_service",
    "ExtractionResult",
    "ExtractedEntity",
    "ExtractedRelation",
    # Ontology Integration
    "OntologyIntegrationService",
    "ontology_integration_service",
    "OntologyCreationResult",
    # Ontology
    "OntologyService",
    "ontology_service",
    "ontology_service_no_index",
    # RAG
    "RAGService",
    "rag_service",
    # Task Converter
    "TaskConverter",
    "TaskTemplate",
    "task_converter",
    # Play Sync
    "PlaySyncService",
    "play_sync_service",
    "PlaySyncTriggers",
    "play_sync_triggers",
    "emit_signal_created",
    "emit_brief_created",
    "emit_brief_status_changed",
    "emit_task_completed",
    "emit_activity_created",
    # Notification
    "NotificationService",
    "notification_service",
    # Approval
    "ApprovalService",
    "approval_service",
    # ToDo
    "TodoParser",
    "todo_parser",
    "TodoItem",
    "TodoList",
    "TodoSyncService",
    "todo_sync_service",
    "SyncDiff",
    "ProgressReport",
]
