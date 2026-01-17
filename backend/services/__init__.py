"""
Services 모듈

비즈니스 로직을 처리하는 서비스 레이어
"""

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
from backend.services.rag_service import RAGService, rag_service

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
]
