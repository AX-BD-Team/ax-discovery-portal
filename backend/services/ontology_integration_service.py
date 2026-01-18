"""
Ontology Integration Service

LLM 추출 결과를 온톨로지(Entity/Triple)로 변환하는 통합 서비스
Entity Resolution, Triple 검증, DB 저장을 조율
"""

from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent_runtime.ontology.validator import TripleValidator
from backend.database.models.entity import Entity, EntityType
from backend.database.models.triple import (
    PredicateType,
    Triple,
)
from backend.database.repositories.ontology import ontology_repo
from backend.services.entity_resolution_service import (
    EntityResolutionService,
    entity_resolution_service,
)
from backend.services.llm_extraction_service import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
)

logger = structlog.get_logger()


# ==================== 데이터 모델 ====================


@dataclass
class OntologyCreationResult:
    """온톨로지 생성 결과"""

    created_entities: list[Entity] = field(default_factory=list)
    merged_entities: list[tuple[ExtractedEntity, Entity]] = field(default_factory=list)
    created_triples: list[Triple] = field(default_factory=list)
    skipped_triples: list[dict[str, Any]] = field(default_factory=list)
    same_as_triples: list[Triple] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # 통계
    entity_created_count: int = 0
    entity_merged_count: int = 0
    triple_created_count: int = 0
    triple_skipped_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "created_entities": [e.to_dict() for e in self.created_entities],
            "merged_entities": [
                {"extracted": e.name, "merged_to": m.entity_id} for e, m in self.merged_entities
            ],
            "created_triples": [t.to_dict() for t in self.created_triples],
            "skipped_triples": self.skipped_triples,
            "same_as_triples": [t.to_dict() for t in self.same_as_triples],
            "errors": self.errors,
            "statistics": {
                "entity_created": self.entity_created_count,
                "entity_merged": self.entity_merged_count,
                "triple_created": self.triple_created_count,
                "triple_skipped": self.triple_skipped_count,
            },
        }


# ==================== 온톨로지 통합 서비스 ====================


class OntologyIntegrationService:
    """
    온톨로지 통합 서비스

    LLM 추출 결과 → Entity/Triple 변환 및 저장
    - Entity Resolution으로 중복 처리
    - Triple Validator로 제약 검증
    - 트랜잭션 관리
    """

    def __init__(
        self,
        resolution_service: EntityResolutionService | None = None,
    ):
        self.resolution_service = resolution_service or entity_resolution_service
        self.triple_validator = TripleValidator()
        self.logger = logger.bind(service="ontology_integration")

    async def create_from_extraction(
        self,
        db: AsyncSession,
        extraction_result: ExtractionResult,
        source_ref: str | None = None,
        created_by: str | None = None,
    ) -> OntologyCreationResult:
        """
        LLM 추출 결과에서 온톨로지 생성

        Args:
            db: 데이터베이스 세션
            extraction_result: LLM 추출 결과
            source_ref: 출처 참조 (Activity ID 등)
            created_by: 생성자

        Returns:
            OntologyCreationResult: 생성 결과
        """
        self.logger.info(
            "Creating ontology from extraction",
            entities=len(extraction_result.entities),
            relations=len(extraction_result.relations),
            source_ref=source_ref,
        )

        result = OntologyCreationResult()

        try:
            # 1. Entity Resolution 수행
            resolution_result = await self.resolution_service.resolve_entities(
                db, extraction_result.entities
            )

            # 2. 엔티티 생성/병합
            entity_id_map = await self._process_entities(db, resolution_result, result, created_by)

            # 3. Triple 생성
            await self._process_relations(
                db,
                extraction_result.relations,
                entity_id_map,
                result,
                source_ref,
                created_by,
            )

            # 4. SAME_AS Triple 생성 (불확실한 쌍)
            await self._process_same_as(
                db, resolution_result.uncertain_pairs, entity_id_map, result, created_by
            )

            self.logger.info(
                "Ontology creation completed",
                entities_created=result.entity_created_count,
                entities_merged=result.entity_merged_count,
                triples_created=result.triple_created_count,
                triples_skipped=result.triple_skipped_count,
            )

            return result

        except Exception as e:
            self.logger.error("Ontology creation failed", error=str(e))
            result.errors.append(f"Ontology creation failed: {e!s}")
            raise

    async def create_activity_entity(
        self,
        db: AsyncSession,
        activity_id: str,
        title: str,
        activity_type: str = "seminar",
        url: str | None = None,
        date: str | None = None,
        created_by: str | None = None,
    ) -> Entity:
        """
        Activity Entity 생성 (편의 메서드)

        Args:
            db: 데이터베이스 세션
            activity_id: Activity ID (external_ref_id)
            title: Activity 제목
            activity_type: 활동 유형 (seminar, meeting, inbound 등)
            url: 관련 URL
            date: 활동 일자
            created_by: 생성자

        Returns:
            생성된 Activity Entity
        """
        properties = {
            "activity_type": activity_type,
        }
        if url:
            properties["url"] = url
        if date:
            properties["activity_date"] = date

        entity = await ontology_repo.create_entity(
            db=db,
            entity_type=EntityType.ACTIVITY,
            name=title,
            description=f"{activity_type}: {title}",
            properties=properties,
            external_ref_id=activity_id,
            confidence=1.0,
            created_by=created_by,
        )

        self.logger.info(
            "Activity entity created",
            entity_id=entity.entity_id,
            activity_id=activity_id,
        )

        return entity

    async def create_signal_entity(
        self,
        db: AsyncSession,
        title: str,
        pain: str,
        activity_entity_id: str | None = None,
        target_org_id: str | None = None,
        created_by: str | None = None,
    ) -> tuple[Entity, list[Triple]]:
        """
        Signal Entity 및 관련 Triple 생성

        Args:
            db: 데이터베이스 세션
            title: Signal 제목
            pain: Pain Point
            activity_entity_id: 출처 Activity Entity ID
            target_org_id: 대상 Organization Entity ID
            created_by: 생성자

        Returns:
            (Signal Entity, 생성된 Triple 목록)
        """
        properties = {"pain": pain}

        signal_entity = await ontology_repo.create_entity(
            db=db,
            entity_type=EntityType.SIGNAL,
            name=title,
            description=f"Pain: {pain}",
            properties=properties,
            confidence=0.85,
            created_by=created_by,
        )

        triples = []

        # Activity --GENERATES--> Signal
        if activity_entity_id:
            triple = await ontology_repo.create_triple(
                db=db,
                subject_id=activity_entity_id,
                predicate=PredicateType.GENERATES,
                object_id=signal_entity.entity_id,
                confidence=0.9,
                created_by=created_by,
            )
            triples.append(triple)

        # Signal --TARGETS--> Organization
        if target_org_id:
            triple = await ontology_repo.create_triple(
                db=db,
                subject_id=signal_entity.entity_id,
                predicate=PredicateType.TARGETS,
                object_id=target_org_id,
                confidence=0.85,
                created_by=created_by,
            )
            triples.append(triple)

        self.logger.info(
            "Signal entity created with triples",
            signal_id=signal_entity.entity_id,
            triples_count=len(triples),
        )

        return signal_entity, triples

    async def _process_entities(
        self,
        db: AsyncSession,
        resolution_result,
        result: OntologyCreationResult,
        created_by: str | None,
    ) -> dict[str, str]:
        """엔티티 처리: 생성 또는 병합"""
        from backend.services.entity_resolution_service import ResolutionResult

        resolution: ResolutionResult = resolution_result
        entity_id_map: dict[str, str] = {}  # 추출 엔티티 이름 → DB 엔티티 ID

        for match in resolution.matches:
            if match.action == "merge" and match.existing_entity is not None:
                # 기존 엔티티로 병합
                existing_entity = match.existing_entity
                entity_id_map[match.new_entity.name] = existing_entity.entity_id
                result.merged_entities.append((match.new_entity, existing_entity))
                result.entity_merged_count += 1

                self.logger.debug(
                    "Entity merged",
                    new_name=match.new_entity.name,
                    existing_id=existing_entity.entity_id,
                )

            else:  # "create" or "same_as"
                # 새 엔티티 생성
                entity = await ontology_repo.create_entity(
                    db=db,
                    entity_type=match.new_entity.entity_type,
                    name=match.new_entity.name,
                    description=match.new_entity.description,
                    properties={
                        **match.new_entity.properties,
                        "aliases": match.new_entity.aliases,
                    },
                    confidence=match.new_entity.confidence,
                    created_by=created_by,
                )

                entity_id_map[match.new_entity.name] = entity.entity_id
                result.created_entities.append(entity)
                result.entity_created_count += 1

                self.logger.debug(
                    "Entity created",
                    name=entity.name,
                    entity_id=entity.entity_id,
                )

        return entity_id_map

    async def _process_relations(
        self,
        db: AsyncSession,
        relations: list[ExtractedRelation],
        entity_id_map: dict[str, str],
        result: OntologyCreationResult,
        source_ref: str | None,
        created_by: str | None,
    ) -> None:
        """관계(Triple) 생성"""
        for relation in relations:
            # Subject/Object ID 조회
            subject_id = entity_id_map.get(relation.subject)
            object_id = entity_id_map.get(relation.object)

            if not subject_id or not object_id:
                result.skipped_triples.append(
                    {
                        "subject": relation.subject,
                        "predicate": relation.predicate.value,
                        "object": relation.object,
                        "reason": "Entity not found in map",
                    }
                )
                result.triple_skipped_count += 1
                continue

            # 검증
            validation = self.triple_validator.validate(
                subject_type=relation.subject_type,
                predicate=relation.predicate,
                object_type=relation.object_type,
                confidence=relation.confidence,
            )

            if not validation.is_valid:
                result.skipped_triples.append(
                    {
                        "subject": relation.subject,
                        "predicate": relation.predicate.value,
                        "object": relation.object,
                        "reason": "; ".join(e.message for e in validation.errors),
                    }
                )
                result.triple_skipped_count += 1
                continue

            # 중복 체크
            existing, _ = await ontology_repo.query_triples(
                db,
                subject_id=subject_id,
                predicate=relation.predicate,
                object_id=object_id,
                limit=1,
            )

            if existing:
                result.skipped_triples.append(
                    {
                        "subject": relation.subject,
                        "predicate": relation.predicate.value,
                        "object": relation.object,
                        "reason": "Duplicate triple",
                    }
                )
                result.triple_skipped_count += 1
                continue

            # Triple 생성
            evidence_span = None
            if relation.evidence_span:
                evidence_span = {
                    "start": relation.evidence_span.start,
                    "end": relation.evidence_span.end,
                    "text": relation.evidence_span.text,
                }

            triple = await ontology_repo.create_triple(
                db=db,
                subject_id=subject_id,
                predicate=relation.predicate,
                object_id=object_id,
                confidence=relation.confidence,
                properties={
                    **relation.properties,
                    "source_ref": source_ref,
                    "evidence_span": evidence_span,
                },
                created_by=created_by,
            )

            result.created_triples.append(triple)
            result.triple_created_count += 1

            self.logger.debug(
                "Triple created",
                triple_id=triple.triple_id,
                subject=relation.subject,
                predicate=relation.predicate.value,
                object=relation.object,
            )

    async def _process_same_as(
        self,
        db: AsyncSession,
        uncertain_pairs: list,
        entity_id_map: dict[str, str],
        result: OntologyCreationResult,
        created_by: str | None,
    ) -> None:
        """SAME_AS Triple 생성 (불확실한 쌍)"""
        from backend.services.entity_resolution_service import SameAsPair

        same_as_pair: SameAsPair
        for same_as_pair in uncertain_pairs:
            # 두 엔티티의 ID 조회
            if isinstance(same_as_pair.entity_a, ExtractedEntity):
                entity_a_id = entity_id_map.get(same_as_pair.entity_a.name)
            else:
                entity_a_id = same_as_pair.entity_a.entity_id

            if isinstance(same_as_pair.entity_b, ExtractedEntity):
                entity_b_id = entity_id_map.get(same_as_pair.entity_b.name)
            else:
                entity_b_id = same_as_pair.entity_b.entity_id

            if not entity_a_id or not entity_b_id:
                continue

            # 중복 체크
            existing, _ = await ontology_repo.query_triples(
                db,
                subject_id=entity_a_id,
                predicate=PredicateType.SAME_AS,
                object_id=entity_b_id,
                limit=1,
            )

            if existing:
                continue

            # SAME_AS Triple 생성 (PROPOSED 상태)
            triple = await ontology_repo.create_triple(
                db=db,
                subject_id=entity_a_id,
                predicate=PredicateType.SAME_AS,
                object_id=entity_b_id,
                confidence=same_as_pair.confidence,
                properties={"reason": same_as_pair.reason},
                created_by=created_by,
            )

            result.same_as_triples.append(triple)

            self.logger.debug(
                "SAME_AS triple created",
                triple_id=triple.triple_id,
                entity_a=entity_a_id,
                entity_b=entity_b_id,
            )


# 싱글톤 인스턴스
ontology_integration_service = OntologyIntegrationService()
